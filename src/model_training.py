"""
model_training.py
==================
Trains and evaluates models for BNPL/installment default risk:

  1. Classification: Logistic Regression baseline + XGBoost — predicts
     whether a borrower defaults (binary).
  2. Scores the full combined population (200K+) and assigns risk tiers.
  3. Survival Analysis stubs remain for a later prompt (lifelines).

Training / evaluation use ONLY source_flag = 'train' (labeled rows).
Scoring applies the fitted XGBoost model to the FULL combined dataset.

Usage:
    python src/model_training.py

Note (macOS): XGBoost needs libomp. If import fails, this script looks for
project-local .local/lib/libomp.dylib (conda-forge llvm-openmp extract).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# macOS: preload project-local OpenMP before importing xgboost (DYLD_LIBRARY_PATH
# is often ignored when set after process start under SIP).
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_LOCAL_OMP = _PROJECT_ROOT / ".local" / "lib" / "libomp.dylib"
if _LOCAL_OMP.exists():
    import ctypes

    ctypes.CDLL(str(_LOCAL_OMP))

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    from xgboost import XGBClassifier
except Exception as exc:  # pragma: no cover - environment/setup help
    raise SystemExit(
        "Failed to import xgboost. On macOS install OpenMP (libomp), e.g. extract "
        "conda-forge llvm-openmp into .local/lib so libomp.dylib is on DYLD_LIBRARY_PATH.\n"
        f"Original error: {exc}"
    ) from exc

PROCESSED_DATA_PATH = Path("data/processed/credit_data_clean.csv")
SCORED_DATA_PATH = Path("data/processed/scored_borrowers.csv")
RANDOM_STATE = 42
TEST_SIZE = 0.20

# Feature columns used for classification (engineered + key raw).
NUMERIC_FEATURES = [
    "revolving_utilization",
    "age",
    "times_30_59_days_late",
    "debt_ratio",
    "monthly_income",
    "num_open_credit_lines",
    "times_90_days_late",
    "num_real_estate_loans",
    "times_60_89_days_late",
    "num_dependents",
    "late_payment_code_artifact",
    "payment_to_income_ratio",
    "prior_delinquency_count",
    "revolving_utilization_bucket_ord",
]

RESUME_FEATURES = {
    "payment_to_income_ratio",
    "prior_delinquency_count",
    "revolving_utilization",
    "revolving_utilization_bucket_ord",
}

BUCKET_ORDER = {"Low (<30%)": 0, "Medium (30-70%)": 1, "High (>70%)": 2}


def load_features(path: Path = PROCESSED_DATA_PATH) -> pd.DataFrame:
    """Load the cleaned, feature-engineered dataset ready for modeling."""
    return pd.read_csv(path)


def prepare_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Add ordinal utilization bucket; return a copy ready for modeling."""
    out = df.copy()
    out["revolving_utilization_bucket_ord"] = (
        out["revolving_utilization_bucket"].map(BUCKET_ORDER).astype(float)
    )
    return out


def build_xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Build X/y from a labeled frame."""
    X = df[NUMERIC_FEATURES].copy()
    y = df["serious_dlq_2yrs"].astype(int)
    return X, y


def train_baseline_model(X_train: pd.DataFrame, y_train: pd.Series) -> Pipeline:
    """Train a logistic regression baseline with median impute + scaling."""
    numeric_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    pre = ColumnTransformer(
        transformers=[("num", numeric_pipe, list(X_train.columns))],
        remainder="drop",
    )
    clf = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=RANDOM_STATE,
    )
    pipe = Pipeline(steps=[("prep", pre), ("clf", clf)])
    pipe.fit(X_train, y_train)
    return pipe


def train_xgboost_model(X_train: pd.DataFrame, y_train: pd.Series) -> Pipeline:
    """Train XGBoost with scale_pos_weight for class imbalance."""
    neg = int((y_train == 0).sum())
    pos = int((y_train == 1).sum())
    scale_pos_weight = neg / max(pos, 1)

    numeric_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )
    pre = ColumnTransformer(
        transformers=[("num", numeric_pipe, list(X_train.columns))],
        remainder="drop",
    )
    clf = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        min_child_weight=5,
        reg_lambda=1.0,
        scale_pos_weight=scale_pos_weight,
        objective="binary:logistic",
        eval_metric="auc",
        random_state=RANDOM_STATE,
        n_jobs=4,
    )
    pipe = Pipeline(steps=[("prep", pre), ("clf", clf)])
    pipe.fit(X_train, y_train)
    print(f"[xgb] scale_pos_weight={scale_pos_weight:.3f} (neg={neg:,}, pos={pos:,})")
    return pipe


def predict_proba_positive(model, X: pd.DataFrame) -> np.ndarray:
    """Return P(default=1)."""
    return model.predict_proba(X)[:, 1]


def evaluate_classifier(
    model,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    label: str,
) -> dict:
    """
    Evaluate a trained classifier with ROC-AUC and PR metrics.
    Accuracy is intentionally not led with (severe class imbalance).
    """
    proba = predict_proba_positive(model, X_test)
    roc = roc_auc_score(y_test, proba)
    pr_auc = average_precision_score(y_test, proba)

    # Precision / recall at top decile of predicted risk
    n = len(proba)
    k = max(1, int(np.ceil(0.10 * n)))
    top_idx = np.argsort(proba)[::-1][:k]
    y_top = y_test.to_numpy()[top_idx]
    precision_at_10 = float(y_top.mean())  # among flagged, share that default
    recall_at_10 = float(y_top.sum() / max(y_test.sum(), 1))

    # PR curve material (kept for optional plotting later)
    precision, recall, _ = precision_recall_curve(y_test, proba)

    metrics = {
        "label": label,
        "roc_auc": float(roc),
        "pr_auc": float(pr_auc),
        "precision_at_top_decile": precision_at_10,
        "recall_at_top_decile": recall_at_10,
        "top_decile_n": k,
        "pr_curve_points": len(precision),
    }

    print(f"\n=== {label} ===")
    print(f"ROC-AUC:              {roc:.4f}")
    print(f"PR-AUC:               {pr_auc:.4f}")
    print(f"Precision @ top 10%:  {precision_at_10:.4f}")
    print(f"Recall @ top 10%:     {recall_at_10:.4f}  (n_flagged={k:,})")
    return metrics


def xgboost_feature_importance(model: Pipeline, feature_names: list[str]) -> pd.DataFrame:
    """Gain-based feature importance from the fitted XGBClassifier."""
    clf: XGBClassifier = model.named_steps["clf"]
    # sklearn interface importance (gain by default for XGBClassifier in recent versions)
    importances = clf.feature_importances_
    imp = (
        pd.DataFrame({"feature": feature_names, "importance": importances})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    return imp


def assign_risk_tiers(proba: np.ndarray) -> pd.Series:
    """
    Business-oriented tiers on the scored population:
      High   = top 10% of predicted risk  (>= 90th percentile)
      Medium = next 20%                   (70th–90th percentile)
      Low    = remaining 70%              (< 70th percentile)
    """
    p70, p90 = np.quantile(proba, [0.70, 0.90])
    tiers = np.full(len(proba), "Low", dtype=object)
    tiers[proba >= p70] = "Medium"
    tiers[proba >= p90] = "High"
    return pd.Series(tiers)


def score_full_population(
    model: Pipeline,
    df_all: pd.DataFrame,
) -> pd.DataFrame:
    """Score all borrowers (train + test) and attach risk_tier."""
    prepared = prepare_feature_frame(df_all)
    X_all = prepared[NUMERIC_FEATURES]
    scored = df_all.copy()
    scored["default_proba"] = predict_proba_positive(model, X_all)
    scored["risk_tier"] = assign_risk_tiers(scored["default_proba"].to_numpy())
    return scored


def fit_kaplan_meier(df):
    """Fit a Kaplan-Meier estimator (implemented in a later survival prompt)."""
    raise NotImplementedError("Survival analysis comes in a later prompt")


def fit_cox_model(df):
    """Fit a Cox PH model (implemented in a later survival prompt)."""
    raise NotImplementedError("Survival analysis comes in a later prompt")


def main():
    print(f"Loading {PROCESSED_DATA_PATH}")
    df = load_features(PROCESSED_DATA_PATH)
    print(f"Combined rows: {len(df):,} (200K+ confirmed: {len(df) >= 200_000})")

    labeled = df.loc[df["source_flag"] == "train"].copy()
    print(f"Labeled train subset: {len(labeled):,}")
    print(
        "Class balance:",
        labeled["serious_dlq_2yrs"].value_counts(normalize=True).round(4).to_dict(),
    )

    labeled = prepare_feature_frame(labeled)
    X, y = build_xy(labeled)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        stratify=y,
        random_state=RANDOM_STATE,
    )
    print(
        f"Stratified split 80/20 — "
        f"train={len(X_train):,} (pos={y_train.mean():.4f}), "
        f"holdout={len(X_test):,} (pos={y_test.mean():.4f})"
    )

    baseline = train_baseline_model(X_train, y_train)
    baseline_metrics = evaluate_classifier(
        baseline, X_test, y_test, label="Logistic Regression (baseline)"
    )

    xgb_model = train_xgboost_model(X_train, y_train)
    xgb_metrics = evaluate_classifier(
        xgb_model, X_test, y_test, label="XGBoost (main)"
    )

    importance = xgboost_feature_importance(xgb_model, NUMERIC_FEATURES)
    top10 = importance.head(10)
    print("\n=== Top-10 XGBoost feature importances ===")
    print(top10.to_string(index=False))

    top10_features = set(top10["feature"])
    present = sorted(RESUME_FEATURES & top10_features)
    missing = sorted(RESUME_FEATURES - top10_features)
    print("\n=== Resume-feature check (top-10) ===")
    print(f"Present in top-10: {present or 'none'}")
    if missing:
        # Check ranks even if outside top-10
        ranks = {
            f: int(importance.index[importance["feature"] == f][0]) + 1
            for f in RESUME_FEATURES
            if f in set(importance["feature"])
        }
        print(f"Not in top-10: {missing} (full ranks: {ranks})")
        print(
            "Honest note: not every resume-named feature made the top-10; "
            "report ranks above rather than cherry-picking a chart."
        )
    else:
        print(
            "All resume-named features "
            "(payment_to_income_ratio, prior_delinquency_count, "
            "revolving_utilization / bucket) appear in the top-10."
        )

    print("\n=== Scoring full combined population ===")
    scored = score_full_population(xgb_model, df)
    SCORED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    scored.to_csv(SCORED_DATA_PATH, index=False)

    tier_counts = scored["risk_tier"].value_counts().reindex(["Low", "Medium", "High"])
    print(f"Wrote {SCORED_DATA_PATH} — {len(scored):,} rows")
    print("\n=== Risk tier counts (full 200K+ population) ===")
    for tier, n in tier_counts.items():
        pct = 100.0 * n / len(scored)
        print(f"  {tier:6s}: {n:,} ({pct:.1f}%)")

    # Summary block for easy paste
    print("\n========== PASTE SUMMARY ==========")
    print(
        f"LogReg  ROC-AUC={baseline_metrics['roc_auc']:.4f}  "
        f"PR-AUC={baseline_metrics['pr_auc']:.4f}"
    )
    print(
        f"XGBoost ROC-AUC={xgb_metrics['roc_auc']:.4f}  "
        f"PR-AUC={xgb_metrics['pr_auc']:.4f}  "
        f"P@10%={xgb_metrics['precision_at_top_decile']:.4f}  "
        f"R@10%={xgb_metrics['recall_at_top_decile']:.4f}"
    )
    print("Top-10 features:")
    for i, row in top10.iterrows():
        print(f"  {i+1:2d}. {row['feature']}: {row['importance']:.4f}")
    print("Tier counts:")
    for tier, n in tier_counts.items():
        print(f"  {tier}: {n}")
    print("===================================")


if __name__ == "__main__":
    # Ensure relative paths resolve from repo root
    os.chdir(_PROJECT_ROOT)
    main()

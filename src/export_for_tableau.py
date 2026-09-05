"""
export_for_tableau.py
=====================
Export clean CSVs under dashboard/data/ for Tableau Public.

Outputs:
  1. delinquency_by_tier_utilization.csv  — labeled train only
  2. collections_funnel.csv               — model-projected funnel stages
  3. survival_by_tier.csv                 — Kaplan–Meier on CONSTRUCTED durations

Usage:
    python src/export_for_tableau.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter

ROOT = Path(__file__).resolve().parents[1]
SCORED_PATH = ROOT / "data" / "processed" / "scored_borrowers.csv"
OUT_DIR = ROOT / "dashboard" / "data"

# Collections assumptions aligned with the planned Excel cost model (Prompt 7).
# Success rate is an industry-benchmark-style ASSUMPTION, not observed data.
SUCCESS_RATE_PAYMENT_PLAN = 0.20
CONTACT_FRACTION = 1.0  # intervene on 100% of borrowers in each tier (Sheet 2 policy)

# Survival construction (NOT observed time — see README Data & Methodology Notes).
OBSERVATION_MONTHS = 24
BUCKET_ORD = {"Low (<30%)": 0, "Medium (30-70%)": 1, "High (>70%)": 2}
TIER_ORDER = ["Low", "Medium", "High"]
STAGE_ORDER = ["flagged", "contacted", "recovered", "written_off"]


def load_scored(path: Path = SCORED_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def export_delinquency_by_tier_utilization(df: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    """Labeled train only: counts + default rate by risk_tier × utilization bucket."""
    train = df.loc[df["source_flag"] == "train"].copy()
    grouped = (
        train.groupby(["risk_tier", "revolving_utilization_bucket"], as_index=False)
        .agg(
            count=("serious_dlq_2yrs", "size"),
            defaults=("serious_dlq_2yrs", "sum"),
        )
    )
    grouped["default_rate"] = grouped["defaults"] / grouped["count"]
    grouped = grouped.drop(columns=["defaults"])

    # Stable sort for Tableau
    grouped["risk_tier"] = pd.Categorical(grouped["risk_tier"], TIER_ORDER, ordered=True)
    util_order = ["Low (<30%)", "Medium (30-70%)", "High (>70%)"]
    grouped["revolving_utilization_bucket"] = pd.Categorical(
        grouped["revolving_utilization_bucket"], util_order, ordered=True
    )
    grouped = grouped.sort_values(["risk_tier", "revolving_utilization_bucket"]).reset_index(
        drop=True
    )
    # Write as plain strings for Tableau
    out = grouped.astype(
        {"risk_tier": str, "revolving_utilization_bucket": str, "count": int}
    )
    path = out_dir / "delinquency_by_tier_utilization.csv"
    out.to_csv(path, index=False)
    print(f"Wrote {path} ({len(out)} rows)")
    return out


def export_collections_funnel(df: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    """
    Funnel stages per risk_tier using Prompt 7–style projections.

    Stages:
      flagged     — all borrowers in the tier (model-flagged population)
      contacted   — flagged × CONTACT_FRACTION (early-intervention outreach)
      recovered   — MODEL-PROJECTED prevented defaults
                    = contacted × mean(default_proba) × success_rate
      written_off — MODEL-PROJECTED residual defaults after intervention
                    = contacted × mean(default_proba) × (1 − success_rate)

    recovered / written_off are NOT observed outcomes — they are cost-model projections.
    """
    tier_stats = (
        df.groupby("risk_tier", as_index=False)
        .agg(
            n_tier=("id", "size"),
            predicted_default_rate=("default_proba", "mean"),
        )
    )

    rows = []
    for row in tier_stats.itertuples(index=False):
        flagged = float(row.n_tier)
        contacted = flagged * CONTACT_FRACTION
        expected_defaults = contacted * float(row.predicted_default_rate)
        recovered = expected_defaults * SUCCESS_RATE_PAYMENT_PLAN
        written_off = expected_defaults * (1.0 - SUCCESS_RATE_PAYMENT_PLAN)

        for stage, count in [
            ("flagged", flagged),
            ("contacted", contacted),
            ("recovered", recovered),
            ("written_off", written_off),
        ]:
            rows.append(
                {
                    "risk_tier": row.risk_tier,
                    "stage": stage,
                    "count": round(count, 1),
                    "stage_type": (
                        "observed_model_flag"
                        if stage in ("flagged", "contacted")
                        else "model_projected"
                    ),
                    "notes": (
                        "Borrowers in tier / assumed contacted under 100% outreach policy."
                        if stage in ("flagged", "contacted")
                        else (
                            "MODEL-PROJECTED (not observed): prevented defaults "
                            f"at success_rate={SUCCESS_RATE_PAYMENT_PLAN:.0%} payment-plan assumption."
                            if stage == "recovered"
                            else (
                                "MODEL-PROJECTED (not observed): residual defaults after "
                                f"intervention at (1−success_rate)={1 - SUCCESS_RATE_PAYMENT_PLAN:.0%}."
                            )
                        )
                    ),
                }
            )

    out = pd.DataFrame(rows)
    out["risk_tier"] = pd.Categorical(out["risk_tier"], TIER_ORDER, ordered=True)
    out["stage"] = pd.Categorical(out["stage"], STAGE_ORDER, ordered=True)
    out = out.sort_values(["risk_tier", "stage"]).reset_index(drop=True)
    out["risk_tier"] = out["risk_tier"].astype(str)
    out["stage"] = out["stage"].astype(str)

    path = out_dir / "collections_funnel.csv"
    out.to_csv(path, index=False)
    print(f"Wrote {path} ({len(out)} rows)")
    print(
        "  NOTE: recovered/written_off are model-projected from "
        f"P(default)×success_rate={SUCCESS_RATE_PAYMENT_PLAN:.0%} — not observed outcomes."
    )
    return out


def construct_duration(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deterministic constructed time-to-default (NOT observed).

    Rule (documented for honesty):
      - Observation window = 24 months.
      - Event = serious_dlq_2yrs == 1; non-events are right-censored at 24.
      - For events, duration_months is a deterministic function of risk severity so
        higher prior delinquency / utilization map to earlier constructed defaults:
            util_ord ∈ {0,1,2}
            severity = prior_delinquency_count + 2 * util_ord
            duration_months = clip(24 - 2 * severity, 1, 23)
      - This produces illustrative KM curves by risk tier; never label as observed time.
    """
    out = df.copy()
    util_ord = out["revolving_utilization_bucket"].map(BUCKET_ORD).fillna(0).astype(int)
    severity = out["prior_delinquency_count"].fillna(0).astype(float) + 2.0 * util_ord
    event_duration = np.clip(24 - 2 * severity, 1, 23).round().astype(int)

    event = out["serious_dlq_2yrs"].fillna(0).astype(int)
    out["event"] = event
    out["duration_months"] = np.where(event == 1, event_duration, OBSERVATION_MONTHS)
    out["duration_is_constructed"] = True
    return out


def export_survival_by_tier(df: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    """Kaplan–Meier survival curves by risk_tier on constructed durations (train labels)."""
    train = df.loc[df["source_flag"] == "train"].copy()
    train = construct_duration(train)

    # Timeline grid for a smooth Tableau line chart
    timeline = np.arange(0, OBSERVATION_MONTHS + 1, 1)
    frames = []

    for tier in TIER_ORDER:
        subset = train.loc[train["risk_tier"] == tier]
        if subset.empty:
            continue
        kmf = KaplanMeierFitter(label=tier)
        kmf.fit(
            durations=subset["duration_months"],
            event_observed=subset["event"],
            timeline=timeline,
        )
        surv = kmf.survival_function_.reindex(timeline).ffill().bfill()
        frames.append(
            pd.DataFrame(
                {
                    "risk_tier": tier,
                    "time_months": timeline.astype(int),
                    "survival_probability": surv.iloc[:, 0].to_numpy(),
                    "duration_source": "constructed_deterministic_not_observed",
                }
            )
        )

    out = pd.concat(frames, ignore_index=True)
    path = out_dir / "survival_by_tier.csv"
    out.to_csv(path, index=False)
    print(f"Wrote {path} ({len(out)} rows)")
    print(
        "  NOTE: duration_months is CONSTRUCTED (deterministic rule), not observed "
        "time-to-default — label the Tableau chart accordingly."
    )
    return out


def main() -> None:
    print(f"Loading {SCORED_PATH}")
    df = load_scored()
    print(f"Rows: {len(df):,} | tiers: {df['risk_tier'].value_counts().to_dict()}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    d1 = export_delinquency_by_tier_utilization(df, OUT_DIR)
    d2 = export_collections_funnel(df, OUT_DIR)
    d3 = export_survival_by_tier(df, OUT_DIR)

    print("\n=== Preview ===")
    print("\n[delinquency_by_tier_utilization]")
    print(d1.to_string(index=False))
    print("\n[collections_funnel]")
    print(d2[["risk_tier", "stage", "count", "stage_type"]].to_string(index=False))
    print("\n[survival_by_tier] head")
    print(d3.groupby("risk_tier").head(3).to_string(index=False))
    print(f"\nAll Tableau CSVs written under {OUT_DIR}/")


if __name__ == "__main__":
    main()

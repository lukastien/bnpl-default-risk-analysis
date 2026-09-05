"""
etl_pipeline.py
================
Loads the raw "Give Me Some Credit" dataset, cleans it, engineers
BNPL-relevant features, and writes processed output to CSV
(SQLite load still TBD — see sql/schema.sql).

Usage:
    python src/etl_pipeline.py
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path

RAW_TRAIN_PATH = Path("data/raw/cs-training.csv")
RAW_TEST_PATH = Path("data/raw/cs-test.csv")
PROCESSED_DATA_PATH = Path("data/processed/credit_data_clean.csv")
DB_PATH = Path("data/processed/credit_risk.db")

# 99th-percentile caps for continuous outliers (computed on the combined frame).
OUTLIER_CAP_QUANTILE = 0.99

# GMSC data-entry codes that are not real late-payment counts.
LATE_COUNT_ARTIFACT_CODES = {96, 98}

COLUMN_RENAME = {
    "Id": "id",
    "index": "id",
    "Unnamed: 0": "id",
    "SeriousDlqin2yrs": "serious_dlq_2yrs",
    "RevolvingUtilizationOfUnsecuredLines": "revolving_utilization",
    "age": "age",
    "NumberOfTime30-59DaysPastDueNotWorse": "times_30_59_days_late",
    "DebtRatio": "debt_ratio",
    "MonthlyIncome": "monthly_income",
    "NumberOfOpenCreditLinesAndLoans": "num_open_credit_lines",
    "NumberOfTimes90DaysLate": "times_90_days_late",
    "NumberRealEstateLoansOrLines": "num_real_estate_loans",
    "NumberOfTime60-89DaysPastDueNotWorse": "times_60_89_days_late",
    "NumberOfDependents": "num_dependents",
    "source_flag": "source_flag",
}

LATE_COUNT_COLS = [
    "times_30_59_days_late",
    "times_60_89_days_late",
    "times_90_days_late",
]


def load_raw_data(
    train_path: Path = RAW_TRAIN_PATH,
    test_path: Path = RAW_TEST_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load the labeled training set and unlabeled Kaggle test set.

    Returns
    -------
    train_df, test_df
        Separate DataFrames. Training has SeriousDlqin2yrs labels;
        test has the same columns but an empty (NaN) target.
    """
    train_df = pd.read_csv(train_path, index_col=0)
    test_df = pd.read_csv(test_path, index_col=0)
    return train_df, test_df


def combine_train_test(train_df: pd.DataFrame, test_df: pd.DataFrame) -> pd.DataFrame:
    """Concatenate train + test with a source_flag so we can always split back out."""
    train = train_df.reset_index().copy()
    test = test_df.reset_index().copy()
    # Source files use an unnamed leading id column; normalize before snake_case rename.
    for frame in (train, test):
        if frame.columns[0] in ("index", "Unnamed: 0", "Id"):
            frame.rename(columns={frame.columns[0]: "Id"}, inplace=True)
    train["source_flag"] = "train"
    test["source_flag"] = "test"
    return pd.concat([train, test], ignore_index=True)


def _age_bucket(age: pd.Series) -> pd.Series:
    """Coarse age buckets used as an income proxy for stratified median imputation."""
    return pd.cut(
        age,
        bins=[-float("inf"), 30, 45, 60, float("inf")],
        labels=["under_30", "30_44", "45_59", "60_plus"],
        right=False,
    )


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize the combined train+test dataset.

    Steps: snake_case rename → age==0 fix → income/dependents imputation →
    DebtRatio / utilization capping → GMSC 96/98 late-count artifact handling.
    """
    out = df.copy()

    # --- 1. Snake_case column names (aligned with sql/schema.sql) ---
    out = out.rename(columns=COLUMN_RENAME)
    # Defensive: any leftover CamelCase / hyphenated names
    out.columns = [
        c if c in COLUMN_RENAME.values() else c.lower().replace("-", "_")
        for c in out.columns
    ]

    # --- 4. Fix age == 0 before age-bucketed income imputation ---
    # (Listed as step 4 in the prompt; applied early so stratified income medians
    # are not polluted by invalid ages.)
    age_zero_mask = out["age"] == 0
    n_age_zero = int(age_zero_mask.sum())
    if n_age_zero:
        median_age = float(out.loc[~age_zero_mask, "age"].median())
        out.loc[age_zero_mask, "age"] = median_age
    print(f"[clean] age == 0 treated as missing and imputed with median age: {n_age_zero:,} rows")

    # --- 2. Impute MonthlyIncome (~20% missing) by age-bucket median ---
    income_missing = out["monthly_income"].isna()
    n_income_imputed = int(income_missing.sum())
    out["_age_bucket"] = _age_bucket(out["age"]).astype(str)
    bucket_medians = (
        out.loc[~income_missing]
        .groupby("_age_bucket", observed=True)["monthly_income"]
        .median()
        .to_dict()
    )
    global_income_median = float(out.loc[~income_missing, "monthly_income"].median())
    imputed_income = out.loc[income_missing, "_age_bucket"].map(bucket_medians)
    out.loc[income_missing, "monthly_income"] = (
        imputed_income.fillna(global_income_median).astype(float)
    )
    out = out.drop(columns=["_age_bucket"])
    print(
        f"[clean] monthly_income imputed (age-bucket median, "
        f"fallback global median={global_income_median:,.0f}): {n_income_imputed:,} values"
    )

    # --- 3. Impute NumberOfDependents with mode (typically 0) ---
    dep_missing = out["num_dependents"].isna()
    n_dep_imputed = int(dep_missing.sum())
    dep_mode = float(out.loc[~dep_missing, "num_dependents"].mode().iloc[0])
    out.loc[dep_missing, "num_dependents"] = dep_mode
    print(f"[clean] num_dependents imputed with mode={dep_mode:g}: {n_dep_imputed:,} values")

    # --- 5. Cap extreme DebtRatio and revolving utilization at 99th percentile ---
    for col in ("debt_ratio", "revolving_utilization"):
        cap = float(out[col].quantile(OUTLIER_CAP_QUANTILE))
        before_max = float(out[col].max())
        above = out[col] > cap
        n_capped = int(above.sum())
        out.loc[above, col] = cap
        after_max = float(out[col].max())
        print(
            f"[clean] {col} capped at {OUTLIER_CAP_QUANTILE:.0%}ile "
            f"({cap:.4f}): {n_capped:,} rows | max {before_max:.4f} → {after_max:.4f}"
        )

    # --- 6. GMSC late-count artifact (96 / 98 are data-entry codes, not real counts) ---
    # Decision: flag affected rows, then replace 96/98 with the column median of
    # non-artifact values so downstream sums (prior_delinquency_count) stay on a
    # realistic scale instead of treating 96/98 as literal delinquency counts.
    artifact_mask = pd.Series(False, index=out.index)
    for col in LATE_COUNT_COLS:
        col_artifact = out[col].isin(LATE_COUNT_ARTIFACT_CODES)
        artifact_mask |= col_artifact
        valid_median = float(out.loc[~col_artifact, col].median())
        out.loc[col_artifact, col] = valid_median
    out["late_payment_code_artifact"] = artifact_mask.astype(int)
    n_artifact = int(artifact_mask.sum())
    print(
        f"[clean] late-count 96/98 artifact flagged + replaced with non-artifact median: "
        f"{n_artifact:,} rows"
    )

    return out


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer BNPL-relevant features on the cleaned combined dataset.
    """
    out = df.copy()

    # --- 1. payment_to_income_ratio (resume-named payment-burden feature) ---
    # Exact formula:
    #   estimated_monthly_debt_payment = debt_ratio * monthly_income
    #   payment_to_income_ratio = estimated_monthly_debt_payment / monthly_income
    #                             (NaN when monthly_income == 0)
    #
    # In Give Me Some Credit, DebtRatio is already defined as monthly debt payments
    # divided by monthly income when income is reported — so for monthly_income > 0
    # this equals debt_ratio algebraically. We still materialize it as an explicit
    # named feature (payment-to-income ratio) for interpretability and the resume claim,
    # with a safe divide for any remaining zero-income rows.
    estimated_monthly_debt_payment = out["debt_ratio"] * out["monthly_income"]
    out["payment_to_income_ratio"] = estimated_monthly_debt_payment / out["monthly_income"].replace(
        0, pd.NA
    )
    out["payment_to_income_ratio"] = pd.to_numeric(out["payment_to_income_ratio"], errors="coerce")

    # --- 2. prior_delinquency_count (post artifact-handling late counts) ---
    out["prior_delinquency_count"] = (
        out["times_30_59_days_late"]
        + out["times_60_89_days_late"]
        + out["times_90_days_late"]
    )

    # --- 3. revolving_utilization_bucket ---
    out["revolving_utilization_bucket"] = pd.cut(
        out["revolving_utilization"],
        bins=[-float("inf"), 0.30, 0.70, float("inf")],
        labels=["Low (<30%)", "Medium (30-70%)", "High (>70%)"],
        right=False,
    )

    _print_feature_summaries(out)
    return out


def _print_feature_summaries(df: pd.DataFrame) -> None:
    """Print mean/median/distribution for engineered features by source_flag."""
    print("\n=== Engineered feature summary (by source_flag) ===")
    for source in ("train", "test"):
        subset = df.loc[df["source_flag"] == source]
        print(f"\n--- {source} (n={len(subset):,}) ---")

        pti = subset["payment_to_income_ratio"]
        print(
            f"payment_to_income_ratio: mean={pti.mean():.4f}  "
            f"median={pti.median():.4f}  "
            f"p25={pti.quantile(0.25):.4f}  p75={pti.quantile(0.75):.4f}  "
            f"nulls={pti.isna().sum()}"
        )

        pdc = subset["prior_delinquency_count"]
        print(
            f"prior_delinquency_count: mean={pdc.mean():.4f}  "
            f"median={pdc.median():.4f}  "
            f"min={pdc.min():.0f}  max={pdc.max():.0f}"
        )
        print("  value distribution (top counts):")
        vc = pdc.value_counts().sort_index().head(10)
        for val, cnt in vc.items():
            print(f"  {val:g}: {cnt:,}")

        bucket = subset["revolving_utilization_bucket"]
        print("revolving_utilization_bucket distribution:")
        dist = bucket.value_counts(dropna=False).sort_index()
        pct = bucket.value_counts(normalize=True, dropna=False).sort_index()
        for label in dist.index:
            print(f"  {label}: {dist[label]:,} ({100 * pct[label]:.1f}%)")


def load_to_sqlite(
    df: pd.DataFrame,
    db_path: Path = DB_PATH,
    schema_path: Path = Path("sql/schema.sql"),
) -> Path:
    """
    Create data/processed/credit_risk.db from sql/schema.sql and load the
    cleaned combined DataFrame into borrowers.
    """
    import re
    import sqlite3

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    schema_sql = schema_path.read_text()
    # Strip full-line and trailing inline SQL comments so ';' inside comments
    # cannot split CREATE TABLE. Keep only DROP/CREATE for DDL execution.
    cleaned_lines = []
    for line in schema_sql.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("--"):
            continue
        if "--" in line:
            line = line[: line.index("--")]
        cleaned_lines.append(line)
    no_comments = "\n".join(cleaned_lines)
    ddl_statements = [
        stmt.strip()
        for stmt in no_comments.split(";")
        if re.match(r"(?is)^(DROP|CREATE)\b", stmt.strip() or "")
    ]
    if len(ddl_statements) < 2:
        raise RuntimeError(f"Expected DROP+CREATE in {schema_path}, got: {ddl_statements!r}")

    conn = sqlite3.connect(db_path)
    try:
        for stmt in ddl_statements:
            conn.execute(stmt)

        load_df = df.copy()
        # SQLite INTEGER NULL for unlabeled test rows (pandas NaN → None).
        if "serious_dlq_2yrs" in load_df.columns:
            load_df["serious_dlq_2yrs"] = load_df["serious_dlq_2yrs"].astype("Int64")

        load_df.to_sql("borrowers", conn, if_exists="append", index=False)
        conn.commit()

        n_rows = conn.execute("SELECT COUNT(*) FROM borrowers").fetchone()[0]
        n_train = conn.execute(
            "SELECT COUNT(*) FROM borrowers WHERE source_flag = 'train'"
        ).fetchone()[0]
        n_test = conn.execute(
            "SELECT COUNT(*) FROM borrowers WHERE source_flag = 'test'"
        ).fetchone()[0]
        n_test_null_label = conn.execute(
            """
            SELECT COUNT(*) FROM borrowers
            WHERE source_flag = 'test' AND serious_dlq_2yrs IS NULL
            """
        ).fetchone()[0]
        print(
            f"[sqlite] Wrote {db_path} — {n_rows:,} rows "
            f"(train={n_train:,}, test={n_test:,}, "
            f"test labels NULL={n_test_null_label:,})"
        )
    finally:
        conn.close()

    return db_path


def run_exploratory_queries(db_path: Path = DB_PATH) -> None:
    """Run the five labeled-train exploratory queries and print results."""
    import sqlite3

    queries = {
        "1. Overall default rate (train only)": """
            SELECT
                COUNT(*) AS borrower_count,
                SUM(serious_dlq_2yrs) AS defaults,
                ROUND(100.0 * SUM(serious_dlq_2yrs) / COUNT(*), 2) AS default_rate_pct
            FROM borrowers
            WHERE source_flag = 'train';
        """,
        "2. Default rate by revolving_utilization_bucket": """
            SELECT
                revolving_utilization_bucket,
                COUNT(*) AS borrower_count,
                ROUND(100.0 * SUM(serious_dlq_2yrs) / COUNT(*), 2) AS default_rate_pct
            FROM borrowers
            WHERE source_flag = 'train'
            GROUP BY revolving_utilization_bucket
            ORDER BY
                CASE revolving_utilization_bucket
                    WHEN 'Low (<30%)' THEN 1
                    WHEN 'Medium (30-70%)' THEN 2
                    WHEN 'High (>70%)' THEN 3
                    ELSE 4
                END;
        """,
        "3. Default rate by prior_delinquency_count bucket": """
            SELECT
                CASE
                    WHEN prior_delinquency_count = 0 THEN '0'
                    WHEN prior_delinquency_count BETWEEN 1 AND 2 THEN '1-2'
                    WHEN prior_delinquency_count BETWEEN 3 AND 5 THEN '3-5'
                    ELSE '6+'
                END AS prior_delinquency_bucket,
                COUNT(*) AS borrower_count,
                ROUND(100.0 * SUM(serious_dlq_2yrs) / COUNT(*), 2) AS default_rate_pct
            FROM borrowers
            WHERE source_flag = 'train'
            GROUP BY prior_delinquency_bucket
            ORDER BY
                CASE
                    WHEN prior_delinquency_bucket = '0' THEN 1
                    WHEN prior_delinquency_bucket = '1-2' THEN 2
                    WHEN prior_delinquency_bucket = '3-5' THEN 3
                    ELSE 4
                END;
        """,
        "4. Default rate by age decade": """
            SELECT
                CAST(age / 10 * 10 AS INTEGER) AS age_decade_start,
                COUNT(*) AS borrower_count,
                ROUND(100.0 * SUM(serious_dlq_2yrs) / COUNT(*), 2) AS default_rate_pct
            FROM borrowers
            WHERE source_flag = 'train'
            GROUP BY age_decade_start
            ORDER BY age_decade_start;
        """,
        "5. Avg payment_to_income_ratio by default status": """
            SELECT
                serious_dlq_2yrs,
                COUNT(*) AS borrower_count,
                ROUND(AVG(payment_to_income_ratio), 4) AS avg_payment_to_income_ratio
            FROM borrowers
            WHERE source_flag = 'train'
            GROUP BY serious_dlq_2yrs;
        """,
    }

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        print("\n=== Exploratory SQL results (train-labeled only) ===")
        for title, sql in queries.items():
            print(f"\n{title}")
            cur = conn.execute(sql)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            print("  " + " | ".join(cols))
            for row in rows:
                print("  " + " | ".join(str(row[c]) for c in cols))
    finally:
        conn.close()


def main():
    train_df, test_df = load_raw_data()
    n_train = len(train_df)
    n_test = len(test_df)
    n_combined = n_train + n_test

    print(f"Training set ({RAW_TRAIN_PATH}): {n_train:,} rows (labeled)")
    print(f"Test set     ({RAW_TEST_PATH}): {n_test:,} rows (unlabeled)")
    print(f"Combined total: {n_combined:,} rows")
    print(f"200K+ confirmed: {n_combined >= 200_000}")

    # Prefer loading the already-written cleaned CSV when present (faster iteration).
    if PROCESSED_DATA_PATH.exists():
        print(f"\nLoading cleaned data from {PROCESSED_DATA_PATH}")
        df_features = pd.read_csv(PROCESSED_DATA_PATH)
    else:
        combined = combine_train_test(train_df, test_df)
        print(f"\nCombined frame with source_flag: {len(combined):,} rows")
        df_clean = clean_data(combined)
        df_features = engineer_features(df_clean)
        PROCESSED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        df_features.to_csv(PROCESSED_DATA_PATH, index=False)
        print(
            f"\nWrote {PROCESSED_DATA_PATH} — "
            f"shape {df_features.shape[0]:,} rows × {df_features.shape[1]} columns"
        )

    load_to_sqlite(df_features, DB_PATH)
    run_exploratory_queries(DB_PATH)


if __name__ == "__main__":
    main()

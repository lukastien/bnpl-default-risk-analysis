"""
etl_pipeline.py
================
Loads the raw "Give Me Some Credit" dataset, cleans it, engineers
BNPL-relevant features, and writes it into a local SQLite database
(see sql/schema.sql).

STATUS: placeholder stub — logic to be filled in.

Usage (once implemented):
    python src/etl_pipeline.py
"""

import pandas as pd
import sqlite3
from pathlib import Path

RAW_DATA_PATH = Path("data/raw/credit_data.csv")
PROCESSED_DATA_PATH = Path("data/processed/credit_data_clean.csv")
DB_PATH = Path("data/processed/credit_risk.db")


def load_raw_data(path: Path) -> pd.DataFrame:
    """Load the raw CSV export into a DataFrame."""
    df = pd.read_csv(path, index_col=0)  # first column is an unnamed row index in source file
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize the raw dataset.

    TODO:
      - Rename columns to snake_case matching sql/schema.sql
      - Handle missing MonthlyIncome (has real NaNs in source data —
        consider median imputation by age/dependents group)
      - Handle missing NumberOfDependents
      - Filter or cap extreme outliers in DebtRatio and age (source data
        has some known bad values, e.g. age = 0)
    """
    raise NotImplementedError("Fill in cleaning logic")


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer BNPL-relevant features.

    TODO:
      - payment_to_income_ratio (approximate from DebtRatio * MonthlyIncome)
      - prior_delinquency_count = sum of the three "times late" columns
      - revolving_utilization_bucket (low/medium/high)
    """
    raise NotImplementedError("Fill in feature engineering logic")


def load_to_sqlite(df: pd.DataFrame, db_path: Path):
    """Write the cleaned DataFrame into the SQLite database defined in sql/schema.sql."""
    raise NotImplementedError("Fill in database load logic")


def main():
    df_raw = load_raw_data(RAW_DATA_PATH)
    print(f"Loaded {len(df_raw)} rows from {RAW_DATA_PATH}")

    # df_clean = clean_data(df_raw)
    # df_features = engineer_features(df_clean)
    # df_features.to_csv(PROCESSED_DATA_PATH, index=False)
    # load_to_sqlite(df_features, DB_PATH)
    print("TODO: implement clean_data(), engineer_features(), and load_to_sqlite()")


if __name__ == "__main__":
    main()

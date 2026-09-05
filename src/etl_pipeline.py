"""
etl_pipeline.py
================
Loads the raw "Give Me Some Credit" dataset, cleans it, engineers
BNPL-relevant features, and writes it into a local SQLite database
(see sql/schema.sql).

STATUS: placeholder stub — load step implemented; cleaning / features TBD.

Usage (once fully implemented):
    python src/etl_pipeline.py
"""

import pandas as pd
import sqlite3
from pathlib import Path

RAW_TRAIN_PATH = Path("data/raw/cs-training.csv")
RAW_TEST_PATH = Path("data/raw/cs-test.csv")
PROCESSED_DATA_PATH = Path("data/processed/credit_data_clean.csv")
DB_PATH = Path("data/processed/credit_risk.db")


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
    train_df, test_df = load_raw_data()
    n_train = len(train_df)
    n_test = len(test_df)
    n_combined = n_train + n_test

    print(f"Training set ({RAW_TRAIN_PATH}): {n_train:,} rows (labeled)")
    print(f"Test set     ({RAW_TEST_PATH}): {n_test:,} rows (unlabeled)")
    print(f"Combined total: {n_combined:,} rows")
    print(f"200K+ confirmed: {n_combined >= 200_000}")

    # df_clean = clean_data(...)
    # df_features = engineer_features(df_clean)
    # df_features.to_csv(PROCESSED_DATA_PATH, index=False)
    # load_to_sqlite(df_features, DB_PATH)
    print("TODO: implement clean_data(), engineer_features(), and load_to_sqlite()")


if __name__ == "__main__":
    main()

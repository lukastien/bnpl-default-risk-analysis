"""
model_training.py
==================
Trains and evaluates models for BNPL/installment default risk:

  1. Classification: Logistic Regression baseline + XGBoost — predicts
     whether a borrower defaults (binary).
  2. Survival Analysis: Kaplan-Meier + Cox Proportional Hazards (lifelines)
     — models *when* default is likely to occur, not just whether.

STATUS: placeholder stub — logic to be filled in.

Note on survival analysis: the source dataset doesn't include an explicit
"time to default" column, since it wasn't built for survival analysis
originally. A defensible approach: simulate a plausible time-to-event
value (e.g., uniformly distributed over the observation window for
defaulters, censored at window end for non-defaulters) OR restrict the
survival analysis framing to a clearly-labeled illustrative extension.
Document whichever approach is used clearly in the notebook and README —
do not present a simulated time variable as if it were observed data.

Usage (once implemented):
    python src/model_training.py
"""

import pandas as pd
from pathlib import Path

# from sklearn.model_selection import train_test_split
# from sklearn.linear_model import LogisticRegression
# from sklearn.metrics import roc_auc_score, precision_recall_curve, classification_report
# from xgboost import XGBClassifier
# from lifelines import KaplanMeierFitter, CoxPHFitter

PROCESSED_DATA_PATH = Path("data/processed/credit_data_clean.csv")


def load_features(path: Path) -> pd.DataFrame:
    """Load the cleaned, feature-engineered dataset ready for modeling."""
    return pd.read_csv(path)


def train_baseline_model(X_train, y_train):
    """Train a logistic regression baseline."""
    raise NotImplementedError


def train_xgboost_model(X_train, y_train):
    """Train the main XGBoost classifier."""
    raise NotImplementedError


def evaluate_classifier(model, X_test, y_test):
    """Evaluate a trained classifier: ROC-AUC, precision/recall, confusion matrix."""
    raise NotImplementedError


def fit_kaplan_meier(df):
    """Fit a Kaplan-Meier estimator to visualize overall survival (non-default) curve."""
    raise NotImplementedError


def fit_cox_model(df):
    """Fit a Cox Proportional Hazards model to identify which features accelerate time-to-default."""
    raise NotImplementedError


def main():
    print("TODO: implement full training pipeline (classification + survival analysis)")


if __name__ == "__main__":
    main()

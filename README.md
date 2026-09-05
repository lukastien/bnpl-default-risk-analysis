# BNPL Payment Default & Collections Risk Analysis

Modeling consumer credit default risk — including *when* default is likely to occur, not just whether — to inform a collections and intervention strategy for an installment/BNPL-style lending business.

> **Status:** 🚧 Placeholder scaffold — full analysis in progress. This repo currently contains the project structure, real source data, and stub code to be filled in.

## Business Question

Which borrowers are at the highest risk of missing a payment, how soon after origination does that risk peak, and where should collections resources be prioritized to minimize losses?

## Framing Note

This project uses the real, public **"Give Me Some Credit"** consumer credit dataset (~251,000 borrowers across labeled training and unlabeled Kaggle test files), which was built for a general credit-default prediction task. It's reframed here around an **installment/BNPL-style lending lens** — the same underlying techniques (default prediction, time-to-default modeling, collections cost-benefit analysis) apply directly to BNPL and installment lending, which is one of the fastest-growing fintech subsectors. The data itself is real; the BNPL framing is an applied lens, not a claim that this is actual BNPL transaction data.

## Data

Source: [Give Me Some Credit](https://www.kaggle.com/c/GiveMeSomeCredit) (public Kaggle competition data)

| File | Rows | Labels |
|------|------|--------|
| `data/raw/cs-training.csv` | 150,000 | Yes — `SeriousDlqin2yrs` (serious delinquency within 2 years) |
| `data/raw/cs-test.csv` | 101,503 | No — Kaggle submission set; target column is present but empty |
| **Combined** | **251,503** | Train labeled only |

(`data/raw/credit_data.csv` is a duplicate of the training file kept for backward compatibility.)

Key fields: revolving credit utilization, age, past-due history (30/60/90-day late counts), debt ratio, monthly income, number of open credit lines, number of dependents, and a binary serious-delinquency-within-2-years target (available on training rows only).

## Data & Methodology Notes

### Record count and the "200K+" claim

The Give Me Some Credit competition ships two files: a labeled training set (~150K) and an unlabeled test set (~101K) with no ground-truth default outcomes. This project treats them differently on purpose:

1. **Feature engineering** (payment-to-income ratio, prior delinquency count, revolving utilization bucket) runs on the **combined train + test set (~251,503 records)**. Features do not require labels, so using the full population is legitimate — and it is what makes the **"200K+ credit records"** claim accurate.
2. **Classifier training and evaluation** use **only the ~150,000 labeled training rows**, with a stratified train/test split *within* that labeled set. The unlabeled Kaggle file is never used to fit or evaluate the classifier, because there is no ground truth.
3. **Scoring / flagging** applies the trained model to the **full combined ~251,503-record population** at the end. "Flag high-risk borrowers before default" therefore refers to risk scores on the 200K+ population, not only the 150K used for training.

In short: engineer and score on 200K+; learn and validate only on the labeled 150K.

### Survival analysis honesty

The dataset has **no observed time-to-default** — only a binary 2-year serious-delinquency outcome. Survival duration in this project is a **constructed** variable, not an observed one. The deterministic rule (used by `src/export_for_tableau.py` for Kaplan–Meier curves) is:

- Observation window = 24 months; non-events are right-censored at 24.
- For events (`serious_dlq_2yrs = 1`):
  `severity = prior_delinquency_count + 2 * utilization_bucket_ord` (Low/Med/High → 0/1/2),
  `duration_months = clip(24 - 2 * severity, 1, 23)`.

It must **never** be described as real observed time in any report, chart, dashboard, or interview talking point. Treat Kaplan–Meier / Cox results as an illustrative time-to-event extension on constructed durations, clearly labeled as such.

## Project Structure

```
bnpl-default-risk-analysis/
├── data/
│   ├── raw/                       # cs-training.csv + cs-test.csv (unmodified)
│   └── processed/                 # Cleaned data + engineered features
├── sql/
│   └── schema.sql                 # Relational schema + exploratory queries
├── notebooks/
│   └── 01_eda_and_modeling.ipynb  # EDA, feature engineering, classification + survival modeling
├── src/
│   ├── etl_pipeline.py            # Data cleaning / loading script
│   └── model_training.py          # Classification + survival model training
├── excel/
│   └── collections_cost_model.xlsx (placeholder — to be built)
├── reports/
│   ├── market_research_brief.md
│   └── strategy_brief.md
├── dashboard/
│   ├── data/                      # Tableau-ready CSVs (from src/export_for_tableau.py)
│   └── README.md                  # Chart map + Tableau Public publish steps
├── requirements.txt
└── README.md
```

## Methodology (planned)

1. **Data Processing** — clean and load data into SQLite; engineer features (payment-to-income ratio, prior delinquency count, revolving utilization bucket) on the combined ~251K population
2. **Classification Modeling** — logistic regression baseline + XGBoost trained/evaluated on labeled ~150K only; score the full ~251K to flag high-risk borrowers; evaluate with ROC-AUC and precision/recall given class imbalance (~6.7% positive rate)
3. **Survival Analysis** — apply time-to-event modeling (`lifelines`, Kaplan-Meier / Cox Proportional Hazards) on a **constructed** (not observed) duration variable to estimate *when* high-risk borrowers are likely to default — see Data & Methodology Notes
4. **Collections Cost Modeling** — Excel model comparing early-intervention cost vs. write-off cost by risk tier
5. **Dashboard** — Tableau Public charts fed by `dashboard/data/*.csv` (delinquency, collections funnel, survival)
6. **Recommendation** — strategy brief proposing an intervention threshold by risk tier

## Tools

Python (pandas, scikit-learn, XGBoost, lifelines), SQL (SQLite), Excel, Tableau

## Status / To Do

- [x] Repo structure + real dataset sourced (train + unlabeled test; 251,503 combined)
- [x] Data & methodology notes (200K+ policy + survival caveat)
- [x] ETL pipeline (`src/etl_pipeline.py`)
- [x] SQL schema + exploratory queries (`sql/schema.sql`)
- [x] EDA + classification modeling
- [x] Survival KM curves for Tableau (constructed duration — see methodology notes)
- [ ] Collections cost-benefit Excel model
- [x] Tableau data exports (`dashboard/data/`) — publish URL TBD
- [ ] Strategy brief write-up

---
*This is a self-directed portfolio project using a real public dataset, reframed with a BNPL/installment-lending lens for illustrative analysis.*

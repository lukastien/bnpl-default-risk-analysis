# BNPL Payment Default & Collections Risk Analysis

Modeling consumer credit default risk — including *when* default is likely to occur, not just whether — to inform a collections and intervention strategy for an installment/BNPL-style lending business.

> **Status:** 🚧 Placeholder scaffold — full analysis in progress. This repo currently contains the project structure, real source data, and stub code to be filled in.

## Business Question

Which borrowers are at the highest risk of missing a payment, how soon after origination does that risk peak, and where should collections resources be prioritized to minimize losses?

## Framing Note

This project uses the real, public **"Give Me Some Credit"** consumer credit dataset (150,000 borrowers), which was built for a general credit-default prediction task. It's reframed here around an **installment/BNPL-style lending lens** — the same underlying techniques (default prediction, time-to-default modeling, collections cost-benefit analysis) apply directly to BNPL and installment lending, which is one of the fastest-growing fintech subsectors. The data itself is real; the BNPL framing is an applied lens, not a claim that this is actual BNPL transaction data.

## Data

Source: [Give Me Some Credit](https://github.com/vivekkalyan/give-me-some-credit) (public, ~150,000 records)

Key fields: revolving credit utilization, age, past-due history (30/60/90-day late counts), debt ratio, monthly income, number of open credit lines, number of dependents, and a binary serious-delinquency-within-2-years target.

Data source: `data/raw/credit_data.csv`

## Project Structure

```
bnpl-default-risk-analysis/
├── data/
│   ├── raw/                       # Original, unmodified dataset
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
│   └── README.md                  # Link to published Tableau dashboard
├── requirements.txt
└── README.md
```

## Methodology (planned)

1. **Data Processing** — clean and load data into SQLite; engineer features (payment-to-income ratio, prior delinquency count, revolving utilization bucket)
2. **Classification Modeling** — logistic regression baseline + XGBoost classifier to flag high-risk borrowers; evaluate with ROC-AUC and precision/recall given class imbalance (~6.7% positive rate)
3. **Survival Analysis** — apply time-to-event modeling (`lifelines`, Kaplan-Meier / Cox Proportional Hazards) to estimate *when* high-risk borrowers are likely to default, not just whether
4. **Collections Cost Modeling** — Excel model comparing early-intervention cost vs. write-off cost by risk tier
5. **Dashboard** — Tableau dashboard visualizing delinquency by risk tier and a collections funnel view
6. **Recommendation** — strategy brief proposing an intervention threshold by risk tier

## Tools

Python (pandas, scikit-learn, XGBoost, lifelines), SQL (SQLite), Excel, Tableau

## Status / To Do

- [x] Repo structure + real dataset sourced
- [ ] ETL pipeline (`src/etl_pipeline.py`)
- [ ] SQL schema + exploratory queries (`sql/schema.sql`)
- [ ] EDA + classification modeling
- [ ] Survival analysis (time-to-default)
- [ ] Collections cost-benefit Excel model
- [ ] Tableau dashboard
- [ ] Strategy brief write-up

---
*This is a self-directed portfolio project using a real public dataset, reframed with a BNPL/installment-lending lens for illustrative analysis.*

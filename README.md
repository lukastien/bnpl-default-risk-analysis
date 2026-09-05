# BNPL Payment Default & Collections Risk Analysis

Modeling consumer credit default risk — including *when* default is likely to occur (on a **constructed** duration), not just whether — to inform a collections and intervention strategy for an installment/BNPL-style lending business.

> **Status:** Core pipeline complete (ETL → EDA → classification → scoring → Tableau exports → strategy brief). Tableau Public URL and interactive Excel workbook remain optional publish steps.

## Business Question

Which borrowers are at the highest risk of missing a payment, how soon after “origination” that risk concentrates (illustrative KM on constructed time), and where should collections resources be prioritized to minimize losses?

## Framing Note

This project uses the real, public **"Give Me Some Credit"** consumer credit dataset (~251,000 borrowers across labeled training and unlabeled Kaggle test files), built for a general credit-default prediction task. It is reframed with an **installment/BNPL-style lending lens**. The data are real credit records; the BNPL framing is an applied lens, **not** a claim that these are Affirm/Klarna/Afterpay transactions.

## Data

Source: [Give Me Some Credit](https://www.kaggle.com/c/GiveMeSomeCredit) (public Kaggle competition data)

| File | Rows | Labels |
|------|------|--------|
| `data/raw/cs-training.csv` | 150,000 | Yes — `SeriousDlqin2yrs` (serious delinquency within 2 years) |
| `data/raw/cs-test.csv` | 101,503 | No — Kaggle submission set; target empty |
| **Combined** | **251,503** | Train labeled only |

### Record count policy (“200K+”)

- **Feature engineering and final scoring** use the **combined train + test set (251,503 records)**.  
- **Classifier training / evaluation** use **only the 150,000 labeled training rows** (stratified 80/20 split within that set).  
- Survival duration is **constructed**, never observed — see Data & Methodology Notes.

## Data & Methodology Notes

### Record count and the "200K+" claim

1. **Feature engineering** (payment-to-income ratio, prior delinquency count, revolving utilization bucket) runs on the **combined ~251,503 records**.  
2. **Classifier training and evaluation** use **only the ~150,000 labeled training rows**.  
3. **Scoring / flagging** applies the trained XGBoost model to the **full combined ~251,503-record population**.

In short: engineer and score on 200K+; learn and validate only on the labeled 150K.

### Survival analysis honesty

The dataset has **no observed time-to-default**. Duration is **constructed** with this deterministic rule (`src/export_for_tableau.py`):

- Window = 24 months; non-events censored at 24.  
- For events: `severity = prior_delinquency_count + 2 * utilization_bucket_ord`, `duration_months = clip(24 - 2 * severity, 1, 23)`.

Never describe KM curves as real observed time-to-default.

## Results

### Engineered features

On the combined 251,503 rows:

| Feature | Role |
|---------|------|
| `payment_to_income_ratio` | Explicit payment-burden feature (`debt_ratio × monthly_income / monthly_income`); equals `debt_ratio` when income &gt; 0. **Ranked #11** in XGBoost importance—secondary signal. |
| `prior_delinquency_count` | Sum of 30–59 / 60–89 / 90+ late counts (after 96/98 artifact handling). **#1 importance (0.408).** |
| `revolving_utilization_bucket` | Low (&lt;30%) / Medium (30–70%) / High (&gt;70%). Ordinal form **#2 importance (0.284)**; continuous utilization **#3 (0.072).** |

### Classification

- Train default rate (labeled): **6.68%**.  
- Logistic regression holdout: ROC-AUC **0.861**, PR-AUC **0.390**.  
- XGBoost holdout: ROC-AUC **0.869**, PR-AUC **0.404**; precision@top 10% **0.372**, recall@top 10% **0.557**.  
- Full population scored into tiers: Low **176,052** (70%), Medium **50,300** (20%), High **25,151** (10%).

### Time-to-default by tier (constructed duration)

Kaplan–Meier survival probability (train labels, constructed duration):

| Tier | S(6) | S(12) | S(24) |
|------|-----:|------:|------:|
| Low | 1.00 | 1.00 | 0.985 |
| Medium | 1.00 | 0.999 | 0.907 |
| High | 0.922 | 0.764 | 0.620 |

High-tier borrowers show the fastest drop in survival under the constructed-time rule. **Cox PH was not run in this repo.**

### Collections recommendation (dollar figure)

Under documented assumptions ($15/attempt × 2, 20% success, LGD 70%, avg balance proxy **$9,789.25**):

- **Prioritize High, then Medium** for early intervention.  
- **High-tier net benefit ≈ $29.0M**; High+Medium combined ≈ **$66.3M** (scenario output—see `reports/strategy_brief.md` caveats on score calibration).

## How to reproduce

Run from the repo root in order:

```bash
# 1–3. Load, clean, engineer features, SQLite + exploratory SQL
python src/etl_pipeline.py

# 4. EDA notebook (sections 1–3)
#    notebooks/01_credit_risk_analysis.ipynb

# 5. Train LR + XGBoost on labeled train; score full 251K; write tiers
python src/model_training.py
#    → data/processed/scored_borrowers.csv

# 6–8. Tableau CSVs (includes constructed-duration KM by tier + projected funnel)
python src/export_for_tableau.py
#    → dashboard/data/*.csv

# Read-outs
#    reports/market_research_brief.md
#    reports/strategy_brief.md
#    dashboard/README.md   # manual Tableau Public publish steps
```

Optional: rebuild SQLite anytime via `python src/etl_pipeline.py` (`data/processed/*.db` is gitignored).

## Project Structure

```
bnpl-default-risk-analysis/
├── data/
│   ├── raw/                       # cs-training.csv + cs-test.csv
│   └── processed/                 # clean CSV, scored_borrowers.csv, (local) SQLite DB
├── sql/schema.sql
├── notebooks/01_credit_risk_analysis.ipynb
├── src/
│   ├── etl_pipeline.py
│   ├── model_training.py
│   └── export_for_tableau.py
├── excel/README.md                # cost-model shell (figures also in strategy brief)
├── reports/
│   ├── market_research_brief.md
│   └── strategy_brief.md
├── dashboard/
│   ├── data/                      # Tableau-ready CSVs
│   └── README.md
├── requirements.txt
└── README.md
```

## Status / To Do

- [x] Repo structure + real dataset sourced (train + unlabeled test; 251,503 combined)
- [x] Data & methodology notes (200K+ policy + survival caveat)
- [x] ETL pipeline (`src/etl_pipeline.py`)
- [x] SQL schema + exploratory queries (`sql/schema.sql`)
- [x] EDA notebook sections 1–3
- [x] Classification (LR + XGBoost) + full-population scoring / risk tiers
- [x] Survival KM curves on **constructed** duration (Tableau export)
- [x] Collections cost-benefit figures (documented assumptions; strategy brief)
- [x] Tableau data exports (`dashboard/data/`) — Public URL optional
- [x] Market research brief (cited) + strategy brief

## Tools

Python (pandas, scikit-learn, XGBoost, lifelines), SQL (SQLite), Excel (optional interactive shell), Tableau Public

---
*Self-directed portfolio project using a real public dataset, reframed with a BNPL/installment-lending lens for illustrative analysis.*

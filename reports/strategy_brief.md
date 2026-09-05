# Strategy Brief — Collections Intervention Recommendation

Numbers below come from this repo’s computed outputs (Prompts 1–8) and the documented cost assumptions used for the collections funnel / cost-benefit arithmetic. They are **not** invented portfolio KPIs.

## Key Finding

**Prior delinquency and revolving utilization dominate both ranking and (constructed) timing.** On the labeled holdout, XGBoost reached **ROC-AUC 0.869** and **PR-AUC 0.404** (vs logistic baseline ROC-AUC **0.861** / PR-AUC **0.390**). Top feature importances were:

1. `prior_delinquency_count` — **0.408**  
2. `revolving_utilization_bucket_ord` — **0.284**  
3. `revolving_utilization` — **0.072**  

(`payment_to_income_ratio` ranked **#11**, outside the top 10—do not oversell it as a top driver.)

On **constructed** (not observed) durations, Kaplan–Meier curves by model risk tier show High-tier survival falling fastest: **S(6)≈0.92**, **S(12)≈0.76**, **S(24)≈0.62**, versus Medium **S(24)≈0.91** and Low **S(24)≈0.99** (`dashboard/data/survival_by_tier.csv`). **Cox PH was not fitted in this repo**—do not cite Cox results.

## Recommended Action

**Prioritize early intervention on the High risk tier first, then Medium**, under the documented outreach policy (contact 100% of the tier; $15/attempt × 2 attempts; 20% payment-plan success; LGD 70%; avg outstanding proxy **$9,789.25** = median of `debt_ratio × monthly_income × 6` for `debt_ratio < 5`).

Rationale:

- High tier = top **10%** of scores (**25,151** of **251,503** scored borrowers); mean predicted default probability **0.863**; observed train default rate within High **38.0%**.
- KM (constructed) shows High defaults earliest.
- Net-benefit arithmetic on the scored population (same assumptions as `src/export_for_tableau.py` funnel) is **positive for all three tiers** under base assumptions; operationally start where severity and speed are worst (High), then Medium.

Trigger: when a borrower is scored into **High** (and, capacity permitting, **Medium**), launch reminder → payment-plan offer within the first servicing window—not after multi-cycle aging.

## Projected Impact

Using mean `default_proba` by tier on the full scored file, avg balance proxy **$9,789.25**, LGD **0.70**, success rate **0.20**, cost **$15 × 2** attempts:

| Tier | N | Mean P(default) | Intervention cost | Expected savings | **Net benefit** |
|------|--:|----------------:|------------------:|-----------------:|----------------:|
| High | 25,151 | 0.863 | $754,530 | $29,740,353 | **+$28,985,823** |
| Medium | 50,300 | 0.563 | $1,509,000 | $38,837,357 | **+$37,328,357** |
| Low | 176,052 | 0.167 | $5,281,560 | $40,201,306 | **+$34,919,746** |

**Dollar-impact statement (recommended focus):** Early intervention on the **High** tier alone is estimated at about **$29.0M net benefit** under these assumptions (savings from prevented write-offs minus outreach cost). Extending the same policy to **High + Medium** implies about **$66.3M** combined net benefit ($28.99M + $37.33M). Low is also net-positive on this uncalibrated-score math but is a poorer first call given low observed delinquency (**1.5%** on train Low) and flat constructed KM survival.

**Caveats (required):** (1) Mean XGBoost probabilities with `scale_pos_weight` are **inflated vs observed tier default rates**—treat dollars as scenario output, not accounting P&L. (2) Success rate, cost, LGD, and balance proxy are **assumptions** (see `reports/market_research_brief.md`), not measured recoveries on GMSC. (3) Survival timing is **constructed**, not observed.

## Methodology Note

- Classification / tiers: `src/model_training.py` → `data/processed/scored_borrowers.csv`  
- KM curves: `src/export_for_tableau.py` → `dashboard/data/survival_by_tier.csv`  
- Cost-benefit arithmetic: same assumptions as collections funnel export (`success_rate=20%`, `$15`, `2` attempts, `LGD=70%`, balance proxy above). Excel workbook `excel/collections_cost_model.xlsx` was planned as the interactive shell for these inputs; figures here are recomputed directly from the scored file for auditability.

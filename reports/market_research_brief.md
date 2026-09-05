# Market Research Brief — BNPL & Installment Lending Benchmarks

Portfolio context for the Give Me Some Credit analysis reframed with an installment/BNPL lens. Industry figures below are **cited external benchmarks**; project figures are from this repo’s computed outputs.

## BNPL / installment delinquency benchmarks

1. **Affirm (U.S. monthly installment loans):** 30+ day delinquencies (excluding Peloton and Pay in X) were **2.8%** in Affirm’s fiscal Q3 2026 shareholder letter (period discussed in that letter). Affirm also reported that recent monthly-installment vintages were tracking toward roughly **~3.5% ultimate net charge-offs as a percent of cohort GMV**, while recent Pay in 4 vintages were tracking to **loss rates under 1% of GMV**.  
   Source: Affirm Holdings FQ3’26 Shareholder Letter (SEC exhibit / investor materials), [SEC HTML](https://www.sec.gov/Archives/edgar/data/1820953/000162828026032105/affirmfq326shareholderle.htm).

2. **Klarna (credit cost vs GMV):** Public commentary citing Klarna’s disclosures has placed **provision for credit losses around ~0.55% of gross merchandise volume** in a recent comparable quarter (vs ~0.54% a year earlier). Treat this as a GMV-scaled credit-cost metric, not a borrower-level 2-year serious-delinquency rate.  
   Source: Forbes summary of Klarna/Affirm credit metrics (22 Jun 2026), [Forbes](https://www.forbes.com/sites/zennonkapron/2026/06/22/klarna-and-affirm-both-post-profits-their-stocks-tell-opposite-stories/).

## Collections cost and recovery-rate ranges (industry)

These ranges informed the **assumption cells** used in this project’s cost-benefit arithmetic (not observed recovery from GMSC):

| Input | Range used as context | Notes |
|-------|----------------------|--------|
| Cost per human call attempt | ~**$7–$15** | Industry compilation of collector ops costs |
| Cost per right-party contact (human) | ~**$15–$35** | Higher than raw attempt cost |
| SMS / email attempt | ~**$0.02–$0.10** / ~**$0.01–$0.05** | Low-cost reminder channels |
| Agency recovery (broad) | often cited ~**15–30%** over multi-month placement windows | Varies heavily by age of debt and channel mix |

Source (industry compilation citing ops benchmarks): [Debt Collection Industry Statistics (Ainora, 2026)](https://ainora.lt/blog/debt-collection-industry-statistics-2026). This project’s live assumptions used in funnel/cost arithmetic are a blended **$15 per outreach**, **2 attempts**, and **20% intervention success rate** (payment-plan style), documented as assumptions—not measured outcomes on this dataset.

## Early-intervention playbook (practice summary)

**1. Reminders (SMS / email / app push).** Low-cost first touch shortly after a missed installment or when a borrower enters a high-risk score band. Goal is to restore payment before the account ages into harder collections. Typical promise-to-pay rates on one-way digital reminders are modest; value is scale and speed.

**2. Payment plans / hardship options.** If reminders fail, offer a structured plan (reduced installment, skipped payment, or extended schedule). This is the intervention type this project’s **20% success-rate assumption** is meant to represent—higher effort/cost than a reminder, higher chance of preventing a full write-off.

**3. Settle-now / discount-to-pay.** For accounts already unlikely to cure in full, a discounted payoff can recover more NPV than a drawn-out chase. Higher “success” in the sense of closing the account, but with an explicit principal concession—use selectively on the riskiest, oldest balances.

## Regulatory note (CFPB / BNPL)

In May 2024 the CFPB issued an interpretive rule on BNPL products accessed via digital user accounts under Truth in Lending (Regulation Z) (89 Fed. Reg. 47,068, May 31, 2024). On **May 12, 2025**, the CFPB **withdrew** that interpretive rule (among other guidance documents). The Bureau’s BNPL compliance resource page states the withdrawal explicitly.

Sources:

- CFPB BNPL products page (notes May 12, 2025 withdrawal): [consumerfinance.gov](https://www.consumerfinance.gov/compliance/compliance-resources/consumer-cards-resources/buy-now-pay-later-bnpl-products/)
- Original interpretive rule citation: *Truth in Lending (Regulation Z); Use of Digital User Accounts to Access Buy Now, Pay Later Loans*, 89 Fed. Reg. 47,068 (May 31, 2024)

Practical takeaway for this portfolio: consumer-protection expectations around disclosure, disputes, and servicing still matter operationally even when a specific federal interpretive rule is withdrawn; state rules may also apply. This project does not claim compliance advice.

## Comparison to this project’s delinquency rate

| Metric | Value | Source |
|--------|------:|--------|
| Project serious-delinquency rate (labeled train) | **6.68%** | `SeriousDlqin2yrs` on 150,000 training rows (`sql` exploratory query / ETL) |
| Affirm 30+ day delinquency (monthly installment, ex-Peloton/Pay in X) | **2.8%** | Affirm FQ3’26 shareholder letter |
| Affirm illustrative ultimate NCO (monthly installment vintages) | **~3.5% of cohort GMV** | Same letter |
| Affirm Pay in 4 vintage losses | **&lt;1% of GMV** | Same letter |

**Interpretation (do not overclaim equivalence):** This project’s **6.68%** is a **2-year serious-delinquency** label on traditional consumer credit bureau–style features (Give Me Some Credit). Affirm’s **2.8%** is a **point-in-time 30+ day delinquency** rate on BNPL/installment loans, and its charge-off figures are **GMV-scaled**. Different definitions, products, and horizons mean the project rate being higher than Affirm’s 30+ DQ is **not** evidence that “BNPL defaults at 6.68%.” The BNPL framing here is an **applied analytics lens** on real credit data, not a claim that these rows are Affirm/Klarna/Afterpay accounts.

## Sources (links)

1. Affirm FQ3’26 Shareholder Letter (SEC): https://www.sec.gov/Archives/edgar/data/1820953/000162828026032105/affirmfq326shareholderle.htm  
2. Forbes (Klarna/Affirm credit metrics summary, 22 Jun 2026): https://www.forbes.com/sites/zennonkapron/2026/06/22/klarna-and-affirm-both-post-profits-their-stocks-tell-opposite-stories/  
3. Ainora debt-collection industry statistics (cost/recovery ranges): https://ainora.lt/blog/debt-collection-industry-statistics-2026  
4. CFPB BNPL products / withdrawal notice page: https://www.consumerfinance.gov/compliance/compliance-resources/consumer-cards-resources/buy-now-pay-later-bnpl-products/  
5. 89 Fed. Reg. 47,068 (May 31, 2024) BNPL interpretive rule citation (as referenced by CFPB materials)

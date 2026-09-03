-- ============================================================
-- BNPL Payment Default & Collections Risk — Schema
-- ============================================================
-- Loads the "Give Me Some Credit" dataset into a single table.
-- Column names below match the source dataset; a real BNPL/
-- installment lender's schema would likely split this into
-- borrowers / loans / payment_history tables — noted in TODOs
-- below as a stretch goal.

DROP TABLE IF EXISTS borrowers;

CREATE TABLE borrowers (
    id                              INTEGER PRIMARY KEY,
    serious_dlq_2yrs                INTEGER,  -- target: 1 = defaulted within 2 years
    revolving_utilization           REAL,     -- total balance / credit limit
    age                             INTEGER,
    times_30_59_days_late           INTEGER,
    debt_ratio                      REAL,
    monthly_income                  REAL,
    num_open_credit_lines           INTEGER,
    times_90_days_late              INTEGER,
    num_real_estate_loans           INTEGER,
    times_60_89_days_late           INTEGER,
    num_dependents                  INTEGER
);

-- ============================================================
-- TODO: Example exploratory queries to build out
-- ============================================================

-- 1. Overall default rate
-- SELECT
--     ROUND(100.0 * SUM(serious_dlq_2yrs) / COUNT(*), 2) AS default_rate_pct
-- FROM borrowers;

-- 2. Default rate by revolving utilization bucket (a key BNPL-style risk signal)
-- SELECT
--     CASE
--         WHEN revolving_utilization < 0.3 THEN 'Low (<30%)'
--         WHEN revolving_utilization < 0.7 THEN 'Medium (30-70%)'
--         ELSE 'High (70%+)'
--     END AS utilization_bucket,
--     COUNT(*) AS borrower_count,
--     ROUND(100.0 * SUM(serious_dlq_2yrs) / COUNT(*), 2) AS default_rate_pct
-- FROM borrowers
-- GROUP BY utilization_bucket;

-- 3. Default rate by prior delinquency history
-- SELECT
--     CASE
--         WHEN times_90_days_late = 0 THEN 'No prior 90+ day lates'
--         WHEN times_90_days_late = 1 THEN '1 prior 90+ day late'
--         ELSE '2+ prior 90+ day lates'
--     END AS prior_delinquency,
--     COUNT(*) AS borrower_count,
--     ROUND(100.0 * SUM(serious_dlq_2yrs) / COUNT(*), 2) AS default_rate_pct
-- FROM borrowers
-- GROUP BY prior_delinquency;

-- 4. Default rate by age bracket
-- SELECT
--     CASE
--         WHEN age < 30 THEN '18-29'
--         WHEN age < 45 THEN '30-44'
--         WHEN age < 60 THEN '45-59'
--         ELSE '60+'
--     END AS age_bracket,
--     COUNT(*) AS borrower_count,
--     ROUND(100.0 * SUM(serious_dlq_2yrs) / COUNT(*), 2) AS default_rate_pct
-- FROM borrowers
-- GROUP BY age_bracket
-- ORDER BY MIN(age);

-- 5. Debt ratio vs. default (sanity check on a key underwriting signal)
-- SELECT
--     serious_dlq_2yrs,
--     ROUND(AVG(debt_ratio), 3) AS avg_debt_ratio
-- FROM borrowers
-- WHERE debt_ratio < 5  -- filter extreme outliers/data errors present in raw data
-- GROUP BY serious_dlq_2yrs;

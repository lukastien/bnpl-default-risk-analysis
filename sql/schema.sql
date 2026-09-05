-- ============================================================
-- BNPL Payment Default & Collections Risk — Schema
-- ============================================================
-- Single borrowers table matching data/processed/credit_data_clean.csv
-- (combined train + unlabeled test). A real BNPL/installment lender's
-- schema would likely split this into borrowers / loans / payment_history
-- tables — noted as a stretch goal.
--
-- id is unique within source_flag only (train and test reuse the same
-- Id space), so the primary key is composite: (source_flag, id).
-- serious_dlq_2yrs is NULL for source_flag = 'test' (no ground truth).

DROP TABLE IF EXISTS borrowers;

CREATE TABLE borrowers (
    id                              INTEGER NOT NULL,
    serious_dlq_2yrs                INTEGER,  -- 1 = default within 2yrs, NULL on test
    revolving_utilization           REAL,
    age                             INTEGER,
    times_30_59_days_late           INTEGER,
    debt_ratio                      REAL,
    monthly_income                  REAL,
    num_open_credit_lines           INTEGER,
    times_90_days_late              INTEGER,
    num_real_estate_loans           INTEGER,
    times_60_89_days_late           INTEGER,
    num_dependents                  REAL,
    source_flag                     TEXT NOT NULL,  -- 'train' or 'test'
    late_payment_code_artifact      INTEGER,        -- 1 if raw late counts were 96/98
    payment_to_income_ratio         REAL,           -- engineered
    prior_delinquency_count         INTEGER,        -- engineered
    revolving_utilization_bucket    TEXT,           -- engineered Low/Medium/High
    PRIMARY KEY (source_flag, id)
);

-- ============================================================
-- Exploratory queries (labeled training rows only)
-- Run via: python src/etl_pipeline.py  (run_exploratory_queries)
-- ============================================================

-- 1. Overall default rate (~6.68% expected)
SELECT
    COUNT(*) AS borrower_count,
    SUM(serious_dlq_2yrs) AS defaults,
    ROUND(100.0 * SUM(serious_dlq_2yrs) / COUNT(*), 2) AS default_rate_pct
FROM borrowers
WHERE source_flag = 'train';

-- 2. Default rate by revolving_utilization_bucket
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

-- 3. Default rate by prior_delinquency_count (0 / 1-2 / 3-5 / 6+)
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

-- 4. Default rate by age decade
SELECT
    CAST(age / 10 * 10 AS INTEGER) AS age_decade_start,
    COUNT(*) AS borrower_count,
    ROUND(100.0 * SUM(serious_dlq_2yrs) / COUNT(*), 2) AS default_rate_pct
FROM borrowers
WHERE source_flag = 'train'
GROUP BY age_decade_start
ORDER BY age_decade_start;

-- 5. Average payment_to_income_ratio for defaulters vs non-defaulters
SELECT
    serious_dlq_2yrs,
    COUNT(*) AS borrower_count,
    ROUND(AVG(payment_to_income_ratio), 4) AS avg_payment_to_income_ratio
FROM borrowers
WHERE source_flag = 'train'
GROUP BY serious_dlq_2yrs;

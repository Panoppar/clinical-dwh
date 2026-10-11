-- ============================================================================
-- Populate Dim_Date for 2024-01-01 .. 2030-12-31 using a recursive CTE.
-- Idempotent: safe to re-run (table is dropped/recreated by 01_create_*).
-- ============================================================================

USE gold;

-- Default MySQL recursion depth (1000) is too shallow for a ~2,557-day
-- range (2024-01-01 .. 2030-12-31); raise it for this session.
SET SESSION cte_max_recursion_depth = 5000;

INSERT INTO Dim_Date (date_key, full_date, year, quarter, month, month_name,
                       day, day_of_week, day_name, is_weekend, week_of_year)
WITH RECURSIVE date_seq AS (
  SELECT DATE('2024-01-01') AS full_date
  UNION ALL
  SELECT full_date + INTERVAL 1 DAY FROM date_seq WHERE full_date < '2030-12-31'
)
SELECT
  CAST(DATE_FORMAT(full_date, '%Y%m%d') AS UNSIGNED) AS date_key,
  full_date,
  YEAR(full_date)                AS year,
  QUARTER(full_date)             AS quarter,
  MONTH(full_date)               AS month,
  MONTHNAME(full_date)           AS month_name,
  DAY(full_date)                 AS day,
  WEEKDAY(full_date) + 1         AS day_of_week,   -- WEEKDAY(): 0=Mon -> +1 = ISO 1=Mon
  DAYNAME(full_date)             AS day_name,
  IF(WEEKDAY(full_date) >= 5, 1, 0) AS is_weekend,
  WEEK(full_date, 3)             AS week_of_year    -- mode 3 = ISO week
FROM date_seq;

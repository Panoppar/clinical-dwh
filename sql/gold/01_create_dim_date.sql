-- ============================================================================
-- GOLD LAYER — dim_date
-- Standard Kimball date dimension, day grain. Surrogate key is the
-- conventional YYYYMMDD integer (e.g. 20240101) -- still an integer
-- surrogate key per the project's convention, just a meaningful one, so
-- range filters ("this year", "this month") don't need a join.
-- Range: 1993-01-01 (DOPA's earliest data) through 2030-12-31 (a few
-- years past today, 2026-10-14).
-- ============================================================================

USE gold;

-- Each gold/*.sql script runs in its own connection and DROPs its own
-- table; rerunning without wiping the whole schema first would otherwise
-- fail here on a FK constraint from a fact table (created in a prior
-- run) still referencing this dimension.
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `dim_date`;

CREATE TABLE `dim_date` (
    `date_key`     INT          NOT NULL PRIMARY KEY COMMENT 'YYYYMMDD',
    `full_date`     DATE         NOT NULL,
    `year_ce`        SMALLINT     NOT NULL,
    `year_be`         SMALLINT     NOT NULL,
    `quarter`          TINYINT      NOT NULL,
    `month`             TINYINT      NOT NULL,
    `month_name`         VARCHAR(20)  NOT NULL,
    `day`                  TINYINT      NOT NULL,
    `is_month_start`        TINYINT(1)   NOT NULL DEFAULT 0,
    KEY `ix_dd_year` (`year_ce`),
    KEY `ix_dd_year_month` (`year_ce`, `month`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Non-recursive number generator (cross join of 10-value digit tables,
-- 10^5 = 100,000 rows -- comfortably covers the ~13,900 days in range)
-- rather than a recursive CTE: MySQL 8.0's default
-- cte_max_recursion_depth is 1000, far less than the day count needed,
-- and this avoids having to raise a session variable just to seed a
-- dimension table.
INSERT INTO `dim_date` (date_key, full_date, year_ce, year_be, quarter, month, month_name, day, is_month_start)
SELECT
    CAST(DATE_FORMAT(d, '%Y%m%d') AS UNSIGNED),
    d,
    YEAR(d),
    YEAR(d) + 543,
    QUARTER(d),
    MONTH(d),
    ELT(MONTH(d), 'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'),
    DAY(d),
    IF(DAY(d) = 1, 1, 0)
FROM (
    SELECT DATE('1993-01-01') + INTERVAL (a.n + b.n*10 + c.n*100 + e.n*1000 + f.n*10000) DAY AS d
    FROM
        (SELECT 0 n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
         UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) a
    CROSS JOIN
        (SELECT 0 n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
         UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) b
    CROSS JOIN
        (SELECT 0 n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
         UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) c
    CROSS JOIN
        (SELECT 0 n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
         UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) e
    CROSS JOIN
        (SELECT 0 n UNION SELECT 1) f
) dates
WHERE d <= '2030-12-31';

SET FOREIGN_KEY_CHECKS = 1;

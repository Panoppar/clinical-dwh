-- ============================================================================
-- SILVER LAYER — other_health's remaining local-area tables
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `health_kpi_export`;
DROP TABLE IF EXISTS `community_count_by_district_bkk`;
DROP TABLE IF EXISTS `foreign_labor_permit_by_area_bkk`;

-- Exact indicator/KPI name is NOT present in the source (per the bronze
-- DDL's own note) -- Silver can only do structural typing, not invent a
-- name for what target/result1..12 actually measure. Known limitation,
-- documented, not solved.
CREATE TABLE `health_kpi_export` (
    `silver_id`       BIGINT AUTO_INCREMENT PRIMARY KEY,
    `geo_level`          VARCHAR(20) NOT NULL,
    `set_number`           VARCHAR(5),
    `area_name`              VARCHAR(200) NOT NULL,
    `target`                   BIGINT,
    `result`                     BIGINT,
    `f3_ratio`                     DECIMAL(10,4),
    `result1`  BIGINT, `result2`  BIGINT, `result3`  BIGINT, `result4`  BIGINT,
    `result5`  BIGINT, `result6`  BIGINT, `result7`  BIGINT, `result8`  BIGINT,
    `result9`  BIGINT, `result10` BIGINT, `result11` BIGINT, `result12` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `community_count_by_district_bkk` (
    `silver_id`     BIGINT AUTO_INCREMENT PRIMARY KEY,
    `district_name`   VARCHAR(100) NOT NULL,
    `crowded_count`     INT,
    `suburban_count`      INT,
    `highrise_count`       INT,
    `urban_count`            INT,
    `special_format_count`     INT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- BRONZE-LEVEL DEFECT FOUND (not fixed at the source, documented here
-- instead -- see below): this source file is actually 4 separate reports
-- stacked vertically in the same 20 physical columns, each with its own
-- title/header block -- confirmed by inspection. Rows 1-11 (general
-- permit types: ทั่วไป/MOU/investment-promo/minority/renewal/undocumented)
-- are correctly captured by bronze's column names. Rows 12+ are a
-- DIFFERENT report (MOU import broken down by nationality: เมียนมา/ลาว/
-- กัมพูชา/เวียดนาม) reusing the same 20 columns with different meaning,
-- then ANOTHER report (renewal by nationality), then ANOTHER (undocumented
-- by nationality) -- bronze's column names (mou_total, minority_male,
-- etc.) are wrong for all of these later rows even though the raw values
-- underneath are intact. Properly fixing this means re-splitting bronze
-- into 4 report-specific tables; given this table's low priority (a
-- single auxiliary foreign-labor dataset, not a population/health
-- pillar), Silver instead loads ONLY rows 1-11 (the correctly-labeled
-- general-permit-type report) and excludes the mislabeled continuation --
-- shipping wrong data would be worse than shipping less of it. Revisit
-- the bronze split if this table becomes more load-bearing later.
-- "รวมทั้งสิ้น" (grand total) row within that first report is flagged.
CREATE TABLE `foreign_labor_permit_by_area_bkk` (
    `silver_id`           BIGINT AUTO_INCREMENT PRIMARY KEY,
    `area_name`              VARCHAR(100),
    `district_group`           VARCHAR(300) NOT NULL,
    `general_total`               BIGINT, `general_male` BIGINT, `general_female` BIGINT,
    `mou_total`                     BIGINT, `mou_male` BIGINT, `mou_female` BIGINT,
    `investment_promo_total`         BIGINT, `investment_promo_male` BIGINT, `investment_promo_female` BIGINT,
    `minority_total`                   BIGINT, `minority_male` BIGINT, `minority_female` BIGINT,
    `renewal_total`                      BIGINT, `renewal_male` BIGINT, `renewal_female` BIGINT,
    `undocumented_registered_total`        BIGINT, `undocumented_registered_male` BIGINT, `undocumented_registered_female` BIGINT,
    `is_aggregate_row`                       TINYINT(1) NOT NULL DEFAULT 0,
    KEY `ix_flp_aggregate` (`is_aggregate_row`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

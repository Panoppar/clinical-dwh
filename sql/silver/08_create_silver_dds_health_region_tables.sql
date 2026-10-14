-- ============================================================================
-- SILVER LAYER — DDS weekly disease surveillance by health region
--
-- YEAR NOTE: unlike every other BE-based source in this project,
-- report_year here is already Gregorian (2022-2026 range) -- confirmed by
-- inspection of the filenames (skr6_2022_wk1wk52.csv etc.); there is no
-- date column inside the row data itself to cross-check against, so this
-- is the only verifiable signal available. No -543 conversion applied.
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `dds_health_region_disease_report`;

CREATE TABLE `dds_health_region_disease_report` (
    `silver_id`           BIGINT AUTO_INCREMENT PRIMARY KEY,
    `health_region_code`   VARCHAR(20)  NOT NULL,
    `report_year_ce`         SMALLINT     NOT NULL,
    `report_period_label`     VARCHAR(30)  NOT NULL,
    `rank_no`                   SMALLINT,
    `disease_name_th`            VARCHAR(255) NOT NULL,
    `patient_count`                BIGINT,
    `morbidity_rate_per_100k`       DECIMAL(10,2),
    `ipd_count`                      BIGINT,
    `death_count`                     BIGINT,
    `case_fatality_rate_pct`           DECIMAL(6,2),
    -- is_aggregate_row: same rollup-vs-subtype pattern already found and
    -- fixed once in this project's DDS_Disease_Ranking data -- "ไข้เลือดออก
    -- รวม" (dengue combined) coexists with its own subtypes ("ไข้เด็งกี",
    -- "ไข้เลือดออก", and sometimes "ไข้เลือดออกช็อก") as separate ranked
    -- rows; "หัดรวม" (measles combined) likewise. Confirmed by inspection
    -- (skr6 2023: 18,933+4,858+378 = 24,169, matching the combined row
    -- exactly). Flagged rather than dropped, same reasoning as before --
    -- the rollup is the right figure for "total dengue", the subtypes are
    -- right for a breakdown, just don't mix them in one SUM().
    `is_aggregate_row`                  TINYINT(1) NOT NULL DEFAULT 0,
    KEY `ix_dds_region_year` (`health_region_code`, `report_year_ce`),
    KEY `ix_dds_aggregate` (`is_aggregate_row`),
    KEY `ix_dds_disease` (`disease_name_th`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

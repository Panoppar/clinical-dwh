-- ============================================================================
-- SILVER LAYER — dds_health_region_disease_report
--
-- YEAR NOTE: unlike every other BE-based source in this project, report_year
-- here is already Gregorian (2022-2026 range) -- confirmed by inspection of
-- the filenames (skr6_2024_wk1wk52.pdf etc.) and cross-checked against the
-- PDF's own cover text ("31 ธันวาคม 2567" = BE 2567 = CE 2024, matching the
-- filename's "2024"). No -543 conversion applied.
--
-- Includes row_hash + ingestion_batch_id from the start (incremental
-- architecture, not retrofitted) -- see pipeline/transform_silver_dds_health_region.py.
-- ============================================================================

USE silver;

CREATE TABLE IF NOT EXISTS `dds_health_region_disease_report` (
    `silver_id`                 BIGINT AUTO_INCREMENT PRIMARY KEY,
    `health_region_code`        VARCHAR(20)  NOT NULL,
    `report_year_ce`            SMALLINT     NOT NULL,
    `report_period_label`       VARCHAR(30)  NOT NULL,
    `rank_no`                   SMALLINT,
    `disease_name_th`           VARCHAR(255) NOT NULL,
    `patient_count`             BIGINT,
    `morbidity_rate_per_100k`   DECIMAL(10,2),
    `ipd_count`                 BIGINT,
    `death_count`               BIGINT,
    `case_fatality_rate_pct`    DECIMAL(6,2),
    -- is_aggregate_row: same rollup-vs-subtype pattern already found and
    -- fixed once in this project's api_dds_disease_ranking data -- e.g.
    -- "ไข้เลือดออกรวม" (dengue combined) coexists with its own subtypes
    -- ("ไข้เด็งกี", "ไข้เลือดออก", "ไข้เลือดออกช็อก") as separate ranked
    -- rows. Flagged rather than dropped -- the rollup is the right figure
    -- for "total dengue", the subtypes are right for a breakdown, just
    -- don't mix them in one SUM().
    `is_aggregate_row`          TINYINT(1) NOT NULL DEFAULT 0,
    `row_hash`                  VARCHAR(16),
    `ingestion_batch_id`        VARCHAR(100),
    KEY `ix_dds_hr_region_year` (`health_region_code`, `report_year_ce`),
    KEY `ix_dds_hr_aggregate` (`is_aggregate_row`),
    KEY `ix_dds_hr_disease` (`disease_name_th`),
    KEY `ix_dds_hr_row_hash` (`row_hash`),
    KEY `ix_dds_hr_batch_id` (`ingestion_batch_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- BRONZE LAYER — dds_health_region_disease_report
-- Source: skr6/skr13 health-region weekly disease ranking PDFs, 2022-2026
-- (DDS - กรมควบคุมโรค), file-based -- same project history as this live
-- DDS backend outage: the province-grain live API has been down since
-- 2026-10-25, so this health-region-grain PDF archive is used as a
-- stand-in. NOT the same grain as api_dds_disease_ranking (province vs
-- health-region) -- see transform_silver_dds_health_region.py and
-- transform_gold_all_sources_incremental.py's _build_fact_disease_ranking
-- for how the two are reconciled (skr13 = Bangkok only, clean 1:1;
-- skr6 spans multiple provinces, not force-mapped to one).
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `dds_health_region_disease_report`;

CREATE TABLE `dds_health_region_disease_report` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key (source PDF)',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_row_number`   INT           NOT NULL COMMENT 'row position within the PDF''s last-page table (1-based, excl. header)',
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'DDS_HEALTH_REGION',

  `health_region_code`     VARCHAR(20)   NOT NULL COMMENT 'skr6, skr13 -- parsed from filename',
  `report_year`             VARCHAR(10)   NOT NULL COMMENT 'already Gregorian/CE per filename, unlike every BE-based source elsewhere in this project',
  `report_period_label`     VARCHAR(30)   NOT NULL COMMENT 'wk1wk52, wk1wk53, this_year -- parsed from filename',

  `raw_no`                  VARCHAR(20),
  `raw_disease_name_th`     VARCHAR(255),
  `raw_patient_count`       VARCHAR(50),
  `raw_morbidity_rate`      VARCHAR(50),
  `raw_ipd_count`           VARCHAR(50),
  `raw_death_count`         VARCHAR(50),
  `raw_case_fatality_rate`  VARCHAR(50),

  KEY `idx_dds_hr_bronze_region_year` (`health_region_code`, `report_year`),
  KEY `idx_dds_hr_bronze_source_file` (`source_file_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Bronze landing table for DDS weekly disease surveillance reports by health region (skr6, skr13), 2022-2026. Raw, untyped, 1:1 with each PDF''s last-page ranking table rows.';

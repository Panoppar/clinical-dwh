-- =============================================================================
-- BRONZE LAYER TABLE DESIGN
-- Source folder : DDS_health_region_reports_2022-2026_checked
-- Source files  : skr6/skr6_*.csv, skr13/skr13_*.csv
--                 (weekly disease surveillance reports, DDS - กรมควบคุมโรค,
--                  by health region, years 2022-2026)
--
-- Translated from the provided DDL at
-- share_unprocessed_20261010/DDS_health_region_reports_2022-2026_checked/bronze_dds_health_region_reports.sql
-- into MySQL 8.0 syntax.
-- =============================================================================

USE bronze;

DROP TABLE IF EXISTS `dds_health_region_disease_report`;

CREATE TABLE `dds_health_region_disease_report` (
    `bronze_id`               BIGINT AUTO_INCREMENT PRIMARY KEY,
    `source_folder`           VARCHAR(50)   NOT NULL COMMENT 'e.g. skr6, skr13',
    `health_region_code`      VARCHAR(20)   NOT NULL COMMENT 'same as source_folder, e.g. skr6, skr13',
    `source_file_name`        VARCHAR(255)  NOT NULL COMMENT 'e.g. skr13_2024_wk1wk52.csv',
    `report_year`             VARCHAR(10)   NOT NULL COMMENT 'parsed from file name, e.g. 2024',
    `report_period_label`     VARCHAR(30)   NOT NULL COMMENT 'parsed from file name, e.g. wk1wk52, wk1wk53, this_year',
    `source_row_number`       INT           NOT NULL COMMENT 'row position within the source CSV (1-based, excl. header)',
    `ingested_at`             TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `load_batch_id`           VARCHAR(100),
    `file_hash`               VARCHAR(64),

    `raw_no`                  VARCHAR(20)   COMMENT 'ที่ (row/rank number)',
    `raw_disease_name_th`     VARCHAR(255)  COMMENT 'โรค (disease name, Thai)',
    `raw_patient_count`       VARCHAR(50)   COMMENT 'ผู้ป่วย (ราย)',
    `raw_morbidity_rate`      VARCHAR(50)   COMMENT 'อัตราป่วย (ตอแสนประชากร)',
    `raw_ipd_count`           VARCHAR(50)   COMMENT 'ผู้ป่วยใน (IPD) (ราย)',
    `raw_death_count`         VARCHAR(50)   COMMENT 'ผู้เสียชีวิต (ราย)',
    `raw_case_fatality_rate`  VARCHAR(50)   COMMENT 'อัตราป่วยตาย (%)',

    KEY `idx_dds_bronze_region_year` (`health_region_code`, `report_year`),
    KEY `idx_dds_bronze_source_file` (`source_file_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Bronze landing table for DDS weekly disease surveillance reports by health region (skr6, skr13), 2022-2026. Raw, untyped, 1:1 with source CSV rows.';

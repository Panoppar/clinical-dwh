-- ============================================================================
-- SILVER LAYER — HDC_manual_exports, unpivoted into one generic long table
--
-- Bronze's 4 category tables each store the handful of promoted dimension
-- columns plus a raw_data JSON payload (every original Thai column name
-- as a key). This was the right call at bronze time -- ~287 files resolve
-- to ~100 reports but only 35 distinct column schemas, and a few reports
-- change their own header text release to release (confirmed for report
-- '18'). Silver unpivots that JSON into one row per (report, row,
-- original-column) -- a generic observation table that Gold can pivot or
-- filter per specific report later, without per-report custom parsing
-- across ~100 heterogeneous reports now.
--
-- NOTE for Gold: the aggregate-row scanner flags several column_name
-- values containing "รวมทั้งหมด"/"รวม" (e.g. a breakdown report's own
-- "grand total" sub-column sitting alongside its per-category
-- sub-columns). This is NOT the hidden-duplicate-row bug class this
-- project has fixed elsewhere -- it's the normal shape of a breakdown
-- report, already understood at bronze time. Never blindly SUM(raw_value)
-- across all column_name values for a row; always filter to the specific
-- original column(s) a report needs first.
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `hdc_indicator_observations`;

CREATE TABLE `hdc_indicator_observations` (
    `silver_id`        BIGINT AUTO_INCREMENT PRIMARY KEY,
    `category_code`     VARCHAR(2)   NOT NULL,
    `report_no`          VARCHAR(20)  NOT NULL,
    `report_name`         VARCHAR(500) NOT NULL,
    `table_variant`        VARCHAR(20),
    `fiscal_year_be`        SMALLINT,
    `fiscal_year_ce`         SMALLINT,
    `health_region`           VARCHAR(50),
    `province`                 VARCHAR(100),
    `area`                      VARCHAR(100),
    `source_file`                VARCHAR(255) NOT NULL,
    `row_in_file`                  INT          NOT NULL,
    `column_name`                   VARCHAR(500) NOT NULL COMMENT 'original Thai column name from the source export',
    `raw_value`                      VARCHAR(1000) COMMENT 'kept as text -- values across ~100 reports mix counts, rates, percentages; cast per-report in Gold, not here',
    KEY `ix_hio_report` (`report_no`),
    KEY `ix_hio_province_year` (`province`, `fiscal_year_ce`),
    KEY `ix_hio_column` (`column_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

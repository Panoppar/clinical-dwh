-- =============================================================================
-- BRONZE LAYER TABLE DESIGN
-- Source folder : KMCH_catchment_places_lists_checked
-- Source file   : KMCH_Catchment_Places_Extended_All - ลิตส์เอง.csv
--
-- Translated from the provided DDL at
-- share_unprocessed_20261010/KMCH_catchment_places_lists_checked/bronze_kmch_catchment_places.sql
-- into MySQL 8.0 syntax.
-- =============================================================================

USE bronze;

DROP TABLE IF EXISTS `kmch_catchment_places`;

CREATE TABLE `kmch_catchment_places` (
    `bronze_id`               BIGINT AUTO_INCREMENT PRIMARY KEY,
    `source_file_name`        VARCHAR(255)  NOT NULL,
    `source_row_number`       INT           NOT NULL,
    `ingested_at`             TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `load_batch_id`           VARCHAR(100),
    `file_hash`               VARCHAR(64),

    `raw_category`             VARCHAR(100)  COMMENT 'Category, e.g. Housing Estate (B2C), Education, Industrial / Logistics (B2B)',
    `raw_place_name_th`        VARCHAR(500),
    `raw_place_name_en`        VARCHAR(500),
    `raw_address`               VARCHAR(500),
    `raw_sub_district`          VARCHAR(255),
    `raw_district`              VARCHAR(255),
    `raw_province`               VARCHAR(255),
    `raw_avg_distance_km`       VARCHAR(50),
    `raw_avg_travel_time_mins`  VARCHAR(50),
    `raw_market_potential`      VARCHAR(255),

    KEY `idx_kmch_bronze_category` (`raw_category`),
    KEY `idx_kmch_bronze_district` (`raw_district`),
    KEY `idx_kmch_bronze_source_file` (`source_file_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Bronze landing table for KMCH catchment-area places list. Raw, untyped, 1:1 with source CSV rows.';

-- ============================================================================
-- BRONZE LAYER — kmch_catchment_places
-- Source: kmch_catchment_places.csv (user-supplied, file-based -- same
-- pattern as bma_zone_districts/dopa_population_supplement, see those
-- tables' headers for why file-based is a deliberate, scoped exception).
-- A synthetic list of places (housing estates, schools, industrial sites,
-- markets, religious sites, etc.) across the 3 catchment-province scope,
-- each with distance/travel-time from KMCH and a market-potential label
-- intended as an ML target for a future catchment-targeting model.
-- Landed 2026-11-03.
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `kmch_catchment_places`;

CREATE TABLE `kmch_catchment_places` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'KMCH_CATCHMENT_PLACES',

  `raw_category`              VARCHAR(100),
  `raw_place_name_th`          VARCHAR(500),
  `raw_place_name_en`           VARCHAR(500),
  `raw_address`                  VARCHAR(500),
  `raw_subdistrict`                VARCHAR(255),
  `raw_district`                     VARCHAR(255),
  `raw_province`                      VARCHAR(255),
  `raw_avg_distance_km`                VARCHAR(50),
  `raw_avg_travel_time_min`              VARCHAR(50),
  `raw_market_potential`                  VARCHAR(255),

  KEY `ix_kcp_category` (`raw_category`),
  KEY `ix_kcp_geo` (`raw_province`, `raw_district`, `raw_subdistrict`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Bronze landing table for the KMCH catchment places list. Raw, untyped, 1:1 with source CSV rows.';

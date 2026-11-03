-- ============================================================================
-- GOLD LAYER — dim_catchment_place
-- One row per place from the KMCH catchment places list (housing estates,
-- schools, industrial sites, markets, religious sites, etc.), each with a
-- market-potential label intended as an ML target for a future
-- catchment-targeting model. geo_key resolved via exact (province,
-- district, subdistrict) text match against dim_geography -- confirmed
-- live all 15 distinct location combinations in this source resolve
-- cleanly (same 3-catchment-province scope as every other source here).
--
-- Descriptive attributes (avg_distance_km, avg_travel_time_min,
-- market_tier/detail) live directly on this dimension, not a separate
-- fact table -- same convention dim_area already uses for its own
-- dist_to_kmch_km/catchment_tier columns, since these are static
-- properties of the place, not a time series.
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `dim_catchment_place`;

CREATE TABLE `dim_catchment_place` (
    `place_key`             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `category`              VARCHAR(100) NOT NULL,
    `place_name_th`         VARCHAR(500) NOT NULL,
    `place_name_en`         VARCHAR(500),
    `address`               VARCHAR(500),
    `geo_key`               INT UNSIGNED NULL COMMENT 'NULL if (province,district,subdistrict) text match fails -- not expected given this source''s scope, but not force-matched either',
    `avg_distance_km`       DECIMAL(6,2),
    `avg_travel_time_min`   DECIMAL(6,1),
    `market_tier`           VARCHAR(100),
    `market_detail`         VARCHAR(255),
    -- place_hash, not a direct (place_name_th, address) composite key:
    -- both are VARCHAR(500) utf8mb4 (2000 bytes each), so a direct
    -- composite unique key would exceed InnoDB's 3072-byte max index
    -- length -- confirmed live (ERROR 1071). Same hash-based-key pattern
    -- as gold.fact_income.business_key_hash.
    `place_hash`            VARCHAR(16) NOT NULL,
    UNIQUE KEY `ux_dcp_place_hash` (`place_hash`),
    KEY `ix_dcp_category` (`category`),
    KEY `ix_dcp_geo` (`geo_key`),
    KEY `ix_dcp_tier` (`market_tier`),
    CONSTRAINT `fk_dcp_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

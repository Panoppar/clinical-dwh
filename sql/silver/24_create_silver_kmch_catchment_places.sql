-- ============================================================================
-- SILVER LAYER — kmch_catchment_places
-- Casts distance/travel-time to numeric, trims text. market_potential is
-- split into market_tier + market_detail (see
-- pipeline/transform_silver_kmch_catchment_places.py for the exact split
-- rule) -- confirmed by direct inspection that all 13 distinct source
-- values follow a "label" or "label (detail)" shape, so a single regex
-- handles every case without a hardcoded enum (some labels are "High"/
-- "Medium" as expected, but others are "Medium to High" or "Strategic
-- Partner" -- genuinely different content, not a fixed 3-value scale).
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `kmch_catchment_places`;

CREATE TABLE `kmch_catchment_places` (
    `silver_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
    `category`              VARCHAR(100) NOT NULL,
    `place_name_th`         VARCHAR(500) NOT NULL,
    `place_name_en`         VARCHAR(500),
    `address`               VARCHAR(500),
    `subdistrict`           VARCHAR(255) NOT NULL,
    `district`              VARCHAR(255) NOT NULL,
    `province`              VARCHAR(255) NOT NULL,
    `avg_distance_km`       DECIMAL(6,2),
    `avg_travel_time_min`   DECIMAL(6,1),
    `market_tier`           VARCHAR(100),
    `market_detail`         VARCHAR(255),
    KEY `ix_kcp_category` (`category`),
    KEY `ix_kcp_geo` (`province`, `district`, `subdistrict`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

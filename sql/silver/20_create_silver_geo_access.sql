-- ============================================================================
-- SILVER LAYER — geo_access (from bronze.geo_hospital_facility / geo_travel_matrix)
-- Typed, trimmed. No BE->CE concern -- no dates in this source.
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `geo_hospital_facility`;
DROP TABLE IF EXISTS `geo_travel_matrix`;

CREATE TABLE `geo_hospital_facility` (
    `silver_id`         BIGINT AUTO_INCREMENT PRIMARY KEY,
    `osm_type`          VARCHAR(20)   NOT NULL,
    `osm_id`            BIGINT        NOT NULL,
    `name`              VARCHAR(500),
    `lat`               DECIMAL(10,6) NOT NULL,
    `lon`               DECIMAL(10,6) NOT NULL,
    `tags_json`         TEXT,
    UNIQUE KEY `ux_ghf_osm` (`osm_type`, `osm_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `geo_travel_matrix` (
    `silver_id`         BIGINT AUTO_INCREMENT PRIMARY KEY,
    `source_unit_code`  VARCHAR(20)   NOT NULL,
    `destination_id`    VARCHAR(100)  NOT NULL COMMENT 'OSM facility id, or the literal string KMCH',
    `duration_s`        DECIMAL(12,2),
    `distance_m`        DECIMAL(14,2),
    `source_snap_m`     DECIMAL(10,2),
    `destination_snap_m` DECIMAL(10,2),
    KEY `ix_gtm_source` (`source_unit_code`),
    KEY `ix_gtm_dest` (`destination_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

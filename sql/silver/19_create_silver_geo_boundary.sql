-- ============================================================================
-- SILVER LAYER — geo_boundary (from bronze.geo_boundary_*)
-- Typed, trimmed. No BE->CE concern -- no dates in this source.
-- geo_boundary_polygon has no Silver counterpart: nothing downstream
-- needs typed access to raw GeoJSON geometry, and gold.dim_area doesn't
-- store geometry at all (see sql/gold/04) -- the Bronze polygon table
-- alone is the source-of-truth, matching how docs/maps/*.geojson is
-- already kept out of the relational DB for the Metabase choropleth.
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `geo_boundary_subdistrict`;
DROP TABLE IF EXISTS `geo_boundary_district`;

CREATE TABLE `geo_boundary_subdistrict` (
    `silver_id`                     BIGINT AUTO_INCREMENT PRIMARY KEY,
    `subdistrict_code`              VARCHAR(20)  NOT NULL COMMENT 'TIS-1099, 6-digit',
    `district_code`                 VARCHAR(20)  NOT NULL COMMENT 'TIS-1099, 4-digit, parent',
    `province_code`                 VARCHAR(20)  NOT NULL COMMENT 'TIS-1099, 2-digit, parent',
    `name_en`                       VARCHAR(255),
    `name_th`                       VARCHAR(255) NOT NULL,
    `centroid_lat`                  DECIMAL(10,6) COMMENT 'NULL for the 13 Bangkok post-2019 khwaeng splits with no polygon in this snapshot -- resolved via parent-district fallback in Gold',
    `centroid_lon`                  DECIMAL(10,6),
    `postal_code`                   VARCHAR(10),
    UNIQUE KEY `ux_gbs_code` (`subdistrict_code`),
    KEY `ix_gbs_district` (`district_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `geo_boundary_district` (
    `silver_id`                     BIGINT AUTO_INCREMENT PRIMARY KEY,
    `district_code`                 VARCHAR(20)  NOT NULL COMMENT 'TIS-1099, 4-digit',
    `province_code`                 VARCHAR(20)  NOT NULL COMMENT 'TIS-1099, 2-digit, parent',
    `name_en`                       VARCHAR(255),
    `name_th`                       VARCHAR(255) NOT NULL,
    `centroid_lat`                  DECIMAL(10,6),
    `centroid_lon`                  DECIMAL(10,6),
    `area_km2`                      DECIMAL(10,2),
    `num_tambon`                    SMALLINT,
    `postal_code_prefixes`          VARCHAR(255),
    UNIQUE KEY `ux_gbd_code` (`district_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

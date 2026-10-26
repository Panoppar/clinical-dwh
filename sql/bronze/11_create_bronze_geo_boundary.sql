-- ============================================================================
-- BRONZE LAYER TABLE DESIGN — Thailand canonical administrative boundaries
-- Source: DevelopedbyWill/thailand-canonical-admin-names (GitHub, public,
-- CC BY 4.0), landed via SeaweedFS (see pipeline/ingest_api_geo_boundary.py).
-- Feeds gold.dim_area (sql/gold/04_create_gold_area_dimension.sql) --
-- the catchment-area dimension kmch-ml needs that clinical-dwh's existing
-- dim_geography (plain text names only) cannot support.
--
-- Three source files, three tables -- 1:1 fidelity, no transformation,
-- same convention as every other Bronze table.
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `geo_boundary_subdistrict`;
DROP TABLE IF EXISTS `geo_boundary_district`;
DROP TABLE IF EXISTS `geo_boundary_polygon`;

CREATE TABLE `geo_boundary_subdistrict` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'GEO_BOUNDARY',

  `raw_tis1099_subdistrict_code`         VARCHAR(20),
  `raw_parent_district_tis1099_code`      VARCHAR(20),
  `raw_parent_province_tis1099_code`       VARCHAR(20),
  `raw_name_en`                              VARCHAR(255),
  `raw_name_th`                               VARCHAR(255),
  `raw_centroid_lat`                           VARCHAR(50) COMMENT 'Empty for 13 Bangkok post-2019 khwaeng splits with no polygon in this snapshot -- resolved via parent district fallback in Gold, not here.',
  `raw_centroid_lon`                            VARCHAR(50),
  `raw_postal_code`                              VARCHAR(20),

  KEY `ix_gbs_code` (`raw_tis1099_subdistrict_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `geo_boundary_district` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'GEO_BOUNDARY',

  `raw_tis1099_district_code`       VARCHAR(20),
  `raw_parent_province_tis1099_code` VARCHAR(20),
  `raw_name_en`                       VARCHAR(255),
  `raw_name_th`                        VARCHAR(255),
  `raw_centroid_lat`                    VARCHAR(50),
  `raw_centroid_lon`                     VARCHAR(50),
  `raw_area_km2`                          VARCHAR(50),
  `raw_bbox_minlat`                        VARCHAR(50),
  `raw_bbox_minlon`                         VARCHAR(50),
  `raw_bbox_maxlat`                          VARCHAR(50),
  `raw_bbox_maxlon`                           VARCHAR(50),
  `raw_num_tambon`                             VARCHAR(20),
  `raw_postal_code_prefixes`                    VARCHAR(255),
  `raw_notes`                                    VARCHAR(500),

  KEY `ix_gbd_code` (`raw_tis1099_district_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- One row per ADM3 (subdistrict) polygon feature. Geometry kept as raw
-- GeoJSON text -- this is the source-of-truth for full polygon shape;
-- gold.dim_area does not store geometry, only the numeric/text attributes
-- derived from it (centroid, distance, tier), matching how docs/maps/
-- GeoJSON is already kept out of the relational DB for the Metabase map.
CREATE TABLE `geo_boundary_polygon` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'GEO_BOUNDARY',

  `raw_adm3_pcode`       VARCHAR(20)  COMMENT 'e.g. TH420803 -- strip leading TH for the bare TIS-1099 code',
  `raw_adm3_en`           VARCHAR(255),
  `raw_adm3_th`            VARCHAR(255),
  `raw_adm2_pcode`          VARCHAR(20),
  `raw_adm1_pcode`           VARCHAR(20),
  `raw_geometry_geojson`      LONGTEXT COMMENT 'Full Polygon/MultiPolygon geometry object, raw GeoJSON text',

  KEY `ix_gbp_pcode` (`raw_adm3_pcode`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

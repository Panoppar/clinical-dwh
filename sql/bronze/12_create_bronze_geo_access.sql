-- ============================================================================
-- BRONZE LAYER TABLE DESIGN — OSM hospital facilities + OSRM travel matrix
-- (kmch-ml input-parity gap 3). Entirely new source TYPE (Overpass API +
-- OSRM, not a Thai government API) landed via SeaweedFS, same pattern as
-- every other live source.
--
-- geo_hospital_facility: 0 rows as of this build -- the public
-- overpass-api.de instance (and its lz4 mirror) returned HTTP 406 on every
-- request tested on 2026-10-26, confirmed from both the elt-runner
-- container and the host machine directly (not a Docker networking
-- issue) -- a block on this network origin, unrelated to this code. Same
-- class of issue as DDS's backend outage: code-complete, wrapped in
-- run_pipeline.run_live_source(), worth retrying once Overpass is
-- reachable again.
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `geo_hospital_facility`;
DROP TABLE IF EXISTS `geo_travel_matrix`;

CREATE TABLE `geo_hospital_facility` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'OSM',

  `raw_osm_type`          VARCHAR(20)  COMMENT 'node | way | relation',
  `raw_osm_id`              BIGINT,
  `raw_lat`                   VARCHAR(50) COMMENT 'node lat, or way/relation center lat',
  `raw_lon`                    VARCHAR(50),
  `raw_name`                     VARCHAR(500),
  `raw_tags_json`                  TEXT COMMENT 'full OSM tags object, raw JSON text',

  KEY `ix_ghf_osm_id` (`raw_osm_type`, `raw_osm_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- One row per (source unit, destination facility) OSRM table-API result
-- cell. Raw matrix only -- no accessibility scoring (Huff share, E2SFCA)
-- computed here or anywhere downstream in this project; that's explicitly
-- out of scope (analytical modeling, not input-data coverage).
CREATE TABLE `geo_travel_matrix` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'OSRM',

  `raw_source_unit_code`    VARCHAR(20)  COMMENT 'dim_area.unit_code',
  `raw_destination_id`        VARCHAR(100) COMMENT 'OSM facility id, or the literal string KMCH for the fixed-hub destination',
  `raw_duration_s`              VARCHAR(50),
  `raw_distance_m`                VARCHAR(50),
  `raw_source_snap_m`                VARCHAR(50) COMMENT 'OSRM''s own snap-to-road distance for the source point',
  `raw_destination_snap_m`              VARCHAR(50),

  KEY `ix_gtm_source` (`raw_source_unit_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

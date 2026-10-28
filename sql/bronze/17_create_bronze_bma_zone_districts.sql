-- ============================================================================
-- BRONZE LAYER — bma_zone_districts. Static administrative reference: which
-- districts fall under each of BMA's own 10 numbered zones. File-based, not
-- a live API -- a deliberate, scoped exception (same category as the
-- tambon-unit crosswalk): this is fixed Thai public-administration
-- geography, not a publication with a fetchable endpoint.
--
-- Split out on 2026-10-28 from what was previously a side-effect of the
-- old file-based migrant-worker-permit source (bronze.bma_migrant_general's
-- raw_zone_districts_or_label column) -- that source became live (DOE's
-- monthly PDF, see sql/bronze/16) and the live PDF has no district-mapping
-- column at all, but gold.dim_bma_zone + bridge_bma_zone_district need
-- this mapping regardless of where permit counts come from. No Silver
-- layer needed -- transform_gold_dimensions._build_dim_bma_zone() reads
-- this table directly, same pattern as bronze.tambon_xwalk.
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `bma_zone_districts`;

CREATE TABLE `bma_zone_districts` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'BMA_ZONE_DISTRICTS',

  `raw_zone_id`          VARCHAR(10),
  `raw_zone_name_th`      VARCHAR(50),
  `raw_district_name`      VARCHAR(150),

  KEY `ix_bzd_zone` (`raw_zone_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

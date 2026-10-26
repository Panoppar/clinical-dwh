-- ============================================================================
-- GOLD LAYER — dim_facility + fact_hospital_access (kmch-ml input-parity gap 3)
-- New file, does not touch any table in sql/gold/01-05 -- those stay
-- exactly as-is.
--
-- fact_hospital_access carries the RAW travel-time/distance matrix only --
-- explicitly excludes kmch-ml's derived accessibility scores (Huff share,
-- e.g. huff_share_kmch_t_beta{1,2,3}; E2SFCA, e.g. e2sfca_t_per_100k_d0_{20,30,45}),
-- which are analytical/scoring models out of scope for this ingestion-only
-- project.
--
-- dim_facility always contains at least the fixed KMCH coordinate
-- (destination_id='KMCH') regardless of whether OSM facility discovery has
-- landed anything -- Overpass's public instance was blocked on every test
-- as of 2026-10-26 (see sql/bronze/12), but the single most important
-- destination for this project doesn't depend on that succeeding.
-- ============================================================================

USE gold;

-- fact_hospital_access FKs into dim_area (sql/gold/04, created earlier in
-- GOLD_SCRIPTS order) and dim_facility (this file) -- on a re-run, a plain
-- DROP TABLE for either referenced table fails while the previous run's
-- fact_hospital_access still exists (same class of error as sql/gold/04's
-- dim_area fix). Same pattern sql/gold/01 already uses for dim_geography.
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `dim_facility`;
DROP TABLE IF EXISTS `fact_hospital_access`;

CREATE TABLE `dim_facility` (
    `facility_key`       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `destination_id`     VARCHAR(100) NOT NULL COMMENT 'OSM facility id, or the literal string KMCH',
    `name`               VARCHAR(500),
    `lat`                DECIMAL(10,6) NOT NULL,
    `lon`                DECIMAL(10,6) NOT NULL,
    `is_kmch`            TINYINT(1)   NOT NULL DEFAULT 0,
    UNIQUE KEY `ux_df_destination` (`destination_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `fact_hospital_access` (
    `fact_id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
    `area_key`           INT UNSIGNED NOT NULL,
    `facility_key`       INT UNSIGNED NOT NULL,
    `duration_s`         DECIMAL(12,2),
    `distance_m`         DECIMAL(14,2),
    KEY `ix_fha_area` (`area_key`),
    KEY `ix_fha_facility` (`facility_key`),
    CONSTRAINT `fk_fha_area` FOREIGN KEY (`area_key`) REFERENCES `dim_area` (`area_key`),
    CONSTRAINT `fk_fha_facility` FOREIGN KEY (`facility_key`) REFERENCES `dim_facility` (`facility_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

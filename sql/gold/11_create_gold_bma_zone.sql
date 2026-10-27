-- ============================================================================
-- GOLD LAYER — dim_bma_zone + bridge_bma_zone_district + fact_migrant_worker_permit
-- (kmch-ml input-parity gap 2). New file, does not touch any table in
-- sql/gold/01-10 -- those stay exactly as-is.
--
-- BMA's own 10-zone grouping (each zone = several districts) is a
-- different grain than dim_geography/dim_area -- a zone cannot collapse
-- to a single geo_key, hence the many-to-many bridge table rather than a
-- geo_key column on dim_bma_zone itself.
--
-- fact_migrant_worker_permit's grain is (zone, permit_category,
-- nationality) -- nationality is NULL for the 3 bma_migrant_general
-- categories with no nationality breakdown available; both a
-- nationality-NULL row and 4 nationality rows exist for the other 3
-- categories (MOU import/renewal/illegal registration) -- see
-- sql/silver/22's header for why this is deliberate, not a duplication
-- bug. Single snapshot (2568 BE / 2025 CE), not a time series -- date_key
-- resolves to the one year this publication covers.
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `bridge_bma_zone_district`;
DROP TABLE IF EXISTS `fact_migrant_worker_permit`;
DROP TABLE IF EXISTS `dim_bma_zone`;

CREATE TABLE `dim_bma_zone` (
    `zone_key`    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `zone_id`      TINYINT      NOT NULL UNIQUE COMMENT 'BMA''s own 1-10 zone numbering',
    `zone_name_th`  VARCHAR(50) NOT NULL COMMENT '"พื้นที่ N"'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Many-to-many: a zone covers several districts, parsed from the source
-- file's own district-name list column (not hardcoded) and matched
-- against dim_geography.district_name.
CREATE TABLE `bridge_bma_zone_district` (
    `bridge_id`    BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `zone_key`      INT UNSIGNED NOT NULL,
    `district_name`  VARCHAR(150) NOT NULL COMMENT 'as given in the source file, matched against dim_geography.district_name',
    `geo_key`         INT UNSIGNED COMMENT 'resolved dim_geography FK, NULL if the district name did not match',
    UNIQUE KEY `ux_bbzd_zone_district` (`zone_key`, `district_name`),
    CONSTRAINT `fk_bbzd_zone` FOREIGN KEY (`zone_key`) REFERENCES `dim_bma_zone` (`zone_key`),
    CONSTRAINT `fk_bbzd_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `fact_migrant_worker_permit` (
    `fact_id`          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `zone_key`          INT UNSIGNED NOT NULL,
    `date_key`           INT UNSIGNED NOT NULL,
    `permit_category`     VARCHAR(100) NOT NULL,
    `nationality`          VARCHAR(50) COMMENT 'NULL = category-level total, no nationality breakdown available',
    `total`                 INT NOT NULL,
    `male`                   INT NOT NULL,
    `female`                  INT NOT NULL,
    KEY `ix_fmwp_zone` (`zone_key`),
    KEY `ix_fmwp_category` (`permit_category`),
    CONSTRAINT `fk_fmwp_zone` FOREIGN KEY (`zone_key`) REFERENCES `dim_bma_zone` (`zone_key`),
    CONSTRAINT `fk_fmwp_date` FOREIGN KEY (`date_key`) REFERENCES `dim_date` (`date_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

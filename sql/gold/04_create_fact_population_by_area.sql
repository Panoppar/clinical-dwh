-- ============================================================================
-- GOLD LAYER — fact_population_by_area
-- Grain: geo_key x date_key x admin_level.
-- is_rollup_row=0 already applied when loading -- Gold is structurally
-- incapable of carrying the embedded-rollup double-count defect this
-- project kept finding in Silver/Bronze; it's filtered here, not just
-- documented.
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `fact_population_by_area`;

CREATE TABLE `fact_population_by_area` (
    `fact_key`        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `geo_key`           INT UNSIGNED NOT NULL,
    `date_key`            INT          NOT NULL,
    `admin_level`           VARCHAR(12)  NOT NULL,
    `male_count`              BIGINT,
    `female_count`              BIGINT,
    `total_count`                 BIGINT,
    `house_count`                   BIGINT,
    `source_system`                   VARCHAR(20) NOT NULL COMMENT 'dopa | other_health',
    KEY `ix_fpba_geo_date` (`geo_key`, `date_key`),
    KEY `ix_fpba_date` (`date_key`),
    CONSTRAINT `fk_fpba_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`),
    CONSTRAINT `fk_fpba_date` FOREIGN KEY (`date_key`) REFERENCES `dim_date` (`date_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

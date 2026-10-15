-- ============================================================================
-- GOLD LAYER — fact_population_age_sex
-- Grain: geo_key x date_key x age_sex_key x component_key.
-- NSO's national-level rows (no province) map to the 'country' geo_key.
-- Component/is_headline_total filtering is a dimension lookup here, not a
-- row exclusion -- unlike fact_population_by_area's rollup rows (which
-- really are duplicates of a coarser figure), every component here is a
-- legitimate distinct observation; summing correctly requires filtering
-- by component_key, which dim_population_component makes explicit.
--
-- GOTCHA, confirmed by direct testing: `is_headline_total=1` ALONE is not
-- enough to safely SUM() -- it only narrows to the DEM_IND24 indicator,
-- which itself has many rows (one per sex x age slice). Summing
-- is_headline_total=1 without ALSO joining dim_age_sex and filtering
-- sex='total' AND age_qualifier='total' silently returns 2x-4x the real
-- figure (confirmed: country-level 2024 read 263,804,840 -- 4x the real
-- 65,951,210 -- until both filters were added). Always filter all three:
-- is_headline_total=1, sex='total', age_qualifier='total'.
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `fact_population_age_sex`;

CREATE TABLE `fact_population_age_sex` (
    `fact_key`         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `geo_key`            INT UNSIGNED NOT NULL,
    `date_key`             INT          NOT NULL,
    `age_sex_key`            INT UNSIGNED NOT NULL,
    `component_key`            INT UNSIGNED NOT NULL,
    `is_headline_total`          TINYINT(1)   NOT NULL DEFAULT 0,
    `population_count`             BIGINT,
    `source_system`                  VARCHAR(20) NOT NULL COMMENT 'nso | other_health',
    KEY `ix_fpas_geo_date` (`geo_key`, `date_key`),
    KEY `ix_fpas_headline` (`is_headline_total`),
    CONSTRAINT `fk_fpas_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`),
    CONSTRAINT `fk_fpas_date` FOREIGN KEY (`date_key`) REFERENCES `dim_date` (`date_key`),
    CONSTRAINT `fk_fpas_age_sex` FOREIGN KEY (`age_sex_key`) REFERENCES `dim_age_sex` (`age_sex_key`),
    CONSTRAINT `fk_fpas_component` FOREIGN KEY (`component_key`) REFERENCES `dim_population_component` (`component_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

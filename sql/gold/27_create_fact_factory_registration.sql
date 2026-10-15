-- ============================================================================
-- GOLD LAYER — fact_factory_registration
-- Grain: one row per factory_list record (11,862 rows -- a real event
-- log, not one-row-per-factory; see dim_factory for the 5,976-factory
-- descriptive dimension). date_key uses permit_year_ce (Jan 1
-- representative), same convention as other year-only Gold facts.
--
-- geo_key resolves to subdistrict level via a compound (district,
-- sub_district) text match against dim_geography -- confirmed by direct
-- testing that subdistrict name alone is ambiguous (178 matches for 172
-- distinct combos, since some subdistrict names repeat across
-- districts), while the compound match is clean (171/172, one
-- genuinely unmatched combo stays NULL rather than guessed).
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `fact_factory_registration`;

CREATE TABLE `fact_factory_registration` (
    `fact_key`             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `factory_key`            INT UNSIGNED NOT NULL,
    `geo_key`                  INT UNSIGNED NULL,
    `date_key`                   INT          NOT NULL,
    `building_value`               DECIMAL(20,2),
    `land_value`                     DECIMAL(20,2),
    `machinery_value`                 DECIMAL(20,2),
    `working_capital`                   DECIMAL(20,2),
    `total_investment`                    DECIMAL(20,2),
    `male_workers`                           INT,
    `female_workers`                          INT,
    `total_workers`                             INT,
    `total_horsepower`                            DECIMAL(20,2),
    `factory_area_sqm`                              DECIMAL(20,2),
    `building_area_sqm`                               DECIMAL(20,2),
    KEY `ix_ffr_geo_date` (`geo_key`, `date_key`),
    KEY `ix_ffr_factory` (`factory_key`),
    CONSTRAINT `fk_ffr_factory` FOREIGN KEY (`factory_key`) REFERENCES `dim_factory` (`factory_key`),
    CONSTRAINT `fk_ffr_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`),
    CONSTRAINT `fk_ffr_date` FOREIGN KEY (`date_key`) REFERENCES `dim_date` (`date_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- Silver layer DDL — cleansed external population reference tables.
-- See docs/03_external_reference_sources.md for source provenance/license.
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `population_reference_age_sex`;
DROP TABLE IF EXISTS `population_reference_subdistrict`;

CREATE TABLE `population_reference_subdistrict` (
  `province_code` VARCHAR(10) NOT NULL,
  `province_name` VARCHAR(100) NOT NULL,
  `regoffice_code` VARCHAR(10) NOT NULL,
  `regoffice_name` VARCHAR(150) NULL,
  `subdistrict_code` VARCHAR(15) NOT NULL,
  `subdistrict_name` VARCHAR(150) NULL,
  `village_code` VARCHAR(20) NOT NULL,
  `village_name` VARCHAR(150) NULL,
  `grain_level` VARCHAR(15) NOT NULL,   -- country | province | district | subdistrict | village
  `male` INT NOT NULL,
  `female` INT NOT NULL,
  `total` INT NOT NULL,
  `house` INT NOT NULL,
  `yymm` VARCHAR(10) NOT NULL,
  KEY `ix_prs_province_code` (`province_code`),
  KEY `ix_prs_regoffice_code` (`regoffice_code`),
  KEY `ix_prs_subdistrict_code` (`subdistrict_code`),
  KEY `ix_prs_grain_level` (`grain_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `population_reference_age_sex` (
  `scope` VARCHAR(10) NOT NULL,          -- national | province
  `province_code` VARCHAR(10) NULL,       -- NULL for scope = national
  `province_name` VARCHAR(100) NULL,
  `sex` VARCHAR(10) NOT NULL,             -- Total | Male | Female
  `age_label` VARCHAR(20) NOT NULL,       -- original SDMX AGE code, kept for traceability
  `age_exact` INT NULL,                   -- populated when age_qualifier = 'exact'
  `age_qualifier` VARCHAR(10) NOT NULL,   -- exact | le | ge | total | other
  `year_be` INT NOT NULL,                 -- Thai Buddhist Era year
  `year_ce` INT NOT NULL,                 -- Gregorian year (year_be - 543)
  `population_count` INT NULL,
  KEY `ix_pras_scope` (`scope`),
  KEY `ix_pras_province_code` (`province_code`),
  KEY `ix_pras_sex` (`sex`),
  KEY `ix_pras_age_exact` (`age_exact`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

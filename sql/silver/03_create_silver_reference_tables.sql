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

-- CRITICAL: `indicator_code` is part of this table's natural grain. The NSO
-- source publishes FOUR different population measures per (scope, province,
-- sex, age, year) cell, and they are NOT alternative estimates of the same
-- thing -- DEM_IND24 is the headline total and the other three are its
-- mutually exclusive components:
--
--   DEM_IND24  "Population from registration"  = TOTAL  (65,951,210 national)
--     +-- DEM_IND109 "Registered in a household registration"  (65,588,431)
--     +-- DEM_IND48  "Central house registration"                 (345,830)
--     +-- DEM_IND50  "During move (mid-transfer)"                  (16,949)
--
-- Verified: 65,588,431 + 345,830 + 16,949 = 65,951,210 exactly.
--
-- An earlier version of this table omitted indicator_code entirely, which
-- collapsed those four measures into what looked like four duplicate rows
-- and made any SUM() return exactly 2x the true population. Keep this
-- column, and filter to a single indicator before aggregating.
CREATE TABLE `population_reference_age_sex` (
  `scope` VARCHAR(10) NOT NULL,          -- national | province
  `province_code` VARCHAR(10) NULL,       -- NULL for scope = national
  `province_name` VARCHAR(100) NULL,
  `indicator_code` VARCHAR(20) NOT NULL,  -- DEM_IND24 | DEM_IND109 | DEM_IND48 | DEM_IND50
  `indicator_name_en` VARCHAR(100) NULL,
  `is_headline_total` TINYINT(1) NOT NULL, -- 1 only for DEM_IND24; filter on this to avoid double-counting
  `sex` VARCHAR(10) NOT NULL,             -- Total | Male | Female
  `age_label` VARCHAR(20) NOT NULL,       -- original SDMX AGE code, kept for traceability
  `age_exact` INT NULL,                   -- populated when age_qualifier is exact | le | ge | gt | lt
  `age_qualifier` VARCHAR(10) NOT NULL,   -- exact | le | ge | gt | lt | total | other
  `year_be` INT NOT NULL,                 -- Thai Buddhist Era year
  `year_ce` INT NOT NULL,                 -- Gregorian year (year_be - 543)
  `population_count` INT NULL,
  KEY `ix_pras_scope` (`scope`),
  KEY `ix_pras_province_code` (`province_code`),
  KEY `ix_pras_indicator` (`indicator_code`),
  KEY `ix_pras_headline` (`is_headline_total`),
  KEY `ix_pras_sex` (`sex`),
  KEY `ix_pras_age_exact` (`age_exact`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

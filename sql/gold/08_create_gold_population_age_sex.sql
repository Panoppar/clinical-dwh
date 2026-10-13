-- ============================================================================
-- Gold layer DDL — national/provincial population by age x sex.
-- Source: NSO. Promotes silver.population_reference_age_sex into Gold so
-- Metabase (gold-only via metabase_ro) can build population-pyramid
-- style panels.
--
-- ⚠ ALWAYS FILTER BY INDICATOR BEFORE AGGREGATING.
-- The NSO source publishes four population measures per cell, where
-- DEM_IND24 is the TOTAL and the other three are its mutually exclusive
-- components (household / central-house / mid-transfer registration).
-- SUM()ing without filtering returns exactly 2x the true population --
-- a real defect that shipped to a live dashboard once already (it showed
-- Thailand at 130.9M against a true ~66M). Use:
--     WHERE is_headline_total = 1
-- unless you specifically want the component breakdown. See
-- docs/02_data_dictionary.md for the full indicator table.
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `Dim_Population_By_Age_Sex`;
CREATE TABLE `Dim_Population_By_Age_Sex` (
  `scope`              VARCHAR(10) NOT NULL,   -- national | province
  `province_code`      INT NULL,
  `province_name_th`   VARCHAR(100) NULL,
  `province_name_en`   VARCHAR(100) NULL,
  `indicator_code`     VARCHAR(20) NOT NULL,   -- DEM_IND24 | DEM_IND109 | DEM_IND48 | DEM_IND50
  `indicator_name_en`  VARCHAR(100) NULL,
  `is_headline_total`  TINYINT(1) NOT NULL,    -- 1 only for DEM_IND24 -- filter on this
  `sex`                VARCHAR(10) NOT NULL,   -- Total | Male | Female
  `age_label`          VARCHAR(20) NOT NULL,
  `age_exact`          INT NULL,
  `age_qualifier`      VARCHAR(10) NOT NULL,   -- exact | le | ge | gt | lt | total | other
  `year_be`            INT NOT NULL,
  `year_ce`            INT NOT NULL,
  `population_count`   INT NULL,
  KEY `ix_gpas_scope` (`scope`),
  KEY `ix_gpas_province_code` (`province_code`),
  KEY `ix_gpas_indicator` (`indicator_code`),
  KEY `ix_gpas_headline` (`is_headline_total`),
  KEY `ix_gpas_sex` (`sex`),
  KEY `ix_gpas_age_exact` (`age_exact`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

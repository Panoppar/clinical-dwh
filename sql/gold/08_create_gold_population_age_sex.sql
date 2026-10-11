-- ============================================================================
-- Gold layer DDL — national/provincial population by age x sex.
-- Source: NSO. Promotes silver.population_reference_age_sex into Gold so
-- Metabase (gold-only via metabase_ro) can build population-pyramid
-- style panels.
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `Dim_Population_By_Age_Sex`;
CREATE TABLE `Dim_Population_By_Age_Sex` (
  `scope`             VARCHAR(10) NOT NULL,   -- national | province
  `province_code`     INT NULL,
  `province_name_th`  VARCHAR(100) NULL,
  `province_name_en`  VARCHAR(100) NULL,
  `sex`               VARCHAR(10) NOT NULL,    -- Total | Male | Female
  `age_label`         VARCHAR(20) NOT NULL,
  `age_exact`         INT NULL,
  `age_qualifier`     VARCHAR(10) NOT NULL,    -- exact | le | ge | total | other
  `year_be`           INT NOT NULL,
  `year_ce`           INT NOT NULL,
  `population_count`  INT NULL,
  KEY `ix_gpas_scope` (`scope`),
  KEY `ix_gpas_province_code` (`province_code`),
  KEY `ix_gpas_sex` (`sex`),
  KEY `ix_gpas_age_exact` (`age_exact`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

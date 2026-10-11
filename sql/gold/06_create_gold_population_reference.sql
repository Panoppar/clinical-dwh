-- ============================================================================
-- Gold layer DDL — district-level population reference (denominator for
-- catchment coverage-rate KPIs).
--
-- This exists because the first version of the coverage-rate KPI query
-- joined Dim_Patient directly against silver.population_reference_subdistrict
-- — which breaks the "Metabase connects strictly to Gold" rule, since the
-- metabase_ro account has SELECT on gold.* only and cannot see silver.* at
-- all (confirmed via SHOW GRANTS). This table materializes exactly what
-- that KPI needs, inside Gold.
--
-- Grain: one row per (district_code, year_ce) — the source data is a
-- 28-point year-end time series (BE2536-2563 / CE1993-2020), kept at full
-- grain rather than collapsed to a single year, so population-trend KPIs
-- are possible later without re-deriving from Silver.
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `Dim_District_Population`;
CREATE TABLE `Dim_District_Population` (
  `district_code`     INT NOT NULL,
  `year_ce`           INT NOT NULL,          -- Gregorian year (yymm's BE year - 543)
  `district_name_th`  VARCHAR(100) NULL,
  `district_name_en`  VARCHAR(100) NULL,
  `province_code`     INT NOT NULL,
  `province_name_th`  VARCHAR(100) NULL,
  `province_name_en`  VARCHAR(100) NULL,
  `male`              INT NOT NULL,
  `female`            INT NOT NULL,
  `total`             INT NOT NULL,
  `house`             INT NOT NULL,
  PRIMARY KEY (`district_code`, `year_ce`),
  KEY `ix_gddp_province_code` (`province_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Gold layer DDL — local-area health & catchment tables.
--
-- Promotes the five Silver tables that were previously cleansed but never
-- surfaced to Gold (and therefore invisible to Metabase, which can only
-- read gold.*).
--
-- The two "wide" source tables (count_2567 / count_2568 columns) are
-- pivoted to LONG here -- one row per (entity, year) with a proper
-- year_ce column -- rather than copied as-is. Wide year columns force
-- every BI consumer to hand-write a UNION to compare years; long format
-- makes year an ordinary filterable dimension.
--
-- Every fact that has one carries `is_aggregate_row` through from Silver.
-- These sources ship pre-summed total rows inside the detail, so an
-- unfiltered SUM() silently returns 2x. Always add `AND is_aggregate_row = 0`.
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `Fact_Disease_Case_Trend`;
DROP TABLE IF EXISTS `Fact_Subdistrict_Case_Trend`;
DROP TABLE IF EXISTS `Fact_Morbidity_By_Group`;
DROP TABLE IF EXISTS `Fact_Disease_Annual_Count`;
DROP TABLE IF EXISTS `Dim_Catchment_Place`;

-- Long-format: one row per (disease, year). Source scope differs from
-- Fact_Disease_Annual_Count -- verified, they are NOT the same data
-- (2024 influenza: 8,297 here vs 19,921 there), so they stay separate.
CREATE TABLE `Fact_Disease_Case_Trend` (
  `disease_th`        VARCHAR(200) NOT NULL,
  `year_ce`           INT NOT NULL,
  `case_count`        INT NULL,
  `is_aggregate_row`  TINYINT(1) NOT NULL DEFAULT 0,
  KEY `ix_fdct_disease` (`disease_th`),
  KEY `ix_fdct_year` (`year_ce`),
  KEY `ix_fdct_aggregate` (`is_aggregate_row`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Long-format: one row per (district, subdistrict, year).
CREATE TABLE `Fact_Subdistrict_Case_Trend` (
  `district_th`       VARCHAR(100) NULL,
  `subdistrict_th`    VARCHAR(100) NULL,
  `year_ce`           INT NOT NULL,
  `case_count`        INT NULL,
  `is_aggregate_row`  TINYINT(1) NOT NULL DEFAULT 0,
  KEY `ix_fsct_district` (`district_th`),
  KEY `ix_fsct_year` (`year_ce`),
  KEY `ix_fsct_aggregate` (`is_aggregate_row`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Already long in Silver. Morbidity by ICD-ish disease group x sex.
CREATE TABLE `Fact_Morbidity_By_Group` (
  `year_ce`           INT NULL,
  `province_th`       VARCHAR(100) NULL,
  `disease_group_th`  VARCHAR(200) NULL,
  `sex`               VARCHAR(10) NULL,
  `case_count`        INT NULL,
  `is_aggregate_row`  TINYINT(1) NOT NULL DEFAULT 0,
  KEY `ix_fmbg_year` (`year_ce`),
  KEY `ix_fmbg_sex` (`sex`),
  KEY `ix_fmbg_aggregate` (`is_aggregate_row`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Already long in Silver. No aggregate rows found in this one (its
-- "โรคไข้เลือดออกรวม (DF+DHF+DSS)" entry has no separate subtype rows in
-- this table, so it is a legitimate single disease, not a rollup).
CREATE TABLE `Fact_Disease_Annual_Count` (
  `year_ce`     INT NULL,
  `disease_th`  VARCHAR(200) NULL,
  `case_count`  INT NULL,
  KEY `ix_fdac_year` (`year_ce`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Catchment places around KMCH: travel distance/time and a market-potential
-- label. district/province are populated for ~70% of rows (2,604 of 3,742)
-- -- the basic-shape source files carry no address columns at all.
CREATE TABLE `Dim_Catchment_Place` (
  `category`              VARCHAR(50) NULL,
  `place_name_th`         VARCHAR(200) NULL,
  `place_name_en`         VARCHAR(200) NULL,
  `subdistrict_th`        VARCHAR(100) NULL,
  `district_th`           VARCHAR(100) NULL,
  `district_name_en`      VARCHAR(100) NULL,
  `province_th`           VARCHAR(100) NULL,
  `avg_distance_km`       DECIMAL(6,2) NULL,
  `avg_travel_time_mins`  INT NULL,
  `market_potential`      VARCHAR(100) NULL,
  KEY `ix_dcp_category` (`category`),
  KEY `ix_dcp_district` (`district_th`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

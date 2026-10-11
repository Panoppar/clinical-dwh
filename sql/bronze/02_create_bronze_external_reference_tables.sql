-- ============================================================================
-- Bronze layer DDL — external reference data (Phase 1).
--
-- Unlike 01_create_bronze_tables.sql (1:1 replicas of the vaccinework OLTP
-- database), these tables land flat-file population reference data from
-- outside sources, used to build real denominators for catchment/coverage
-- KPIs. See docs/03_external_reference_sources.md for provenance, license,
-- and the list of source groups deliberately NOT included in this load.
--
-- As with the OLTP bronze tables: raw values only, no type coercion or
-- cleansing (e.g. numbers with thousand-separator commas are kept as
-- VARCHAR here and parsed in Silver).
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `dopa_population_monthly`;
CREATE TABLE `dopa_population_monthly` (
  `yymm` VARCHAR(10),
  `province_code` VARCHAR(10),
  `province_name` VARCHAR(100),
  `regoffice_code` VARCHAR(10),
  `regoffice_name` VARCHAR(150),
  `subdistrict_code` VARCHAR(15),
  `subdistrict_name` VARCHAR(150),
  `village_code` VARCHAR(20),
  `village_name` VARCHAR(150),
  `male_raw` VARCHAR(20),
  `female_raw` VARCHAR(20),
  `total_raw` VARCHAR(20),
  `house_raw` VARCHAR(20),
  `_bronze_loaded_at` TIMESTAMP NULL,
  `_source_system` VARCHAR(50),
  `_source_file` VARCHAR(100),
  KEY `ix_dopa_province_code` (`province_code`),
  KEY `ix_dopa_regoffice_code` (`regoffice_code`),
  KEY `ix_dopa_subdistrict_code` (`subdistrict_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `nso_population_registration`;
CREATE TABLE `nso_population_registration` (
  `dataflow` VARCHAR(50),
  `pop_subj` VARCHAR(30),
  `pop_ind` VARCHAR(30),
  `sex_code` VARCHAR(5),
  `age_code` VARCHAR(20),
  `cwt_code` VARCHAR(10),       -- province code when present, else '_T'
  `amphoe_code` VARCHAR(10),
  `tambon_code` VARCHAR(10),
  `unit` VARCHAR(10),
  `freq` VARCHAR(5),
  `time_period` VARCHAR(10),     -- Thai Buddhist Era year, e.g. 2567
  `obs_value` VARCHAR(20),
  `source_th` TEXT,
  `note` TEXT,
  `obs_value_alt` VARCHAR(20),   -- extra trailing column present only in the province-level export
  `_bronze_loaded_at` TIMESTAMP NULL,
  `_source_system` VARCHAR(50),
  `_source_file` VARCHAR(100),
  KEY `ix_nso_cwt_code` (`cwt_code`),
  KEY `ix_nso_age_code` (`age_code`),
  KEY `ix_nso_sex_code` (`sex_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

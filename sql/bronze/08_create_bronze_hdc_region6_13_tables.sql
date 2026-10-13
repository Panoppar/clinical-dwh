-- =====================================================================
-- Bronze Layer Table Design
-- Source: HDC (Health Data Center) API exports - region6_13_by_age_api
--
-- Translated from the provided DDL at
-- share_unprocessed_20261010/HDC_region6_13_by_age_api_checked/bronze_layer_table_design.sql
-- into MySQL 8.0 syntax: GENERATED ALWAYS AS IDENTITY -> AUTO_INCREMENT,
-- double-quoted identifiers -> backticks, NUMERIC -> DECIMAL(20,2) (source
-- blanks arrive as truly empty strings here, kept nullable).
--
-- Design principles (from the provided DDL):
--   1. One bronze table per source file (1:1 raw mirror), no business
--      transformation.
--   2. Dimension/identifier columns kept as VARCHAR to preserve source
--      formatting (zero-padded codes, hashed ids, free-text Thai province
--      names).
--   3. Measure columns kept as DECIMAL (nullable) since source blanks =
--      NULL counts.
--   4. Every table carries standard ingestion metadata columns prefixed
--      with "_".
--   5. Tables are grouped into three schema families, matching the folder
--      layout:
--        incidence/monthly      -> bronze.inc_monthly_*      (23-col monthly schema)
--        incidence/annual_target -> bronze.inc_annual_ihd    (13-col annual schema, mismatched vs monthly)
--        population_by_age      -> bronze.pop_age_*          (19-col pop_group/result_group schema)
--        death_by_age           -> bronze.death_age_*        (19-col pt_group/death_group schema)
-- =====================================================================

USE bronze;

DROP TABLE IF EXISTS `inc_monthly_asthma`;
DROP TABLE IF EXISTS `inc_monthly_copd`;
DROP TABLE IF EXISTS `inc_monthly_coronary`;
DROP TABLE IF EXISTS `inc_monthly_dm`;
DROP TABLE IF EXISTS `inc_monthly_ht`;
DROP TABLE IF EXISTS `inc_annual_ihd`;
DROP TABLE IF EXISTS `pop_age_ca_breast`;
DROP TABLE IF EXISTS `pop_age_ca_cervix`;
DROP TABLE IF EXISTS `pop_age_ca_lung`;
DROP TABLE IF EXISTS `pop_age_copd`;
DROP TABLE IF EXISTS `pop_age_coronary`;
DROP TABLE IF EXISTS `pop_age_dm`;
DROP TABLE IF EXISTS `pop_age_emphysema`;
DROP TABLE IF EXISTS `pop_age_ht`;
DROP TABLE IF EXISTS `pop_age_stroke`;
DROP TABLE IF EXISTS `death_age_copd`;
DROP TABLE IF EXISTS `death_age_coronary`;
DROP TABLE IF EXISTS `death_age_dm`;
DROP TABLE IF EXISTS `death_age_ht`;

-- ---------------------------------------------------------------------
-- SECTION 1: INCIDENCE - MONTHLY SCHEMA (target, result, result10..result09)
-- ---------------------------------------------------------------------
CREATE TABLE `inc_monthly_asthma` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `target` DECIMAL(20,2), `result` DECIMAL(20,2),
    `result10` DECIMAL(20,2), `result11` DECIMAL(20,2), `result12` DECIMAL(20,2),
    `result01` DECIMAL(20,2), `result02` DECIMAL(20,2), `result03` DECIMAL(20,2),
    `result04` DECIMAL(20,2), `result05` DECIMAL(20,2), `result06` DECIMAL(20,2),
    `result07` DECIMAL(20,2), `result08` DECIMAL(20,2), `result09` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Asthma - monthly incidence. Raw 1:1 load from s_asthma_incidence.csv.';

CREATE TABLE `inc_monthly_copd` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `target` DECIMAL(20,2), `result` DECIMAL(20,2),
    `result10` DECIMAL(20,2), `result11` DECIMAL(20,2), `result12` DECIMAL(20,2),
    `result01` DECIMAL(20,2), `result02` DECIMAL(20,2), `result03` DECIMAL(20,2),
    `result04` DECIMAL(20,2), `result05` DECIMAL(20,2), `result06` DECIMAL(20,2),
    `result07` DECIMAL(20,2), `result08` DECIMAL(20,2), `result09` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='COPD - monthly incidence. Raw 1:1 load from s_copd_incidence.csv.';

CREATE TABLE `inc_monthly_coronary` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `target` DECIMAL(20,2), `result` DECIMAL(20,2),
    `result10` DECIMAL(20,2), `result11` DECIMAL(20,2), `result12` DECIMAL(20,2),
    `result01` DECIMAL(20,2), `result02` DECIMAL(20,2), `result03` DECIMAL(20,2),
    `result04` DECIMAL(20,2), `result05` DECIMAL(20,2), `result06` DECIMAL(20,2),
    `result07` DECIMAL(20,2), `result08` DECIMAL(20,2), `result09` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Coronary artery disease - monthly incidence. Raw 1:1 load from s_coronary_incidence.csv.';

CREATE TABLE `inc_monthly_dm` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `target` DECIMAL(20,2), `result` DECIMAL(20,2),
    `result10` DECIMAL(20,2), `result11` DECIMAL(20,2), `result12` DECIMAL(20,2),
    `result01` DECIMAL(20,2), `result02` DECIMAL(20,2), `result03` DECIMAL(20,2),
    `result04` DECIMAL(20,2), `result05` DECIMAL(20,2), `result06` DECIMAL(20,2),
    `result07` DECIMAL(20,2), `result08` DECIMAL(20,2), `result09` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Diabetes mellitus - monthly incidence. Raw 1:1 load from s_dm_incidence.csv.';

CREATE TABLE `inc_monthly_ht` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `target` DECIMAL(20,2), `result` DECIMAL(20,2),
    `result10` DECIMAL(20,2), `result11` DECIMAL(20,2), `result12` DECIMAL(20,2),
    `result01` DECIMAL(20,2), `result02` DECIMAL(20,2), `result03` DECIMAL(20,2),
    `result04` DECIMAL(20,2), `result05` DECIMAL(20,2), `result06` DECIMAL(20,2),
    `result07` DECIMAL(20,2), `result08` DECIMAL(20,2), `result09` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Hypertension - monthly incidence. Raw 1:1 load from s_ht_incidence.csv.';

-- ---------------------------------------------------------------------
-- SECTION 2: INCIDENCE - ANNUAL TARGET/RESULT SCHEMA (mismatched vs monthly; split out)
-- ---------------------------------------------------------------------
CREATE TABLE `inc_annual_ihd` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `target` DECIMAL(20,2), `result` DECIMAL(20,2), `target1` DECIMAL(20,2), `result1` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Ischemic heart disease - annual target/result incidence (distinct schema). Raw 1:1 load from s_ihd_incidence_annual.csv.';

-- ---------------------------------------------------------------------
-- SECTION 3: POPULATION BY AGE GROUP SCHEMA (pop_groupN / result_groupN)
-- ---------------------------------------------------------------------
CREATE TABLE `pop_age_ca_breast` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `pop_group1` DECIMAL(20,2), `result_group1` DECIMAL(20,2),
    `pop_group2` DECIMAL(20,2), `result_group2` DECIMAL(20,2),
    `pop_group3` DECIMAL(20,2), `result_group3` DECIMAL(20,2),
    `pop_group4` DECIMAL(20,2), `result_group4` DECIMAL(20,2),
    `pop_group5` DECIMAL(20,2), `result_group5` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Breast cancer - population screened by age group. Raw 1:1 load from s_ca_breast_pop_age.csv.';

CREATE TABLE `pop_age_ca_cervix` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `pop_group1` DECIMAL(20,2), `result_group1` DECIMAL(20,2),
    `pop_group2` DECIMAL(20,2), `result_group2` DECIMAL(20,2),
    `pop_group3` DECIMAL(20,2), `result_group3` DECIMAL(20,2),
    `pop_group4` DECIMAL(20,2), `result_group4` DECIMAL(20,2),
    `pop_group5` DECIMAL(20,2), `result_group5` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Cervical cancer - population screened by age group. Raw 1:1 load from s_ca_cervix_pop_age.csv.';

CREATE TABLE `pop_age_ca_lung` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `pop_group1` DECIMAL(20,2), `result_group1` DECIMAL(20,2),
    `pop_group2` DECIMAL(20,2), `result_group2` DECIMAL(20,2),
    `pop_group3` DECIMAL(20,2), `result_group3` DECIMAL(20,2),
    `pop_group4` DECIMAL(20,2), `result_group4` DECIMAL(20,2),
    `pop_group5` DECIMAL(20,2), `result_group5` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Lung cancer - population screened by age group. Raw 1:1 load from s_ca_lung_pop_age.csv.';

CREATE TABLE `pop_age_copd` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `pop_group1` DECIMAL(20,2), `result_group1` DECIMAL(20,2),
    `pop_group2` DECIMAL(20,2), `result_group2` DECIMAL(20,2),
    `pop_group3` DECIMAL(20,2), `result_group3` DECIMAL(20,2),
    `pop_group4` DECIMAL(20,2), `result_group4` DECIMAL(20,2),
    `pop_group5` DECIMAL(20,2), `result_group5` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='COPD - population by age group. Raw 1:1 load from s_copd_pop_age.csv.';

CREATE TABLE `pop_age_coronary` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `pop_group1` DECIMAL(20,2), `result_group1` DECIMAL(20,2),
    `pop_group2` DECIMAL(20,2), `result_group2` DECIMAL(20,2),
    `pop_group3` DECIMAL(20,2), `result_group3` DECIMAL(20,2),
    `pop_group4` DECIMAL(20,2), `result_group4` DECIMAL(20,2),
    `pop_group5` DECIMAL(20,2), `result_group5` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Coronary artery disease - population by age group. Raw 1:1 load from s_coronary_pop_age.csv.';

CREATE TABLE `pop_age_dm` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `pop_group1` DECIMAL(20,2), `result_group1` DECIMAL(20,2),
    `pop_group2` DECIMAL(20,2), `result_group2` DECIMAL(20,2),
    `pop_group3` DECIMAL(20,2), `result_group3` DECIMAL(20,2),
    `pop_group4` DECIMAL(20,2), `result_group4` DECIMAL(20,2),
    `pop_group5` DECIMAL(20,2), `result_group5` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Diabetes mellitus - population by age group. Raw 1:1 load from s_dm_pop_age.csv.';

CREATE TABLE `pop_age_emphysema` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `pop_group1` DECIMAL(20,2), `result_group1` DECIMAL(20,2),
    `pop_group2` DECIMAL(20,2), `result_group2` DECIMAL(20,2),
    `pop_group3` DECIMAL(20,2), `result_group3` DECIMAL(20,2),
    `pop_group4` DECIMAL(20,2), `result_group4` DECIMAL(20,2),
    `pop_group5` DECIMAL(20,2), `result_group5` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Emphysema - population by age group. Raw 1:1 load from s_emphysema_pop_age.csv.';

CREATE TABLE `pop_age_ht` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `pop_group1` DECIMAL(20,2), `result_group1` DECIMAL(20,2),
    `pop_group2` DECIMAL(20,2), `result_group2` DECIMAL(20,2),
    `pop_group3` DECIMAL(20,2), `result_group3` DECIMAL(20,2),
    `pop_group4` DECIMAL(20,2), `result_group4` DECIMAL(20,2),
    `pop_group5` DECIMAL(20,2), `result_group5` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Hypertension - population by age group. Raw 1:1 load from s_ht_pop_age.csv.';

CREATE TABLE `pop_age_stroke` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `pop_group1` DECIMAL(20,2), `result_group1` DECIMAL(20,2),
    `pop_group2` DECIMAL(20,2), `result_group2` DECIMAL(20,2),
    `pop_group3` DECIMAL(20,2), `result_group3` DECIMAL(20,2),
    `pop_group4` DECIMAL(20,2), `result_group4` DECIMAL(20,2),
    `pop_group5` DECIMAL(20,2), `result_group5` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Stroke - population by age group. Raw 1:1 load from s_stroke_pop_age.csv.';

-- ---------------------------------------------------------------------
-- SECTION 4: DEATHS BY AGE GROUP SCHEMA (pt_groupN / death_groupN)
-- ---------------------------------------------------------------------
CREATE TABLE `death_age_copd` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `pt_group1` DECIMAL(20,2), `death_group1` DECIMAL(20,2),
    `pt_group2` DECIMAL(20,2), `death_group2` DECIMAL(20,2),
    `pt_group3` DECIMAL(20,2), `death_group3` DECIMAL(20,2),
    `pt_group4` DECIMAL(20,2), `death_group4` DECIMAL(20,2),
    `pt_group5` DECIMAL(20,2), `death_group5` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='COPD - deaths by age group. Raw 1:1 load from s_copd_death_age.csv.';

CREATE TABLE `death_age_coronary` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `pt_group1` DECIMAL(20,2), `death_group1` DECIMAL(20,2),
    `pt_group2` DECIMAL(20,2), `death_group2` DECIMAL(20,2),
    `pt_group3` DECIMAL(20,2), `death_group3` DECIMAL(20,2),
    `pt_group4` DECIMAL(20,2), `death_group4` DECIMAL(20,2),
    `pt_group5` DECIMAL(20,2), `death_group5` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Coronary artery disease - deaths by age group. Raw 1:1 load from s_coronary_death_age.csv.';

CREATE TABLE `death_age_dm` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `pt_group1` DECIMAL(20,2), `death_group1` DECIMAL(20,2),
    `pt_group2` DECIMAL(20,2), `death_group2` DECIMAL(20,2),
    `pt_group3` DECIMAL(20,2), `death_group3` DECIMAL(20,2),
    `pt_group4` DECIMAL(20,2), `death_group4` DECIMAL(20,2),
    `pt_group5` DECIMAL(20,2), `death_group5` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Diabetes mellitus - deaths by age group. Raw 1:1 load from s_dm_death_age.csv.';

CREATE TABLE `death_age_ht` (
    `_bronze_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_code` VARCHAR(10), `province_name` VARCHAR(150), `id` VARCHAR(64),
    `hospcode` VARCHAR(20), `areacode` VARCHAR(20), `flag_sent` VARCHAR(5),
    `date_com` VARCHAR(20), `b_year` VARCHAR(10),
    `pt_group1` DECIMAL(20,2), `death_group1` DECIMAL(20,2),
    `pt_group2` DECIMAL(20,2), `death_group2` DECIMAL(20,2),
    `pt_group3` DECIMAL(20,2), `death_group3` DECIMAL(20,2),
    `pt_group4` DECIMAL(20,2), `death_group4` DECIMAL(20,2),
    `pt_group5` DECIMAL(20,2), `death_group5` DECIMAL(20,2),
    `ip` VARCHAR(45),
    `_source_file_name` VARCHAR(255) NOT NULL, `_ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `_ingestion_batch_id` VARCHAR(64), `_source_row_num` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Hypertension - deaths by age group. Raw 1:1 load from s_ht_death_age.csv.';

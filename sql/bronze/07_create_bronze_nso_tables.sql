-- ============================================================================
-- BRONZE LAYER TABLE DESIGN — NSO (National Statistical Office) Population Data
-- ============================================================================
-- Source file -> bronze table mapping (grouped by exact schema), confirmed by
-- inspection of the real files:
--   1. POP_REG_National_BySex_AllIndicators_2560-2568.csv (14 cols, 162 rows)
--      POP_REG_National_2567_ByAge.csv (14 cols, 2509 rows)
--      -> bronze.pop_reg_national (identical 14-column schema; distinguished
--         by src_file_name)
--   2. POP_REG_ByProvince_2567.csv (15 cols, 1867 rows: same 14 + trailing "v")
--      -> bronze.pop_reg_province (different exact schema from pop_reg_national)
--   3. POP_REG_StructureMetadata_SDMX.xml (SDMX-ML structure/codelist file,
--      not row-level data) -> bronze.pop_reg_structure_metadata, landed as
--      raw XML (1 row)
--   4. POP_SUR_LaborForceSurvey_AllPeriods_2563-2567.csv (34-col bilingual
--      SDMX-CSV schema, 20740 rows) -> bronze.pop_sur_survey
--
-- Translated from the provided DDL at
-- share_unprocessed_20261010/NSO_checked/ddl/bronze_layer_tables.sql into
-- MySQL 8.0 syntax: GENERATED ALWAYS AS IDENTITY -> AUTO_INCREMENT,
-- double-quoted Thai identifiers -> backticks, REFERENCES clause unchanged
-- (MySQL InnoDB supports it the same way).
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `pop_reg_national`;
DROP TABLE IF EXISTS `pop_reg_province`;
DROP TABLE IF EXISTS `pop_reg_structure_metadata`;
DROP TABLE IF EXISTS `pop_sur_survey`;
DROP TABLE IF EXISTS `ingestion_log`;

-- ----------------------------------------------------------------------------
-- 0. Ingestion log — one row per file load, so every batch landed into the
--    tables below can be traced, re-run, or audited independently of the
--    row-level data.
-- ----------------------------------------------------------------------------
CREATE TABLE `ingestion_log` (
    `ingestion_id`        BIGINT        AUTO_INCREMENT PRIMARY KEY,
    `src_file_name`        VARCHAR(500)  NOT NULL,
    `src_dataflow_id`      VARCHAR(100)  COMMENT 'e.g. TNSO:DF_01POP_REG(1.3)',
    `target_table`         VARCHAR(200)  NOT NULL,
    `row_count`            BIGINT,
    `file_hash_md5`        VARCHAR(32),
    `ingested_at`          TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `ingestion_status`     VARCHAR(20)   NOT NULL DEFAULT 'SUCCESS' COMMENT 'SUCCESS | FAILED | PARTIAL'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 1. bronze.pop_reg_national
--    Source schema: DATAFLOW,POP_SUBJ,POP_IND,SEX,AGE,CWT,AMPHOE,TAMBON,UNIT,
--                    FREQ,TIME_PERIOD,OBS_VALUE,SOURCE,NOTE  (14 columns)
--    Covers: national-level registration totals by sex (2560-2568) AND the
--    national age-breakdown extract for 2567 — same exact schema, two files.
-- ----------------------------------------------------------------------------
CREATE TABLE `pop_reg_national` (
    `dataflow`              VARCHAR(100)   COMMENT 'e.g. TNSO:DF_01POP_REG(1.3)',
    `pop_subj`              VARCHAR(50)    COMMENT 'e.g. DEM_POP',
    `pop_ind`               VARCHAR(50)    COMMENT 'indicator code, e.g. DEM_IND49',
    `sex`                   VARCHAR(10)    COMMENT 'M | F | _T',
    `age`                   VARCHAR(20)    COMMENT '_T | Y1..Y100 | Y_LE1 | LUNAR ...',
    `cwt`                   VARCHAR(20)    COMMENT 'province code | _T',
    `amphoe`                VARCHAR(20)    COMMENT 'district code | _T',
    `tambon`                VARCHAR(20)    COMMENT 'sub-district code | _T',
    `unit`                  VARCHAR(20)    COMMENT 'e.g. PS',
    `freq`                  VARCHAR(10)    COMMENT 'e.g. A (annual)',
    `time_period`           VARCHAR(20)    COMMENT 'e.g. 2567',
    `obs_value`             VARCHAR(50)    COMMENT 'kept as string in bronze; cast in silver',
    `source`                VARCHAR(200)   COMMENT 'e.g. กรมการปกครอง',
    `note`                  VARCHAR(1000),

    `src_file_name`         VARCHAR(500)  NOT NULL,
    `src_row_number`        BIGINT,
    `ingested_at`           TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `ingestion_id`          BIGINT REFERENCES `ingestion_log` (`ingestion_id`),

    KEY `idx_pop_reg_national_ingestion` (`ingestion_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 2. bronze.pop_reg_province
--    Source schema: same 14 columns as above PLUS trailing "v" column
--    (OBS_VALUE repeated as float-formatted string, e.g. "20461.0") -> 15 cols.
-- ----------------------------------------------------------------------------
CREATE TABLE `pop_reg_province` (
    `dataflow`              VARCHAR(100),
    `pop_subj`              VARCHAR(50),
    `pop_ind`               VARCHAR(50),
    `sex`                   VARCHAR(10),
    `age`                   VARCHAR(20),
    `cwt`                   VARCHAR(20)    COMMENT 'populated with real province codes here',
    `amphoe`                VARCHAR(20),
    `tambon`                VARCHAR(20),
    `unit`                  VARCHAR(20),
    `freq`                  VARCHAR(10),
    `time_period`           VARCHAR(20),
    `obs_value`             VARCHAR(50),
    `source`                VARCHAR(200),
    `note`                  VARCHAR(1000),
    `v`                     VARCHAR(50)    COMMENT 'extra column unique to this file/schema',

    `src_file_name`         VARCHAR(500)  NOT NULL,
    `src_row_number`        BIGINT,
    `ingested_at`           TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `ingestion_id`          BIGINT REFERENCES `ingestion_log` (`ingestion_id`),

    KEY `idx_pop_reg_province_ingestion` (`ingestion_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 3. bronze.pop_reg_structure_metadata
--    Source: SDMX-ML structure/codelist XML (not row-level observation data).
--    Bronze convention for non-tabular sources: land the raw file verbatim
--    in one column, so silver/gold can parse dataflow/codelist definitions
--    on demand without re-touching the original file.
-- ----------------------------------------------------------------------------
CREATE TABLE `pop_reg_structure_metadata` (
    `structure_id`          VARCHAR(100)  COMMENT 'e.g. DF_01POP_REG',
    `structure_version`     VARCHAR(20)   COMMENT 'e.g. 1.3',
    `raw_xml`               LONGTEXT      NOT NULL COMMENT 'full verbatim file content',
    `file_prepared_at`      TIMESTAMP     NULL COMMENT 'from <message:Prepared> in the XML header',

    `src_file_name`         VARCHAR(500)  NOT NULL,
    `ingested_at`           TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `ingestion_id`          BIGINT REFERENCES `ingestion_log` (`ingestion_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 4. bronze.pop_sur_survey
--    Source schema: TNSO:DF_01POP_SUR(2.0) — 34-column bilingual SDMX-CSV
--    (every coded column is paired with its Thai label column). Labor force /
--    population survey data, quarterly and annual, 2563-2567.
-- ----------------------------------------------------------------------------
CREATE TABLE `pop_sur_survey` (
    `structure`              VARCHAR(50)    COMMENT 'e.g. DATAFLOW',
    `structure_id`           VARCHAR(100)   COMMENT 'e.g. TNSO:DF_01POP_SUR(2.0)',
    `structure_name`         VARCHAR(300)   COMMENT 'Thai dataflow name',
    `action`                 VARCHAR(10)    COMMENT 'e.g. I (insert)',
    `stat_list`               VARCHAR(50)    COMMENT 'indicator code, e.g. DEM_IND84',
    `รายการสถิติ`             VARCHAR(500)   COMMENT 'indicator label (Thai)',
    `list_status`             VARCHAR(20)    COMMENT 'e.g. STAT',
    `สถานะรายการ`             VARCHAR(100),
    `level_of_edu`            VARCHAR(30)    COMMENT 'e.g. ED07 | _T | _O',
    `ระดับการศึกษา`           VARCHAR(300),
    `sex`                     VARCHAR(10),
    `เพศ`                    VARCHAR(50),
    `age_gp`                  VARCHAR(30)    COMMENT 'e.g. Y25T29',
    `กลุ่มอายุ`               VARCHAR(100),
    `area`                     VARCHAR(20)    COMMENT 'region code, e.g. TH1',
    `พื้นที่ระดับภาค`          VARCHAR(200),
    `cwt`                      VARCHAR(20)    COMMENT 'province code | _T',
    `พื้นที่ระดับจังหวัด`       VARCHAR(200),
    `municipal`                VARCHAR(20)    COMMENT 'urban/rural code | _T',
    `พื้นที่ระดับเขตการปกครอง`  VARCHAR(200),
    `unit`                     VARCHAR(20)    COMMENT 'e.g. PS',
    `หน่วยวัด`                VARCHAR(100),
    `unit_mul`                 VARCHAR(10)    COMMENT 'multiplier, e.g. 3 (thousand)',
    `หน่วยวัดตัวคูณ`           VARCHAR(100),
    `freq`                     VARCHAR(10)    COMMENT 'e.g. Q | A',
    `ความถี่ในการเผยแพร่`       VARCHAR(100),
    `time_period`              VARCHAR(20)    COMMENT 'e.g. 2563-Q1, 2567',
    `ช่วงเวลา`                 VARCHAR(100),
    `obs_value`                VARCHAR(50)    COMMENT 'blank-able, kept as string',
    `ค่าสังเกต`                VARCHAR(100),
    `note`                     VARCHAR(1000),
    `หมายเหตุ`                VARCHAR(1000),
    `source`                   VARCHAR(200)   COMMENT 'e.g. สำนักงานสถิติแห่งชาติ',
    `แหล่งที่มา`               VARCHAR(200),

    `src_file_name`            VARCHAR(500)  NOT NULL,
    `src_row_number`           BIGINT,
    `ingested_at`              TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `ingestion_id`             BIGINT REFERENCES `ingestion_log` (`ingestion_id`),

    KEY `idx_pop_sur_survey_ingestion` (`ingestion_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

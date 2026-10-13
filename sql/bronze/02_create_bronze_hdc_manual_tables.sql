-- =====================================================================================
-- BRONZE LAYER TABLE DESIGN
-- Source  : HDC (Health Data Center, Thai Ministry of Public Health) manual CSV exports
-- Folder  : HDC_manual_exports_checked (4 categories x N exact-schema subfolders)
--
-- Translated from the provided Postgres-flavored DDL at
-- share_unprocessed_20261010/HDC_manual_exports_checked/bronze_layer_design.sql
-- into MySQL 8.0 syntax (same translation rules as sql/bronze/01_create_bronze_dopa_tables.sql):
--   BIGSERIAL                   -> BIGINT AUTO_INCREMENT PRIMARY KEY
--   JSONB                       -> JSON
--   TEXT (Postgres, unbounded)  -> TEXT
--   TIMESTAMPTZ                 -> TIMESTAMP
--   CREATE INDEX ... USING GIN (raw_data) -> dropped; MySQL has no GIN.
--     report_no/source_file/province/fiscal_year are already promoted to
--     real columns and indexed below, which covers the lookups bronze
--     actually needs; nothing queries into raw_data's JSON structure here.
-- Every other structural decision (column set, hybrid raw_data design,
-- which columns get promoted) is kept exactly as provided.
--
-- Why a hybrid "common columns + JSON payload" design instead of one table
-- per report (from the source DDL): the ~287 source files resolve to ~100
-- distinct reports (HDC indicator numbers) but only 35 DISTINCT COLUMN
-- SCHEMAS once grouped by exact header match (see each category's
-- _SCHEMA_INDEX.csv manifest). A handful of reports even change their own
-- header text between extracts because the HDC export tool bakes the
-- comparison year into a column name (report '18' in the NCD category:
-- confirmed by inspection -- its 2022 extract's header literally says
-- "...ปี 2564" / "...ปี 2565" while its 2023 extract says "...ปี 2565" /
-- "...ปี 2566"). Building 100+ rigid CREATE TABLEs would churn every time
-- HDC tweaks a label. Instead: promote the handful of dimension columns
-- present in virtually every export (fiscal year, health region, province,
-- area) into real columns for fast filtering/joins, and keep the full
-- original row -- every original Thai column name and value, unmodified
-- -- in a JSON payload.
--
-- Folder <-> table mapping:
--   01_การป่วยด้วยโรคไม่ติดต่อที่สำคัญ_NCD           -> bronze.ncd_reports
--   02_สาเหตุการป่วย-ตาย                              -> bronze.morbidity_mortality_causes
--   03_โรคจากการประกอบอาชีพและสิ่งแวดล้อม             -> bronze.occupational_environmental_diseases
--   04_การป่วยด้วยโรคจากมลพิษทางอากาศ                 -> bronze.air_pollution_diseases
--
-- Known data-quality note (from the provided design doc, section 5):
-- during the 2026-10-13 reorganization, 12 of the 13 original export rows
-- for NCD report no. '4' (source_table s_ht_incidence) were lost to a
-- filename-collision bug. The 1 surviving row is kept as
-- .../schema_02/..._PARTIAL_REMNANT.csv. The report was REBUILT the same
-- day from the public MOPH Open Data API, kept as
-- .../schema_02/..._RECONSTRUCTED_2026-10-13_from_opendata_moph_go_th.csv.
-- Both land as ordinary rows via the same generic loader -- no special
-- casing needed, the provenance is carried in source_file lineage alone.
-- This is a fresh API pull, not a byte-identical replay of the original
-- export: treat its FY2569 row as provisional (facility-level reporting
-- lags HDC's own cutoff by days to weeks).
-- =====================================================================================

USE bronze;

DROP TABLE IF EXISTS `ncd_reports`;
DROP TABLE IF EXISTS `morbidity_mortality_causes`;
DROP TABLE IF EXISTS `occupational_environmental_diseases`;
DROP TABLE IF EXISTS `air_pollution_diseases`;
DROP TABLE IF EXISTS `report_catalog`;
DROP TABLE IF EXISTS `schema_registry`;

-- -------------------------------------------------------------------------------------
-- 1. SCHEMA REGISTRY
--    One row per distinct exact column schema discovered in the source folder
--    (= one row per "schema_NN" subfolder created during file reorganization,
--    per category). This is the join key between the physical file layout and
--    the bronze tables, and the audit trail for "which reports share which schema".
-- -------------------------------------------------------------------------------------
CREATE TABLE `schema_registry` (
    `schema_registry_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `category_code`       VARCHAR(2)   NOT NULL COMMENT '01..04',
    `category_name`       VARCHAR(150) NOT NULL COMMENT 'Thai category name',
    `schema_folder`       VARCHAR(20)  NOT NULL COMMENT 'e.g. schema_01',
    `n_columns`           INT          NOT NULL,
    `columns_json`        JSON         NOT NULL COMMENT 'ordered array of original Thai column names, verbatim',
    `columns_hash`        VARCHAR(64)  NOT NULL COMMENT 'sha256 of columns_json, for fast equality checks on ingest',
    `report_numbers_json` JSON         NOT NULL COMMENT 'array of HDC report numbers (order_no) that use this schema',
    `example_report_name` VARCHAR(500),
    `first_seen_at`       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `ux_schema_registry_category_folder` (`category_code`, `schema_folder`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Catalog of the distinct exact column schemas found across the source CSV exports. Mirrors each category''s _SCHEMA_INDEX.csv manifest.';

-- -------------------------------------------------------------------------------------
-- 2. REPORT CATALOG (reference / lookup data, not raw report rows)
--    Loaded from the three catalog files kept in _reference/: these describe the HDC
--    indicator menu itself (category, order number, official report name) rather than
--    report DATA, so they get their own small reference table instead of living inside
--    one of the four data tables below.
-- -------------------------------------------------------------------------------------
CREATE TABLE `report_catalog` (
    `report_catalog_id`   BIGINT AUTO_INCREMENT PRIMARY KEY,
    `category_name`       VARCHAR(150) NOT NULL,
    `report_no`           VARCHAR(20)  NOT NULL COMMENT 'HDC order number, e.g. 1, 11.2, 24.2',
    `report_name`         VARCHAR(500) NOT NULL,
    `years_available`     VARCHAR(100) COMMENT 'raw text as exported, e.g. 2565 2566 2567 2568 2569',
    `export_status`       VARCHAR(100) COMMENT 'e.g. ดาวน์โหลดแล้ว, ข้าม (ไม่มีข้อมูล)',
    `export_note`         TEXT,
    `source_catalog_file` VARCHAR(255) NOT NULL COMMENT 'which _reference/*.csv this row came from',
    `loaded_at`           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY `ix_catalog_report_no` (`report_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------------------
-- 3. GENERIC COLUMN TEMPLATE shared by the four category bronze tables.
--    One table per category, each sharing the identical shape below.
-- -------------------------------------------------------------------------------------

-- 3a. Category 01 - NCD (Non-communicable diseases): cardiovascular, diabetes, hypertension,
--     COPD, cancers, stroke, asthma. The bulk of the corpus.
--     Typical row = one (province x fiscal year) observation of a rate or count indicator.
CREATE TABLE `ncd_reports` (
    `bronze_id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
    `source_file`           VARCHAR(255) NOT NULL,
    `source_folder`         VARCHAR(100) NOT NULL,
    `category_code`         VARCHAR(2)   NOT NULL DEFAULT '01',
    `report_no`             VARCHAR(20)  NOT NULL,
    `report_name`           VARCHAR(500) NOT NULL,
    `table_variant`         VARCHAR(20)  COMMENT 'table1 / table2 marker when a report exports >1 table, else NULL',
    `schema_registry_id`    BIGINT       REFERENCES `schema_registry` (`schema_registry_id`),
    `fiscal_year`            VARCHAR(10)  COMMENT 'ปีงบประมาณ, Buddhist Era, kept as text (raw, no casting in bronze)',
    `health_region`          VARCHAR(50)  COMMENT 'เขตสุขภาพ',
    `province`                VARCHAR(100) COMMENT 'จังหวัด',
    `area`                     VARCHAR(100) COMMENT 'พื้นที่ (present on some reports only)',
    `row_in_file`              INT          NOT NULL COMMENT '1-based data row position within the source file, for traceability',
    `raw_data`                 JSON         NOT NULL COMMENT 'the full original row: {"<exact original column name>": "<raw string value>", ...}',
    `ingested_at`               TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY `ix_ncd_source_file` (`source_file`),
    KEY `ix_ncd_report_no` (`report_no`),
    KEY `ix_ncd_province_year` (`province`, `fiscal_year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3b. Category 02 - Causes of morbidity / mortality (สาเหตุการป่วย-ตาย).
CREATE TABLE `morbidity_mortality_causes` (
    `bronze_id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
    `source_file`           VARCHAR(255) NOT NULL,
    `source_folder`         VARCHAR(100) NOT NULL,
    `category_code`         VARCHAR(2)   NOT NULL DEFAULT '02',
    `report_no`             VARCHAR(20)  NOT NULL,
    `report_name`           VARCHAR(500) NOT NULL,
    `table_variant`         VARCHAR(20),
    `schema_registry_id`    BIGINT       REFERENCES `schema_registry` (`schema_registry_id`),
    `fiscal_year`            VARCHAR(10),
    `health_region`          VARCHAR(50),
    `province`                VARCHAR(100),
    `area`                     VARCHAR(100),
    `row_in_file`              INT          NOT NULL,
    `raw_data`                 JSON         NOT NULL,
    `ingested_at`               TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY `ix_mmc_source_file` (`source_file`),
    KEY `ix_mmc_report_no` (`report_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3c. Category 03 - Occupational & environmental diseases (โรคจากการประกอบอาชีพและสิ่งแวดล้อม).
--     Highest schema diversity of the four categories (fine-grained sub-indicators x.1/x.2/x.3,
--     e.g. report_no '11.2', '24.2' -- confirmed decimal report numbers by inspection).
CREATE TABLE `occupational_environmental_diseases` (
    `bronze_id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
    `source_file`           VARCHAR(255) NOT NULL,
    `source_folder`         VARCHAR(100) NOT NULL,
    `category_code`         VARCHAR(2)   NOT NULL DEFAULT '03',
    `report_no`             VARCHAR(20)  NOT NULL,
    `report_name`           VARCHAR(500) NOT NULL,
    `table_variant`         VARCHAR(20),
    `schema_registry_id`    BIGINT       REFERENCES `schema_registry` (`schema_registry_id`),
    `fiscal_year`            VARCHAR(10),
    `health_region`          VARCHAR(50),
    `province`                VARCHAR(100),
    `area`                     VARCHAR(100),
    `row_in_file`              INT          NOT NULL,
    `raw_data`                 JSON         NOT NULL,
    `ingested_at`               TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY `ix_occ_source_file` (`source_file`),
    KEY `ix_occ_report_no` (`report_no`),
    KEY `ix_occ_province_year` (`province`, `fiscal_year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3d. Category 04 - Air-pollution-related illness (การป่วยด้วยโรคจากมลพิษทางอากาศ / PM2.5).
CREATE TABLE `air_pollution_diseases` (
    `bronze_id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
    `source_file`           VARCHAR(255) NOT NULL,
    `source_folder`         VARCHAR(100) NOT NULL,
    `category_code`         VARCHAR(2)   NOT NULL DEFAULT '04',
    `report_no`             VARCHAR(20)  NOT NULL,
    `report_name`           VARCHAR(500) NOT NULL,
    `table_variant`         VARCHAR(20),
    `schema_registry_id`    BIGINT       REFERENCES `schema_registry` (`schema_registry_id`),
    `fiscal_year`            VARCHAR(10),
    `health_region`          VARCHAR(50),
    `province`                VARCHAR(100),
    `area`                     VARCHAR(100),
    `row_in_file`              INT          NOT NULL,
    `raw_data`                 JSON         NOT NULL,
    `ingested_at`               TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY `ix_air_source_file` (`source_file`),
    KEY `ix_air_report_no` (`report_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

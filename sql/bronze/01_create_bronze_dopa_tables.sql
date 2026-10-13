-- =====================================================================
-- BRONZE LAYER — DOPA Population by Month and Area
-- Source: กรมการปกครอง (DOPA) ส่วนบริหารและพัฒนาเทคโนโลยีการทะเบียน
--         "จำนวนประชากรในประเทศไทย แยกตามพื้นที่" (province / district / subdistrict)
--
-- Translated from the provided Postgres-flavored DDL at
-- share_unprocessed_20261010/DOPA_population_by_month_and_area_checked/sql/bronze_layer_ddl.sql
-- into MySQL 8.0 syntax. Translation rules applied (same rules for every
-- future source in this project):
--   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY -> BIGINT AUTO_INCREMENT PRIMARY KEY
--   BOOLEAN                                         -> TINYINT(1)
--   TIMESTAMP (Postgres default now())              -> TIMESTAMP DEFAULT CURRENT_TIMESTAMP
--   COMMENT ON TABLE/COLUMN ...                     -> inline COMMENT '...'
--   CREATE SCHEMA IF NOT EXISTS                     -> dropped (schema already exists; see 00_init_schemas_and_grants.sql)
-- Every other structural decision (column set, lineage columns, which rows
-- get which flags) is kept exactly as provided.
--
-- Medallion-architecture bronze principles applied here (from the source DDL):
--   1. 1:1 fidelity with source files — no type casting, no dedup, no joins.
--   2. All business columns kept as TEXT/VARCHAR exactly as received
--      (source values include thousands separators e.g. "32,375,532",
--      and some source files replace Thai text with "?" — bronze must
--      not silently "fix" this; silver layer handles cleansing).
--   3. Every row carries lineage/audit columns identifying which source
--      file, format and schema-variant it came from, so the known
--      anomalies in this dataset (corrupted-text raw export, triplicated
--      HTML export) are traceable and filterable downstream instead of
--      being silently merged/deduped at load time.
--   4. Append-only / immutable. Re-ingesting a file adds a new batch_id,
--      it never updates rows in place.
-- =====================================================================

USE bronze;

DROP TABLE IF EXISTS `dopa_population_by_area_month`;
DROP TABLE IF EXISTS `dopa_source_file_registry`;
DROP TABLE IF EXISTS `dopa_metadata_file_registry`;

-- ---------------------------------------------------------------------
-- 1) Raw fact table — one row per administrative area per YYMM period,
--    as it appeared in the source file. Grain: country / province /
--    district / subdistrict row, for one Buddhist-era YYMM snapshot.
-- ---------------------------------------------------------------------
CREATE TABLE `dopa_population_by_area_month` (
    `bronze_id`                 BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- ===== business columns, kept as raw text (bronze = schema-on-read) =====
    `yymm`                      VARCHAR(4)    NOT NULL COMMENT 'Buddhist-era YYMM, e.g. 6312 = Dec BE2563 / Dec 2020 CE',
    `cc_code`                   VARCHAR(10)   COMMENT 'changwat (province) code; 0 = whole-country total row',
    `cc_desc`                   VARCHAR(100)  COMMENT 'province name (Thai); may be ?-corrupted in some sources',
    `rcode_code`                VARCHAR(10)   COMMENT 'amphoe / local registration office (district) code',
    `rcode_desc`                VARCHAR(150),
    `ccaatt_code`                VARCHAR(10)   COMMENT 'tambon (subdistrict) code',
    `ccaatt_desc`                VARCHAR(150),
    `ccaattmm_code`              VARCHAR(10)   COMMENT 'village code (always 0/blank in every file in this extract)',
    `ccaattmm_desc`              VARCHAR(150),
    `male`                       VARCHAR(20)   COMMENT 'raw text, thousands-separated, e.g. 32,375,532',
    `female`                     VARCHAR(20),
    `total`                      VARCHAR(20),
    `house`                      VARCHAR(20),

    -- ===== lineage / audit columns =====
    `admin_level`                VARCHAR(20)   NOT NULL COMMENT 'country | province | district | subdistrict (derived from which source file the row came from, not re-derived from the code columns above)',
    `source_file_name`           VARCHAR(255)  NOT NULL COMMENT 'renamed file this row was loaded from, e.g. population_by_district_snapshot_2024_12.html',
    `original_file_name`         VARCHAR(255)  COMMENT 'pre-rename source filename, e.g. stat_a67.xls',
    `source_format`              VARCHAR(20)   NOT NULL COMMENT 'csv_pipe | csv_comma | xlsx | html_table',
    `schema_variant`              VARCHAR(50)   NOT NULL COMMENT 'see dopa_source_file_registry.schema_variant',
    `source_row_number`          INT COMMENT '1-based row position within the source file/table',
    `is_duplicate_row`           TINYINT(1)    NOT NULL DEFAULT 0 COMMENT 'TRUE for rows 2 and 3 of the triplicated 2025-12 subdistrict export (same table repeated 3x)',
    `row_sha256`                 VARCHAR(64)   COMMENT 'hash of raw column values, for silver-layer dedup',
    `batch_id`                   VARCHAR(50)   NOT NULL COMMENT 'ingestion run identifier',
    `ingested_at`                 TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    KEY `ix_dopa_fact_yymm_level` (`yymm`, `admin_level`),
    KEY `ix_dopa_fact_codes` (`cc_code`, `rcode_code`, `ccaatt_code`),
    KEY `ix_dopa_fact_source` (`source_file_name`, `batch_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Bronze raw landing for all DOPA population-by-area files (province, district, subdistrict; master historical pipe-delimited exports and yearly HTML snapshot exports). No casting/dedup -- numeric columns retain source thousands separators; Thai text retains source corruption (?) where present. Known anomaly: 2025-12 subdistrict HTML export contains the same table 3x (is_duplicate_row flags rows 2 and 3 of that repeat).';


-- ---------------------------------------------------------------------
-- 2) Source file registry — one row per physical file ingested.
--    Lets downstream layers reason about coverage/gaps and anomalies
--    without re-deriving them from the fact table every time.
-- ---------------------------------------------------------------------
CREATE TABLE `dopa_source_file_registry` (
    `file_registry_id`          BIGINT AUTO_INCREMENT PRIMARY KEY,
    `source_file_name`           VARCHAR(255)  NOT NULL COMMENT 'renamed, content-matching name',
    `original_file_name`         VARCHAR(255)  NOT NULL COMMENT 'as originally delivered',
    `folder_path`                VARCHAR(500)  NOT NULL COMMENT 'e.g. subdistrict/html_yearly_snapshot',
    `admin_level`                 VARCHAR(20)   NOT NULL COMMENT 'province | district | subdistrict | metadata',
    `schema_variant`               VARCHAR(50)   NOT NULL COMMENT 'long_format_pipe_delimited | raw_source_corrupted_text | raw_source_clean_text | html_yearly_snapshot | html_yearly_snapshot_triplicated',
    `file_format`                  VARCHAR(20)   NOT NULL COMMENT 'csv | xlsx | html',
    `period_start_yymm`            VARCHAR(4),
    `period_end_yymm`               VARCHAR(4),
    `row_count_raw`                  INT,
    `distinct_table_count`            SMALLINT     DEFAULT 1 COMMENT '>1 flags concatenated/duplicated tables',
    `has_known_anomaly`                TINYINT(1)   NOT NULL DEFAULT 0,
    `anomaly_description`                TEXT,
    `batch_id`                             VARCHAR(50)  NOT NULL,
    `ingested_at`                           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='One row per ingested source file. Tracks the rename (original_file_name -> source_file_name), which schema variant/folder it lives in, and any known structural anomaly, e.g. the corrupted-text legacy CSV vs. its clean-text XLSX counterpart, or the triplicated 2025-12 subdistrict HTML export.';

-- Registry seed reflecting the current folder reorganization (verbatim from
-- the provided DDL's own INSERT block).
INSERT INTO `dopa_source_file_registry`
 (source_file_name, original_file_name, folder_path, admin_level, schema_variant, file_format,
  period_start_yymm, period_end_yymm, row_count_raw, distinct_table_count, has_known_anomaly,
  anomaly_description, batch_id)
VALUES
 ('population_by_province_1993_2020_dec_snapshot.csv', 'raaycchanghwad.csv',
  'province/long_format_pipe_delimited', 'province', 'long_format_pipe_delimited', 'csv',
  '3612', '6312', 2167, 1, 0, NULL, 'initial_load'),

 ('population_by_district_1993_2020_dec_snapshot.csv', 'raay-ameph.csv',
  'district/long_format_pipe_delimited', 'district', 'long_format_pipe_delimited', 'csv',
  '3612', '6312', 56361, 1, 0, NULL, 'initial_load'),

 ('population_by_district_1993_2020_dec_snapshot_RAW_corrupted_text.csv', 'stat_a.csv',
  'district/raw_source_variant', 'district', 'raw_source_corrupted_text', 'csv',
  '3612', '6312', 56361, 1, 1,
  'Thai province/district/subdistrict names replaced with "?" at source; same figures as the clean long_format_pipe_delimited district file. Keep for lineage, prefer the clean file for silver.',
  'initial_load'),

 ('population_by_district_1993_2020_dec_snapshot_RAW_clean_text.xlsx', 'stat_a.csv.xlsx',
  'district/raw_source_variant', 'district', 'raw_source_clean_text', 'xlsx',
  '3612', '6312', 56361, 1, 0,
  'Clean-text Excel counterpart of stat_a.csv; same data, Thai text intact.', 'initial_load'),

 ('population_by_district_snapshot_2024_12.html', 'stat_a67.xls',
  'district/html_yearly_snapshot', 'district', 'html_yearly_snapshot', 'html',
  '6712', '6712', 2531, 1, 0, NULL, 'initial_load'),

 ('population_by_subdistrict_1993_2020_dec_snapshot.csv', 'stat_t.txt',
  'subdistrict/long_format_pipe_delimited', 'subdistrict', 'long_format_pipe_delimited', 'csv',
  '3612', '6312', 294475, 1, 0,
  'datapackage.json declares this resource as raaytambl.csv; the delivered file was stat_t.txt.',
  'initial_load'),

 ('population_by_subdistrict_snapshot_2017_12.html', 'stat_t60.xls',
  'subdistrict/html_yearly_snapshot', 'subdistrict', 'html_yearly_snapshot', 'html',
  '6012', '6012', 11378, 1, 0, NULL, 'initial_load'),
 ('population_by_subdistrict_snapshot_2018_12.html', 'stat_t61.xls',
  'subdistrict/html_yearly_snapshot', 'subdistrict', 'html_yearly_snapshot', 'html',
  '6112', '6112', 11389, 1, 0, NULL, 'initial_load'),
 ('population_by_subdistrict_snapshot_2019_12.html', 'stat_t62.xls',
  'subdistrict/html_yearly_snapshot', 'subdistrict', 'html_yearly_snapshot', 'html',
  '6212', '6212', 11381, 1, 0, NULL, 'initial_load'),
 ('population_by_subdistrict_snapshot_2020_12.html', 'stat_t63.xls',
  'subdistrict/html_yearly_snapshot', 'subdistrict', 'html_yearly_snapshot', 'html',
  '6312', '6312', 11377, 1, 0, NULL, 'initial_load'),
 ('population_by_subdistrict_snapshot_2021_12.html', 'stat_t64.xls',
  'subdistrict/html_yearly_snapshot', 'subdistrict', 'html_yearly_snapshot', 'html',
  '6412', '6412', 11377, 1, 0, NULL, 'initial_load'),
 ('population_by_subdistrict_snapshot_2022_12.html', 'stat_t65.xls',
  'subdistrict/html_yearly_snapshot', 'subdistrict', 'html_yearly_snapshot', 'html',
  '6512', '6512', 11376, 1, 0, NULL, 'initial_load'),
 ('population_by_subdistrict_snapshot_2023_12.html', 'stat_t66.xls',
  'subdistrict/html_yearly_snapshot', 'subdistrict', 'html_yearly_snapshot', 'html',
  '6612', '6612', 11376, 1, 0, NULL, 'initial_load'),
 ('population_by_subdistrict_snapshot_2024_12.html', 'stat_t67.xls',
  'subdistrict/html_yearly_snapshot', 'subdistrict', 'html_yearly_snapshot', 'html',
  '6712', '6712', 11380, 1, 0, NULL, 'initial_load'),

 ('population_by_subdistrict_snapshot_2025_12_TRIPLICATED_3x.html', 'stat_t68.xls',
  'subdistrict/html_yearly_snapshot_triplicated_anomaly', 'subdistrict',
  'html_yearly_snapshot_triplicated', 'html',
  '6812', '6812', 34161, 3, 1,
  'File contains the same <table> (11,387 rows incl. header) concatenated 3 times with identical data in each copy. Load once into the fact table and flag the 2 repeats via is_duplicate_row, or dedupe at ingestion time.', 'initial_load');


-- ---------------------------------------------------------------------
-- 3) Metadata files (datapackage.json, data dictionary) are not tabular
--    and are not loaded into the fact table — kept as files under
--    metadata/ and referenced here by name only, for catalog completeness.
-- ---------------------------------------------------------------------
CREATE TABLE `dopa_metadata_file_registry` (
    `metadata_id`         BIGINT AUTO_INCREMENT PRIMARY KEY,
    `file_name`            VARCHAR(255) NOT NULL COMMENT 'datapackage.json | data_dictionary.html',
    `original_file_name`   VARCHAR(255) NOT NULL COMMENT 'datapackage.json | data-dictionary.url',
    `file_format`           VARCHAR(20)  NOT NULL COMMENT 'json | html',
    `description`             TEXT,
    `ingested_at`               TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `dopa_metadata_file_registry` (file_name, original_file_name, file_format, description)
VALUES
 ('datapackage.json', 'datapackage.json', 'json',
  'Frictionless-style datapackage manifest describing the 3 CSV resources and their declared schema.'),
 ('data_dictionary.html', 'data-dictionary.url', 'html',
  'Actual content is an HTML page (DOPA stat-by-year site export), not a URL shortcut file -- extension corrected from .url to .html to match content.');

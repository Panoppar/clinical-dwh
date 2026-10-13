-- ============================================================================
-- BRONZE LAYER (raw ingest) — DDL for 15 source-aligned tables + manifest
-- Source: other_health_and_population_tables_checked
--
-- Translated from the provided DDL at
-- share_unprocessed_20261010/other_health_and_population_tables_checked/bronze_layer_ddl.sql
-- into MySQL 8.0 syntax: STRING -> VARCHAR/TEXT, BIGINT (Postgres plain
-- bigint, no identity in the source) -> BIGINT AUTO_INCREMENT so each
-- table gets a real primary key, TIMESTAMP unchanged.
--
-- Conventions (from the provided DDL):
--   * One bronze table per DISTINCT source schema (not per category) --
--     zero transformation, no type casting. Native columns are kept as
--     VARCHAR/TEXT, including numbers that use Thai thousands-separators
--     (e.g. "19,921").
--   * Every table is prefixed with the same lineage/audit columns.
--
-- RESOLVED DURING TRANSLATION (TODO-VERIFY in the source DDL):
-- ncd_mortality_multisheet's "ปี YYYY" 3-sub-column structure was
-- confirmed by inspection against the real file (row 5 sub-headers read
-- "จำนวน | อัตรา | ประชากรกลางปี" for every year) -- columns below are
-- named accordingly instead of the stubbed ปีYYYY_ค่า1/2/3 placeholders.
--
-- ENCODING NOTE (found during translation, not flagged in the source
-- DDL): TWO files in this source are cp874/TIS-620 encoded rather than
-- UTF-8 -- confirmed by inspection: both sick_298group_long's 2568 file
-- AND both cause_of_death_top10_* csv files decode cleanly as cp874 but
-- fail as UTF-8. The loader auto-detects per file (try utf-8-sig, fall
-- back to cp874) rather than assuming one encoding source-wide.
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `sick_298group_long`;
DROP TABLE IF EXISTS `sick_298group_wide`;
DROP TABLE IF EXISTS `surveillance_top_diseases_2566`;
DROP TABLE IF EXISTS `surveillance_top_diseases_2567`;
DROP TABLE IF EXISTS `compare_cases_by_disease`;
DROP TABLE IF EXISTS `compare_cases_by_subdistrict`;
DROP TABLE IF EXISTS `ncd_mortality_multisheet`;
DROP TABLE IF EXISTS `cause_of_death_top10_with_rate`;
DROP TABLE IF EXISTS `cause_of_death_top10_no_rate`;
DROP TABLE IF EXISTS `population_by_age_subdistrict_bkk`;
DROP TABLE IF EXISTS `population_by_tambon_national`;
DROP TABLE IF EXISTS `elderly_dependency_by_district`;
DROP TABLE IF EXISTS `health_kpi_export`;
DROP TABLE IF EXISTS `community_count_by_district_bkk`;
DROP TABLE IF EXISTS `foreign_labor_permit_by_area_bkk`;
DROP TABLE IF EXISTS `_ingestion_manifest`;

-- ============================================================================
-- sick_298group_long
-- Source: 01_.../298กลุ่มโรค_รายจังหวัด_แยกเพศ_ยาว (2 files)
-- Grain: 1 row per (year, province, disease group, sex)
-- NOTE: source column is 'ชื่อกลุ่ม' in one file and 'ชื่อกลุ่ม(298โรค)' in
-- the other -- both land in this single 'ชื่อกลุ่ม' column; original label
-- kept in source_file_name.
-- ============================================================================
CREATE TABLE `sick_298group_long` (
  `bronze_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`       VARCHAR(255), `source_folder` VARCHAR(255), `source_sheet_name` VARCHAR(100),
  `source_row_number`      INT, `file_hash` VARCHAR(64), `ingestion_batch_id` VARCHAR(100),
  `ingested_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, `source_system` VARCHAR(100),
  `ปี`                     VARCHAR(10), `จังหวัด` VARCHAR(100), `ชื่อกลุ่ม` VARCHAR(300),
  `เพศ`                    VARCHAR(10), `จำนวน` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- sick_298group_wide
-- Source: 01_.../298กลุ่มโรค_รายจังหวัด_แยกเพศ_กว้าง (8 files, 407-414)
-- Grain: 1 row per disease group, per file. Province and year are NOT
-- present in the file body -- only in the filename -- so they are
-- extracted at landing time into file_province / file_year.
-- ============================================================================
CREATE TABLE `sick_298group_wide` (
  `bronze_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`       VARCHAR(255), `source_folder` VARCHAR(255), `source_sheet_name` VARCHAR(100),
  `source_row_number`      INT, `file_hash` VARCHAR(64), `ingestion_batch_id` VARCHAR(100),
  `ingested_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, `source_system` VARCHAR(100),
  `file_province`          VARCHAR(100) COMMENT 'derived from filename, not from file content',
  `file_year`              VARCHAR(10)  COMMENT 'derived from filename, not from file content',
  `ชื่อกลุ่ม(298โรค)`       VARCHAR(300), `ชาย` VARCHAR(50), `หญิง` VARCHAR(50), `รวม` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- surveillance_top_diseases_2566
-- Source: 01_.../10อันดับโรคเฝ้าระวัง_2566 (1 file)
-- ============================================================================
CREATE TABLE `surveillance_top_diseases_2566` (
  `bronze_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`       VARCHAR(255), `source_folder` VARCHAR(255), `source_sheet_name` VARCHAR(100),
  `source_row_number`      INT, `file_hash` VARCHAR(64), `ingestion_batch_id` VARCHAR(100),
  `ingested_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, `source_system` VARCHAR(100),
  `ปี`                     VARCHAR(10), `โรค` VARCHAR(200), `จำนวน` VARCHAR(50), `หน่วย` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- surveillance_top_diseases_2567
-- Source: 01_.../10อันดับโรคเฝ้าระวัง_2567 (1 file)
-- NOTE: schema differs from 2566 version (no 'หน่วย' column, 'ชื่อโรค' vs
-- 'โรค') -- kept as a separate bronze table by design.
-- ============================================================================
CREATE TABLE `surveillance_top_diseases_2567` (
  `bronze_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`       VARCHAR(255), `source_folder` VARCHAR(255), `source_sheet_name` VARCHAR(100),
  `source_row_number`      INT, `file_hash` VARCHAR(64), `ingestion_batch_id` VARCHAR(100),
  `ingested_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, `source_system` VARCHAR(100),
  `ปี`                     VARCHAR(10), `ชื่อโรค` VARCHAR(200), `จำนวน` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- compare_cases_by_disease
-- Source: 01_.../เปรียบเทียบผู้ป่วยรายโรค_2567-2568 (1 file)
-- ============================================================================
CREATE TABLE `compare_cases_by_disease` (
  `bronze_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`       VARCHAR(255), `source_folder` VARCHAR(255), `source_sheet_name` VARCHAR(100),
  `source_row_number`      INT, `file_hash` VARCHAR(64), `ingestion_batch_id` VARCHAR(100),
  `ingested_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, `source_system` VARCHAR(100),
  `โรค`                    VARCHAR(200), `ปี2567` VARCHAR(50), `ปี2568` VARCHAR(50), `ผลต่าง` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- compare_cases_by_subdistrict
-- Source: 01_.../เปรียบเทียบผู้ป่วยรายเขตแขวง_2567-2568 (1 file)
-- ============================================================================
CREATE TABLE `compare_cases_by_subdistrict` (
  `bronze_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`       VARCHAR(255), `source_folder` VARCHAR(255), `source_sheet_name` VARCHAR(100),
  `source_row_number`      INT, `file_hash` VARCHAR(64), `ingestion_batch_id` VARCHAR(100),
  `ingested_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, `source_system` VARCHAR(100),
  `เขต`                    VARCHAR(100), `แขวง` VARCHAR(100), `ปี2567` VARCHAR(50), `ปี2568` VARCHAR(50),
  `ผลต่าง`                 VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- ncd_mortality_multisheet
-- Source: 02_.../NCDรายจังหวัด_multi-sheet (1 file, 6 sheets)
-- source_sheet_name identifies which disease the row belongs to.
-- Sub-column ordering per year confirmed by inspection of the real file's
-- row-5 sub-header: จำนวน (count) | อัตรา (rate) | ประชากรกลางปี (mid-year population).
-- ============================================================================
CREATE TABLE `ncd_mortality_multisheet` (
  `bronze_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`       VARCHAR(255), `source_folder` VARCHAR(255), `source_sheet_name` VARCHAR(100),
  `source_row_number`      INT, `file_hash` VARCHAR(64), `ingestion_batch_id` VARCHAR(100),
  `ingested_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, `source_system` VARCHAR(100),
  `เขตสุขภาพ`               VARCHAR(100), `จังหวัด` VARCHAR(100),
  `ปี2562_จำนวน` VARCHAR(50), `ปี2562_อัตรา` VARCHAR(50), `ปี2562_ประชากรกลางปี` VARCHAR(50),
  `ปี2563_จำนวน` VARCHAR(50), `ปี2563_อัตรา` VARCHAR(50), `ปี2563_ประชากรกลางปี` VARCHAR(50),
  `ปี2564_จำนวน` VARCHAR(50), `ปี2564_อัตรา` VARCHAR(50), `ปี2564_ประชากรกลางปี` VARCHAR(50),
  `ปี2565_จำนวน` VARCHAR(50), `ปี2565_อัตรา` VARCHAR(50), `ปี2565_ประชากรกลางปี` VARCHAR(50),
  `ปี2566_จำนวน` VARCHAR(50), `ปี2566_อัตรา` VARCHAR(50), `ปี2566_ประชากรกลางปี` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- cause_of_death_top10_with_rate
-- Source: 02_.../สาเหตุการตาย10อันดับ_มีอัตราตาย (2 files: .csv + its
-- mis-encoded .xlsx twin). Both load through the same generic path: the
-- xlsx's Thai text is a deterministic, fully-recoverable cp1252->cp874
-- double-encoding bug (confirmed by inspection, not guessed -- "Ë¹èÇÂ"
-- round-trips to "หน่วย" exactly), so the loader corrects it at read time
-- rather than landing mojibake -- same treatment as the BOM-stripping
-- already applied to DOPA's HTML files, since this is a lossless
-- transport artifact, not source data corruption.
-- ============================================================================
CREATE TABLE `cause_of_death_top10_with_rate` (
  `bronze_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`       VARCHAR(255), `source_folder` VARCHAR(255), `source_sheet_name` VARCHAR(100),
  `source_row_number`      INT, `file_hash` VARCHAR(64), `ingestion_batch_id` VARCHAR(100),
  `ingested_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, `source_system` VARCHAR(100),
  `ปี`                     VARCHAR(10), `จังหวัด` VARCHAR(100), `สาเหตุการตาย` VARCHAR(200),
  `เพศชาย`                 VARCHAR(50), `เพศหญิง` VARCHAR(50), `รวม` VARCHAR(50),
  `อัตราการตายต่อประชากร`  VARCHAR(50), `หน่วย` VARCHAR(100), `ที่มา` VARCHAR(300)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- cause_of_death_top10_no_rate
-- Source: 02_.../สาเหตุการตาย10อันดับ_ไม่มีอัตราตาย (1 file)
-- ============================================================================
CREATE TABLE `cause_of_death_top10_no_rate` (
  `bronze_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`       VARCHAR(255), `source_folder` VARCHAR(255), `source_sheet_name` VARCHAR(100),
  `source_row_number`      INT, `file_hash` VARCHAR(64), `ingestion_batch_id` VARCHAR(100),
  `ingested_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, `source_system` VARCHAR(100),
  `ปี`                     VARCHAR(10), `จังหวัด` VARCHAR(100), `สาเหตุการตาย` VARCHAR(200),
  `ชาย`                    VARCHAR(50), `หญิง` VARCHAR(50), `รวม` VARCHAR(50), `หน่วย` VARCHAR(100),
  `ที่มา`                  VARCHAR(300)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- population_by_age_subdistrict_bkk
-- Source: 03_.../ประชากรรายอายุ_รายเขตกทม (2 files, Dec 2567 & Dec 2568)
-- Grain: 1 row per village/sub-district, per file. 228 columns confirmed by
-- inspection (9 identifier cols + 204 single-year-age x sex cols + 15
-- summary cols).
--
-- DEVIATION FROM THE PROVIDED DDL (confirmed necessary by testing, not
-- assumed): the provided schema declares all 228 as named columns. MySQL
-- InnoDB rejects this outright -- confirmed by direct testing against this
-- exact database that even 219 bare TEXT columns alone (no other columns)
-- exceed the 8126-byte row-size limit ("Row size too large"); TEXT/BLOB
-- still carry real per-column overhead toward that check, so splitting
-- VARCHAR into TEXT (tried first) did not fix it, and ROW_FORMAT=DYNAMIC
-- doesn't change this since it's a column-count problem, not a
-- column-length problem. Postgres has no equivalent hard limit (TOAST
-- handles wide rows differently), which is exactly the kind of
-- engine-specific adjustment the provided DDL's own header comment
-- anticipates ("adjust types for your target warehouse").
-- Fix: the 9 identifier columns stay named; the 219 age/sex/summary
-- columns collapse into one JSON payload column (age_sex_data), keyed by
-- their exact original Thai column names -- same hybrid pattern already
-- used in this project for HDC_manual_exports, for the same underlying
-- reason (a wide, repetitive column set). No information is lost: every
-- original column name and value is preserved, just addressed by JSON key
-- instead of by a named SQL column.
-- ============================================================================
CREATE TABLE `population_by_age_subdistrict_bkk` (
  `bronze_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`       VARCHAR(255), `source_folder` VARCHAR(255), `source_sheet_name` VARCHAR(100),
  `source_row_number`      INT, `file_hash` VARCHAR(64), `ingestion_batch_id` VARCHAR(100),
  `ingested_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, `source_system` VARCHAR(100),
  `ปีเดือน` VARCHAR(10), `รหัสจังหวัด` VARCHAR(20), `ชื่อจังหวัด` VARCHAR(100),
  `รหัสสำนักทะเบียน` VARCHAR(20), `ชื่อสำนักทะเบียน` VARCHAR(150),
  `รหัสตำบล` VARCHAR(20), `ชื่อตำบล` VARCHAR(150), `รหัสหมู่บ้าน` VARCHAR(20), `ชื่อหมู่บ้าน` VARCHAR(150),
  `age_sex_data` JSON NOT NULL COMMENT 'all 219 age/sex + summary columns, keyed by exact original Thai column name, e.g. {"ชาย < 1 ปี": "6", "หญิง < 1 ปี": "2", ...}'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- population_by_tambon_national
-- Source: 03_.../ประชากรรายตำบล_ทั่วประเทศ (1 file, YYMM=6812)
-- Grain: 1 row per administrative level (country/province/district/tambon),
-- nationwide. Same DOPA-style schema as this project's DOPA source, but
-- kept in its own bronze table per this source's own DDL -- no
-- cross-source deduplication at bronze.
--
-- UNDOCUMENTED ANOMALY (found independently, not flagged in this source's
-- own design doc): this xlsx is triplicated internally -- the header row
-- repeats verbatim mid-sheet at two points, each exactly one single-copy
-- length apart. Same underlying anomaly as the DOPA source's known
-- triplicated subdistrict snapshot (confirmed by inspection: both are
-- Dec-2025/YYMM=6812 nationwide subdistrict dumps), just delivered as an
-- inline repeated header here instead of 3 separate <table> tags. This
-- table has no is_duplicate_row flag column (unlike DOPA's), so per
-- bronze's no-dedup principle all 3 copies of real data are loaded as
-- ordinary rows; only the 2 literal header-repeat lines are skipped as
-- non-data.
-- ============================================================================
CREATE TABLE `population_by_tambon_national` (
  `bronze_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`       VARCHAR(255), `source_folder` VARCHAR(255), `source_sheet_name` VARCHAR(100),
  `source_row_number`      INT, `file_hash` VARCHAR(64), `ingestion_batch_id` VARCHAR(100),
  `ingested_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, `source_system` VARCHAR(100),
  `YYMM` VARCHAR(4), `CC-CODE` VARCHAR(10), `CC-DESC` VARCHAR(100), `RCODE-CODE` VARCHAR(10),
  `RCODE-DESC` VARCHAR(150), `CCAATT-CODE` VARCHAR(10), `CCAATT-DESC` VARCHAR(150),
  `CCAATTMM-CODE` VARCHAR(10), `CCAATTMM-DESC` VARCHAR(150),
  `MALE` VARCHAR(20), `FEMALE` VARCHAR(20), `TOTAL` VARCHAR(20), `HOUSE` VARCHAR(20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- elderly_dependency_by_district
-- Source: 04_ผู้สูงอายุ (2 files: FY2566, FY2568)
-- ============================================================================
CREATE TABLE `elderly_dependency_by_district` (
  `bronze_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`       VARCHAR(255), `source_folder` VARCHAR(255), `source_sheet_name` VARCHAR(100),
  `source_row_number`      INT, `file_hash` VARCHAR(64), `ingestion_batch_id` VARCHAR(100),
  `ingested_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, `source_system` VARCHAR(100),
  `ปีงบประมาณ`              VARCHAR(10), `อำเภอ` VARCHAR(100),
  `ผู้สูงอายุติดเตียง` VARCHAR(20), `ผู้สูงอายุติดบ้าน` VARCHAR(20), `ผู้สูงอายุติดสังคม` VARCHAR(20),
  `หน่วย` VARCHAR(50), `ที่มา` VARCHAR(300)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- health_kpi_export
-- Source: 05_ตัวชี้วัดสาธารณสุข (5 files: 1 province-level + 4 district-level
-- sets). file_geo_level: 'province' | 'district'. file_set_number: NULL for
-- the province file, '1'..'4' for the district files (exact indicator/KPI
-- name is NOT present in the source).
-- ============================================================================
CREATE TABLE `health_kpi_export` (
  `bronze_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`       VARCHAR(255), `source_folder` VARCHAR(255), `source_sheet_name` VARCHAR(100),
  `source_row_number`      INT, `file_hash` VARCHAR(64), `ingestion_batch_id` VARCHAR(100),
  `ingested_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, `source_system` VARCHAR(100),
  `file_geo_level`         VARCHAR(20)  COMMENT 'derived from filename, not from file content',
  `file_set_number`        VARCHAR(5)   COMMENT 'derived from filename, not from file content',
  `a_name` VARCHAR(200), `target` VARCHAR(50), `result` VARCHAR(50), `F3` VARCHAR(50),
  `result1` VARCHAR(50), `result2` VARCHAR(50), `result3` VARCHAR(50), `result4` VARCHAR(50),
  `result5` VARCHAR(50), `result6` VARCHAR(50), `result7` VARCHAR(50), `result8` VARCHAR(50),
  `result9` VARCHAR(50), `result10` VARCHAR(50), `result11` VARCHAR(50), `result12` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- community_count_by_district_bkk
-- Source: 06_.../จำนวนชุมชนรายเขต (1 file)
-- ============================================================================
CREATE TABLE `community_count_by_district_bkk` (
  `bronze_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`       VARCHAR(255), `source_folder` VARCHAR(255), `source_sheet_name` VARCHAR(100),
  `source_row_number`      INT, `file_hash` VARCHAR(64), `ingestion_batch_id` VARCHAR(100),
  `ingested_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, `source_system` VARCHAR(100),
  `สำนักงานเขต` VARCHAR(100), `ชุมชนแออัด` VARCHAR(20), `ชุมชนชานเมือง` VARCHAR(20),
  `ชุมชนอาคารสูง` VARCHAR(20), `ชุมชนเมือง` VARCHAR(20), `ชุมชนรูปแบบพิเศษ` VARCHAR(20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- foreign_labor_permit_by_area_bkk
-- Source: 06_.../แรงงานต่างด้าวรายอนุญาต (1 file, title row:
-- 'จำนวนคนต่างด้าว...2568'). Source has a genuine FOUR-row spreadsheet
-- header (title -> permit-type group -> blank -> ชาย/หญิง/รวม), confirmed
-- by inspection. Flattened here into composite column names at landing
-- time (non-lossy); the report title itself is metadata, not a column.
-- ============================================================================
CREATE TABLE `foreign_labor_permit_by_area_bkk` (
  `bronze_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`       VARCHAR(255), `source_folder` VARCHAR(255), `source_sheet_name` VARCHAR(100),
  `source_row_number`      INT, `file_hash` VARCHAR(64), `ingestion_batch_id` VARCHAR(100),
  `ingested_at`            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, `source_system` VARCHAR(100),
  `พื้นที่` VARCHAR(100), `เขตที่ครอบคลุม` VARCHAR(100),
  `ทั่วไป_รวม` VARCHAR(50), `ทั่วไป_ชาย` VARCHAR(50), `ทั่วไป_หญิง` VARCHAR(50),
  `นำเข้าตามMOU_รวม` VARCHAR(50), `นำเข้าตามMOU_ชาย` VARCHAR(50), `นำเข้าตามMOU_หญิง` VARCHAR(50),
  `ส่งเสริมการลงทุน_รวม` VARCHAR(50), `ส่งเสริมการลงทุน_ชาย` VARCHAR(50), `ส่งเสริมการลงทุน_หญิง` VARCHAR(50),
  `ชนกลุ่มน้อย_รวม` VARCHAR(50), `ชนกลุ่มน้อย_ชาย` VARCHAR(50), `ชนกลุ่มน้อย_หญิง` VARCHAR(50),
  `ต่ออายุ_รวม` VARCHAR(50), `ต่ออายุ_ชาย` VARCHAR(50), `ต่ออายุ_หญิง` VARCHAR(50),
  `จดทะเบียนสถานะไม่ถูกกฎหมาย_รวม` VARCHAR(50), `จดทะเบียนสถานะไม่ถูกกฎหมาย_ชาย` VARCHAR(50),
  `จดทะเบียนสถานะไม่ถูกกฎหมาย_หญิง` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- bronze._ingestion_manifest
-- One row per file landed. Use for lineage, auditing, and re-run/backfill tracking.
-- ============================================================================
CREATE TABLE `_ingestion_manifest` (
  `batch_id`            VARCHAR(100), `source_file_name` VARCHAR(255), `source_folder` VARCHAR(255),
  `file_hash`           VARCHAR(64), `file_size_bytes` BIGINT, `sheet_name` VARCHAR(100),
  `row_count`           INT, `column_count` INT, `ingested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `status`              VARCHAR(100), `error_message` TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

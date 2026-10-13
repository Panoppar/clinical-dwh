-- =====================================================================
-- BRONZE LAYER TABLE DESIGN
-- Source: Lat Krabang District Office open-data CSV extracts
-- Layer purpose: raw, lightly-typed landing tables that mirror the
--   source files 1:1. No business logic, no joins, no deduplication.
--   Every column is kept as text/varchar to guarantee the load never
--   fails on a dirty/raw value; typing and cleansing happen in Silver.
--
-- Translated from the provided DDL at
-- share_unprocessed_20261010/Lat_Krabang_district_office_tables_checked/bronze_layer_tables.sql
-- into MySQL 8.0 syntax (same rules as the other sources in this project:
-- TIMESTAMP DEFAULT now() unchanged, CREATE SCHEMA dropped).
--
-- PII EXCLUSION (carried forward from this project's prior build, same
-- file, same reasoning): table 8 (community, 06_ชุมชน) is created per the
-- provided schema but deliberately NOT loaded. Its source file carries a
-- community leader's real name and phone number (columns name_head, tel)
-- -- real PII with no de-identified alternative available. The table
-- exists empty so the schema is complete and documented, but
-- extract_load_lat_krabang.py skips this file entirely; see its docstring.
-- =====================================================================

USE bronze;

DROP TABLE IF EXISTS `edu_vocational_college`;
DROP TABLE IF EXISTS `edu_university`;
DROP TABLE IF EXISTS `edu_school`;
DROP TABLE IF EXISTS `health_hospital`;
DROP TABLE IF EXISTS `religious_site`;
DROP TABLE IF EXISTS `business_establishment`;
DROP TABLE IF EXISTS `safety_risk_point`;
DROP TABLE IF EXISTS `community`;
DROP TABLE IF EXISTS `population_total`;
DROP TABLE IF EXISTS `population_death`;

-- ---------------------------------------------------------------------
-- 1. Education / สถาบันอาชีวศึกษา (vocational colleges)
--    Source: 01_การศึกษา/สถาบันอาชีวศึกษา/รายชื่อวิทยาลัยอาชีวศึกษา_เขตลาดกระบัง.csv
-- ---------------------------------------------------------------------
CREATE TABLE `edu_vocational_college` (
    `id`              VARCHAR(50),
    `ed_id`           VARCHAR(50),
    `d_id`            VARCHAR(50),
    `sb_id`           VARCHAR(50),
    `ed_name`         VARCHAR(500),
    `ad_name`         VARCHAR(1000),
    `remark`          VARCHAR(1000),
    `adddate`         VARCHAR(50),
    `updatedate`      VARCHAR(50),
    `_source_file`    VARCHAR(255) NOT NULL,
    `_batch_id`       VARCHAR(100),
    `_ingested_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 2. Education / มหาวิทยาลัย (universities)
-- ---------------------------------------------------------------------
CREATE TABLE `edu_university` (
    `id`              VARCHAR(50),
    `u_id`            VARCHAR(50),
    `district_id`     VARCHAR(50),
    `sdistrict_id`    VARCHAR(50),
    `n_u_name`        VARCHAR(500),
    `a_name`          VARCHAR(1000),
    `remark`          VARCHAR(1000),
    `adddate`         VARCHAR(50),
    `updatedate`      VARCHAR(50),
    `_source_file`    VARCHAR(255) NOT NULL,
    `_batch_id`       VARCHAR(100),
    `_ingested_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 3. Education / โรงเรียน (schools + enrollment stats)
-- ---------------------------------------------------------------------
CREATE TABLE `edu_school` (
    `id`              VARCHAR(50),
    `s_id`            VARCHAR(50),
    `district_id`     VARCHAR(50),
    `s_district_id`   VARCHAR(50),
    `s_name`          VARCHAR(500),
    `student_num`     VARCHAR(50),
    `classroom_num`   VARCHAR(50),
    `teacher_num`     VARCHAR(50),
    `studentm6_num`   VARCHAR(50),
    `studentp3_num`   VARCHAR(50),
    `remark`          VARCHAR(1000),
    `adddate`         VARCHAR(50),
    `updatedate`      VARCHAR(50),
    `_source_file`    VARCHAR(255) NOT NULL,
    `_batch_id`       VARCHAR(100),
    `_ingested_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 4. Health / โรงพยาบาล (hospitals)
-- ---------------------------------------------------------------------
CREATE TABLE `health_hospital` (
    `id`              VARCHAR(50),
    `h_id`            VARCHAR(50),
    `d_id`            VARCHAR(50),
    `sb_id`           VARCHAR(50),
    `h_name`          VARCHAR(500),
    `address_name`    VARCHAR(1000),
    `remark`          VARCHAR(1000),
    `adddate`         VARCHAR(50),
    `updatedate`      VARCHAR(50),
    `_source_file`    VARCHAR(255) NOT NULL,
    `_batch_id`       VARCHAR(100),
    `_ingested_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 5. Religion / ศาสนสถาน (religious sites)
-- ---------------------------------------------------------------------
CREATE TABLE `religious_site` (
    `id`              VARCHAR(50),
    `rel_id`          VARCHAR(50),
    `district_id`     VARCHAR(50),
    `s_district_id`   VARCHAR(50),
    `n_rel`           VARCHAR(500),
    `a_rel`           VARCHAR(1000),
    `remark`          VARCHAR(1000),
    `adddate`         VARCHAR(50),
    `updatedate`      VARCHAR(50),
    `_source_file`    VARCHAR(255) NOT NULL,
    `_batch_id`       VARCHAR(100),
    `_ingested_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 6. Economy / สถานประกอบการ (business establishments)
-- ---------------------------------------------------------------------
CREATE TABLE `business_establishment` (
    `id`              VARCHAR(50),
    `business_id`     VARCHAR(50),
    `district`        VARCHAR(50),
    `name_b`          VARCHAR(500),
    `type_b`          VARCHAR(50),
    `investment`      VARCHAR(50),
    `address`         VARCHAR(1000),
    `remark`          VARCHAR(1000),
    `adddate`         VARCHAR(50),
    `updatedate`      VARCHAR(50),
    `_source_file`    VARCHAR(255) NOT NULL,
    `_batch_id`       VARCHAR(100),
    `_ingested_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 7. Safety / จุดเสี่ยงภัย (risk points)
-- ---------------------------------------------------------------------
CREATE TABLE `safety_risk_point` (
    `id`              VARCHAR(50),
    `risk_id`         VARCHAR(50),
    `district`        VARCHAR(50),
    `risk_name`       VARCHAR(500),
    `risk_type`       VARCHAR(50),
    `r1`              VARCHAR(10),
    `r2`              VARCHAR(10),
    `r3`              VARCHAR(10),
    `r4`              VARCHAR(10),
    `r5`              VARCHAR(10),
    `r6`              VARCHAR(10),
    `remark`          VARCHAR(1000),
    `adddate`         VARCHAR(50),
    `updatedate`      VARCHAR(50),
    `_source_file`    VARCHAR(255) NOT NULL,
    `_batch_id`       VARCHAR(100),
    `_ingested_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 8. Community / ชุมชน -- created empty, see PII note in header comment.
-- ---------------------------------------------------------------------
CREATE TABLE `community` (
    `l_district`                  VARCHAR(100),
    `community_name`               VARCHAR(500),
    `institute_date`                VARCHAR(50),
    `area_size`                     VARCHAR(50),
    `community_type`                VARCHAR(100),
    `count_house1`                  VARCHAR(50),
    `count_house2`                  VARCHAR(50),
    `count_male`                    VARCHAR(50),
    `count_female`                  VARCHAR(50),
    `total`                          VARCHAR(50),
    `religion`                       VARCHAR(100),
    `name_head`                      VARCHAR(500),
    `count_community_committee`      VARCHAR(50),
    `address`                        VARCHAR(1000),
    `tel`                            VARCHAR(200),
    `_source_file`    VARCHAR(255) NOT NULL,
    `_batch_id`       VARCHAR(100),
    `_ingested_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 9. Population / ประชากรทั้งหมด (population totals by sub-district)
-- ---------------------------------------------------------------------
CREATE TABLE `population_total` (
    `l_district`     VARCHAR(100),
    `l_male`          VARCHAR(50),
    `l_female`        VARCHAR(50),
    `l_total`         VARCHAR(50),
    `_source_file`    VARCHAR(255) NOT NULL,
    `_batch_id`       VARCHAR(100),
    `_ingested_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 10. Population / การเสียชีวิต (deaths by sub-district)
-- ---------------------------------------------------------------------
CREATE TABLE `population_death` (
    `l_district`     VARCHAR(100),
    `l_male`          VARCHAR(50),
    `l_female`        VARCHAR(50),
    `l_total`         VARCHAR(50),
    `_source_file`    VARCHAR(255) NOT NULL,
    `_batch_id`       VARCHAR(100),
    `_ingested_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

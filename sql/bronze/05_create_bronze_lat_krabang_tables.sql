-- ============================================================================
-- Bronze layer DDL — Lat Krabang district office tables (unrestricted —
-- not part of the HDC/DDS usage-rights hold, but one source file in this
-- group (community-level data) carries real PII — a community leader's
-- name and phone number — and is deliberately NOT loaded anywhere in this
-- pipeline, Bronze included. See docs/03_external_reference_sources.md.
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `lat_krabang_population_by_subdistrict`;
CREATE TABLE `lat_krabang_population_by_subdistrict` (
  `subdistrict_name_th` VARCHAR(100), `male` VARCHAR(20), `female` VARCHAR(20), `total` VARCHAR(20),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `lat_krabang_deaths_by_subdistrict`;
CREATE TABLE `lat_krabang_deaths_by_subdistrict` (
  `subdistrict_name_th` VARCHAR(100), `male` VARCHAR(20), `female` VARCHAR(20), `total` VARCHAR(20),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `lat_krabang_universities`;
CREATE TABLE `lat_krabang_universities` (
  `id` VARCHAR(20), `u_id` VARCHAR(20), `district_id` VARCHAR(10), `sdistrict_id` VARCHAR(10),
  `name_th` VARCHAR(200), `address_th` TEXT, `remark` TEXT, `adddate` VARCHAR(20), `updatedate` VARCHAR(20),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `lat_krabang_vocational_colleges`;
CREATE TABLE `lat_krabang_vocational_colleges` (
  `id` VARCHAR(20), `ed_id` VARCHAR(20), `d_id` VARCHAR(10), `sb_id` VARCHAR(10),
  `name_th` VARCHAR(200), `address_th` TEXT, `remark` TEXT, `adddate` VARCHAR(20), `updatedate` VARCHAR(20),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `lat_krabang_schools`;
CREATE TABLE `lat_krabang_schools` (
  `id` VARCHAR(20), `s_id` VARCHAR(20), `district_id` VARCHAR(10), `s_district_id` VARCHAR(10),
  `name_th` VARCHAR(200), `student_num` VARCHAR(20), `classroom_num` VARCHAR(20), `teacher_num` VARCHAR(20),
  `student_m6_num` VARCHAR(20), `student_p3_num` VARCHAR(20), `remark` TEXT,
  `adddate` VARCHAR(20), `updatedate` VARCHAR(20),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `lat_krabang_risk_points`;
CREATE TABLE `lat_krabang_risk_points` (
  `id` VARCHAR(20), `risk_id` VARCHAR(20), `district_th` VARCHAR(100), `risk_name_th` VARCHAR(200),
  `risk_type` VARCHAR(10), `r1` VARCHAR(5), `r2` VARCHAR(5), `r3` VARCHAR(5),
  `r4` VARCHAR(5), `r5` VARCHAR(5), `r6` VARCHAR(5), `remark` TEXT,
  `adddate` VARCHAR(20), `updatedate` VARCHAR(20),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `lat_krabang_religious_sites`;
CREATE TABLE `lat_krabang_religious_sites` (
  `id` VARCHAR(20), `rel_id` VARCHAR(20), `district_id` VARCHAR(10), `s_district_id` VARCHAR(10),
  `name_th` VARCHAR(200), `address_th` TEXT, `remark` TEXT, `adddate` VARCHAR(20), `updatedate` VARCHAR(20),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Business/commercial registry — names and investment amounts. Mostly
-- registered company names, but some rows are sole-proprietorship
-- registrations where Thai business law permits (and this data shows)
-- using the individual owner's personal name as the registered business
-- name — e.g. a row literally named "นายสิทธิธรรม เรืองจรุงพงศ์" (a person's
-- name, not "Company Limited"). That's public business-registration
-- record, not a separate personal-data leak, but it's real individual
-- identification nonetheless; the explicitly excluded factory-owner-name
-- file from the source README is a different, separate file that was
-- never included in this shared folder at all.
DROP TABLE IF EXISTS `lat_krabang_businesses`;
CREATE TABLE `lat_krabang_businesses` (
  `id` VARCHAR(20), `business_id` VARCHAR(20), `district_th` VARCHAR(100),
  `business_name_th` VARCHAR(300), `business_type_code` VARCHAR(20), `investment_thb` VARCHAR(30),
  `address_th` TEXT, `remark` TEXT, `adddate` VARCHAR(20), `updatedate` VARCHAR(20),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `lat_krabang_hospitals`;
CREATE TABLE `lat_krabang_hospitals` (
  `id` VARCHAR(20), `h_id` VARCHAR(20), `d_id` VARCHAR(10), `sb_id` VARCHAR(10),
  `name_th` VARCHAR(200), `address_th` TEXT, `remark` TEXT, `adddate` VARCHAR(20), `updatedate` VARCHAR(20),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

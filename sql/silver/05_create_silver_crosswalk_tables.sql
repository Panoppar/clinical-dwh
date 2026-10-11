-- ============================================================================
-- Silver layer DDL — Thai geography + zip-code admin crosswalk.
--
-- A Thai zip_code does NOT map 1:1 to a district: 167 of 966 distinct zip
-- codes in this reference dataset span more than one district (17%). Rather
-- than fake a clean 1:1 mapping, this is modeled as two tables:
--   * zip_code_admin_crosswalk  — full fidelity, one row per
--     (zip_code, subdistrict_code) pair. Use this when you need every
--     subdistrict a zip code could mean.
--   * zip_code_primary_district — one row per zip_code, resolved to its
--     most-common district (ties broken by lowest district_code), with an
--     `is_ambiguous` flag so downstream consumers know when that resolution
--     is a simplification. Use this for a simple FK join onto
--     Dim_Patient.zip_code.
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `zip_code_primary_district`;
DROP TABLE IF EXISTS `zip_code_admin_crosswalk`;
DROP TABLE IF EXISTS `thai_geography`;

CREATE TABLE `thai_geography` (
  `subdistrict_code` INT NOT NULL,
  `subdistrict_name_th` VARCHAR(100) NULL,
  `subdistrict_name_en` VARCHAR(100) NULL,
  `zip_code` VARCHAR(10) NULL,
  `district_code` INT NOT NULL,
  `district_name_th` VARCHAR(100) NULL,
  `district_name_en` VARCHAR(100) NULL,
  `province_code` INT NOT NULL,
  `province_name_th` VARCHAR(100) NULL,
  `province_name_en` VARCHAR(100) NULL,
  PRIMARY KEY (`subdistrict_code`),
  KEY `ix_tg_zip_code` (`zip_code`),
  KEY `ix_tg_district_code` (`district_code`),
  KEY `ix_tg_province_code` (`province_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `zip_code_admin_crosswalk` (
  `zip_code` VARCHAR(10) NOT NULL,
  `subdistrict_code` INT NOT NULL,
  `subdistrict_name_en` VARCHAR(100) NULL,
  `district_code` INT NOT NULL,
  `district_name_en` VARCHAR(100) NULL,
  `province_code` INT NOT NULL,
  `province_name_en` VARCHAR(100) NULL,
  PRIMARY KEY (`zip_code`, `subdistrict_code`),
  KEY `ix_zac_district_code` (`district_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `zip_code_primary_district` (
  `zip_code` VARCHAR(10) NOT NULL,
  `district_code` INT NOT NULL,
  `district_name_th` VARCHAR(100) NULL,
  `district_name_en` VARCHAR(100) NULL,
  `province_code` INT NOT NULL,
  `province_name_th` VARCHAR(100) NULL,
  `province_name_en` VARCHAR(100) NULL,
  `district_count` INT NOT NULL,
  `is_ambiguous` TINYINT(1) NOT NULL,
  PRIMARY KEY (`zip_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Bronze layer DDL — Thai administrative geography reference data.
-- Source: github.com/kongvut/thai-province-data (MIT license). Used to build
-- the zip-code -> province/district/subdistrict crosswalk. See
-- docs/03_external_reference_sources.md for provenance.
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `thai_geo_subdistrict`;
DROP TABLE IF EXISTS `thai_geo_district`;
DROP TABLE IF EXISTS `thai_geo_province`;

CREATE TABLE `thai_geo_province` (
  `id` VARCHAR(10),
  `name_th` VARCHAR(100),
  `name_en` VARCHAR(100),
  `prefix_th` VARCHAR(20),
  `prefix_en` VARCHAR(20),
  `geography_id` VARCHAR(10),
  `created_at` VARCHAR(40),
  `updated_at` VARCHAR(40),
  `deleted_at` VARCHAR(40),
  `_bronze_loaded_at` TIMESTAMP NULL,
  `_source_system` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `thai_geo_district` (
  `id` VARCHAR(10),
  `name_th` VARCHAR(100),
  `name_en` VARCHAR(100),
  `prefix_th` VARCHAR(20),
  `prefix_en` VARCHAR(20),
  `province_id` VARCHAR(10),
  `created_at` VARCHAR(40),
  `updated_at` VARCHAR(40),
  `deleted_at` VARCHAR(40),
  `_bronze_loaded_at` TIMESTAMP NULL,
  `_source_system` VARCHAR(50),
  KEY `ix_bgd_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `thai_geo_subdistrict` (
  `id` VARCHAR(10),
  `zip_code` VARCHAR(10),
  `name_th` VARCHAR(100),
  `name_en` VARCHAR(100),
  `prefix_th` VARCHAR(20),
  `prefix_en` VARCHAR(20),
  `district_id` VARCHAR(10),
  `lat` VARCHAR(30),
  `long` VARCHAR(30),
  `created_at` VARCHAR(40),
  `updated_at` VARCHAR(40),
  `deleted_at` VARCHAR(40),
  `_bronze_loaded_at` TIMESTAMP NULL,
  `_source_system` VARCHAR(50),
  KEY `ix_bgs_zip_code` (`zip_code`),
  KEY `ix_bgs_district_id` (`district_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Bronze layer DDL — KMCH catchment places (4 files, union schema) and
-- other health/population tables (4 clean CSVs from group 6). Unrestricted.
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `kmch_catchment_places`;
CREATE TABLE `kmch_catchment_places` (
  `category` VARCHAR(50), `place_name_th` VARCHAR(200), `place_name_en` VARCHAR(200),
  `address_th` TEXT, `subdistrict_th` VARCHAR(100), `district_th` VARCHAR(100), `province_th` VARCHAR(100),
  `avg_distance_km` VARCHAR(20), `avg_travel_time_mins` VARCHAR(20), `market_potential` VARCHAR(100),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50), `_source_file` VARCHAR(150)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `other_health_disease_cases`;
CREATE TABLE `other_health_disease_cases` (
  `disease_th` VARCHAR(200), `count_2567` VARCHAR(20), `count_2568` VARCHAR(20), `diff` VARCHAR(20),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `other_health_subdistrict_cases`;
CREATE TABLE `other_health_subdistrict_cases` (
  `district_th` VARCHAR(100), `subdistrict_th` VARCHAR(100),
  `count_2567` VARCHAR(20), `count_2568` VARCHAR(20), `diff` VARCHAR(20),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `other_health_sick_by_group`;
CREATE TABLE `other_health_sick_by_group` (
  `year_be` VARCHAR(10), `province_th` VARCHAR(100), `disease_group_th` VARCHAR(200),
  `sex_th` VARCHAR(20), `count` VARCHAR(20),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `other_health_disease_by_year`;
CREATE TABLE `other_health_disease_by_year` (
  `year_be` VARCHAR(10), `disease_th` VARCHAR(200), `count` VARCHAR(20),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Silver layer DDL — Thai geography name lookup.
--
-- The zip-code crosswalk tables that used to live here
-- (zip_code_admin_crosswalk, zip_code_primary_district) were removed along
-- with the clinic/patient pipeline they existed solely to serve -- nothing
-- in the surviving warehouse carries a zip_code field. `thai_geography`
-- itself stays: several Gold loads (population reference, HDC, DDS) join
-- against it purely to resolve English province/district names.
-- ============================================================================

USE silver;

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

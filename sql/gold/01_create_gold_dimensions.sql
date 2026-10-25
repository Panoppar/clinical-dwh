-- ============================================================================
-- GOLD LAYER — dimensions, built from the 5 live-API Silver sources
-- Designed from the KPI tree + dashboard design in
-- C:\Users\PunPun\Desktop\Workspace\KMITL\Excel\KPI_Tree_and_Dashboard_Design.xlsx
-- (tabs KPI_Tree / Dashboard_Design).
--
-- dim_geography: unlike the previous (removed) DOPA-based dimension, this
-- is built purely from the 5 sources' OWN text labels -- NSO/BMA/DIW all
-- use plain geographic names (province/amphoe-district/tambon-subdistrict),
-- confirmed by direct inspection that BMA's `district` and DIW's `amphoe`
-- match character-for-character for every Bangkok area checked (e.g.
-- "คลองเตย", "จตุจักร"). No DOPA local-government-unit naming is involved
-- this time, so the earlier Bronze-stage name-mismatch problem does not
-- apply here.
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `dim_date`;
DROP TABLE IF EXISTS `dim_geography`;
DROP TABLE IF EXISTS `dim_industry`;
DROP TABLE IF EXISTS `dim_hdc_report`;
DROP TABLE IF EXISTS `dim_disease`;

CREATE TABLE `dim_date` (
    `date_key`   INT UNSIGNED PRIMARY KEY COMMENT 'year_ce, e.g. 2025',
    `year_ce`    SMALLINT NOT NULL,
    `year_be`    SMALLINT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `dim_geography` (
    `geo_key`           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `admin_level`       VARCHAR(12)  NOT NULL COMMENT 'province | district | subdistrict',
    `province_name`     VARCHAR(150) NOT NULL,
    `district_name`     VARCHAR(150) COMMENT 'NULL at province level',
    `subdistrict_name`  VARCHAR(150) COMMENT 'NULL above subdistrict level',
    `parent_geo_key`    INT UNSIGNED NULL,
    `source_systems`    VARCHAR(100) NOT NULL COMMENT 'which of NSO/BMA/DIW contributed this row, comma-separated',
    KEY `ix_dg_level` (`admin_level`),
    KEY `ix_dg_province` (`province_name`),
    KEY `ix_dg_district` (`province_name`, `district_name`),
    KEY `ix_dg_parent` (`parent_geo_key`),
    CONSTRAINT `fk_dg_parent` FOREIGN KEY (`parent_geo_key`) REFERENCES `dim_geography` (`geo_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `dim_industry` (
    `industry_key`       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `tsic_code`           VARCHAR(20),
    `factory_type_code`    VARCHAR(20),
    UNIQUE KEY `ux_di_codes` (`tsic_code`, `factory_type_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- From bronze.api_hdc_report_catalog -- reference data, not a Silver fact,
-- promoted straight to Gold since Silver's HDC tables already resolve
-- report_name via this same catalog (see transform_silver_api_hdc.py).
CREATE TABLE `dim_hdc_report` (
    `report_key`          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `report_code`          VARCHAR(100) NOT NULL,
    `report_name`           VARCHAR(500),
    `subcatalog_name`        VARCHAR(255),
    `years_available`         VARCHAR(255) COMMENT 'comma-separated BE years, from byear_list',
    UNIQUE KEY `ux_dhr_code` (`report_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- From silver.api_dds_disease_ranking (0 rows as of this build -- DDS's
-- backend has been down since 2026-10-25). Structurally ready; populates
-- once that source recovers.
CREATE TABLE `dim_disease` (
    `disease_key`   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `disease_name`   VARCHAR(500) NOT NULL,
    UNIQUE KEY `ux_dd_name` (`disease_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

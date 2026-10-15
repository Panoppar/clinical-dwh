-- ============================================================================
-- GOLD LAYER — dim_geography
--
-- Built by pipeline/transform_gold_dim_geography.py from DOPA's real
-- government admin codes (the authoritative, complete hierarchy),
-- extended with any new codes from population_by_tambon_national and
-- the one source with no codes at all (elderly_dependency_by_district,
-- matched by exact name -- confirmed identical strings against DOPA's
-- district names for Samut Prakan).
--
-- Geography names are NOT consistent across sources at the raw-text level
-- (DOPA: "จังหวัดสมุทรปราการ " with prefix+trailing space; other sources:
-- "สมุทรปราการ" bare) -- this table is the one normalized, canonical
-- geography list; every Gold fact joins to it by code, not by raw text.
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `dim_geography`;

CREATE TABLE `dim_geography` (
    `geo_key`              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `admin_level`            VARCHAR(12)  NOT NULL COMMENT 'country | province | district | subdistrict',
    `province_code`           VARCHAR(10),
    `province_name_th`         VARCHAR(150),
    `district_code`             VARCHAR(15),
    `district_name_th`           VARCHAR(150),
    `subdistrict_code`             VARCHAR(15),
    `subdistrict_name_th`            VARCHAR(150),
    `parent_geo_key`                  INT UNSIGNED NULL,
    `source_system`                    VARCHAR(50)  NOT NULL,
    KEY `ix_dg_admin_level` (`admin_level`),
    KEY `ix_dg_province_code` (`province_code`),
    KEY `ix_dg_district_code` (`province_code`, `district_code`),
    KEY `ix_dg_subdistrict_code` (`province_code`, `district_code`, `subdistrict_code`),
    KEY `ix_dg_parent` (`parent_geo_key`),
    CONSTRAINT `fk_dg_parent` FOREIGN KEY (`parent_geo_key`) REFERENCES `dim_geography` (`geo_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

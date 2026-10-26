-- ============================================================================
-- GOLD LAYER — dim_area (catchment-area dimension)
-- New file, does not touch dim_date/dim_geography/dim_industry/
-- dim_hdc_report/dim_disease in sql/gold/01 -- those stay exactly as-is.
--
-- Built from silver.geo_boundary_{subdistrict,district}
-- (kmch-ml input-parity gap 1). Grain: one row per catchment "unit" --
-- normally a subdistrict, but Bangkok's 13 post-2019 khwaeng splits (no
-- polygon/centroid in this snapshot) fall back to their parent district
-- as a single coarser unit, same handling kmch-ml's own dim_area uses
-- (confirmed: 13 splits -> 7 parent districts). is_district_level_fallback
-- marks which rows took that path, rather than hiding it.
--
-- Scope: the 3 catchment provinces only (10=Bangkok, 11=Samut Prakan,
-- 24=Chachoengsao), matching kmch-ml's own scope and every other source
-- in this project. NOT built nationwide.
--
-- catchment_tier/dist_to_kmch_km are geographic classification (distance
-- bucketing from a fixed hospital coordinate), matching kmch-ml's own
-- input-dimension schema -- NOT the accessibility *scoring* models (Huff
-- share, E2SFCA) that stay explicitly out of scope for this project.
-- ============================================================================

USE gold;

-- fact_hospital_access (sql/gold/06, created later in GOLD_SCRIPTS order)
-- has a FK into this table -- on a re-run, that table still exists from
-- the previous run and blocks a plain DROP TABLE without this guard
-- (confirmed live: "ERROR 3730 ... referenced by a foreign key
-- constraint 'fk_fha_area'"). Same pattern sql/gold/01 already uses for
-- dim_geography's self-reference.
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `dim_area`;

CREATE TABLE `dim_area` (
    `area_key`                      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `unit_code`                     VARCHAR(20)  NOT NULL COMMENT 'TIS-1099 subdistrict code, or parent district code for is_district_level_fallback=1 rows',
    `unit_th`                       VARCHAR(255) NOT NULL,
    `is_district_level_fallback`    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '1 when unit_code is a district (not subdistrict) due to missing subdistrict-level centroid data',
    `province_code`                 VARCHAR(20)  NOT NULL,
    `province_th`                   VARCHAR(150) NOT NULL,
    `amphoe_code`                   VARCHAR(20)  NOT NULL,
    `amphoe_th`                     VARCHAR(150) NOT NULL,
    `centroid_lat`                  DECIMAL(10,6) NOT NULL,
    `centroid_lon`                  DECIMAL(10,6) NOT NULL,
    `dist_to_kmch_km`               DECIMAL(10,3) NOT NULL COMMENT 'Haversine straight-line distance from centroid to the fixed KMCH coordinate -- see transform_gold_dimensions.py for the exact constant',
    `catchment_tier`                VARCHAR(20)  NOT NULL COMMENT 'core (<=10km) | primary (<=20km) | extended (<=30km) | bkk_other (>30km, Bangkok) | province_other (>30km, Samut Prakan/Chachoengsao)',
    `is_catchment`                  TINYINT(1)   NOT NULL COMMENT '1 for core/primary/extended',
    UNIQUE KEY `ux_da_unit_code` (`unit_code`),
    KEY `ix_da_province` (`province_code`),
    KEY `ix_da_tier` (`catchment_tier`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

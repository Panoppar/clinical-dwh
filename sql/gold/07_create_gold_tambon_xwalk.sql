-- ============================================================================
-- GOLD LAYER — dim_tambon_unit_xwalk (kmch-ml input-parity gap 4/6)
-- New file, does not touch any table in sql/gold/01-06 -- those stay
-- exactly as-is.
--
-- Grain: one row per original TIS-1099 tambon code (finer than dim_area's
-- 312 merged units -- the 13 Bangkok post-2019 khwaeng-split tambons each
-- get their own row here, pointing at their shared merged unit_code).
--
-- adm3_pcode is the exact key the nationwide ADM3 polygon geojson uses
-- (gap 6 -- see docs/06_kmch_ml_gap_closure_plan.md) so kmch-ml or anyone
-- else can join that geometry straight to dim_area via this table, without
-- needing to know the 'TH' prefix convention.
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `dim_tambon_unit_xwalk`;

CREATE TABLE `dim_tambon_unit_xwalk` (
    `xwalk_key`      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `tambon_code`    VARCHAR(20)  NOT NULL COMMENT 'original TIS-1099 subdistrict code, pre-2019-split',
    `tambon_th`      VARCHAR(255) NOT NULL,
    `tambon_en`      VARCHAR(255),
    `amphoe_code`    VARCHAR(20)  NOT NULL,
    `amphoe_th`      VARCHAR(150) NOT NULL,
    `postal_code`    VARCHAR(10),
    `adm3_pcode`     VARCHAR(20)  NOT NULL COMMENT "= 'TH' || tambon_code -- the exact key thailand-adm3-polygons-v1.0.0.geojson uses",
    `unit_code`      VARCHAR(20)  NOT NULL COMMENT 'FK to dim_area.unit_code -- the merged catchment unit this tambon belongs to',
    `is_split`       TINYINT(1)   NOT NULL COMMENT '1 for a post-2019 khwaeng split sibling (tambon_code != unit_code)',
    UNIQUE KEY `ux_dtux_tambon` (`tambon_code`),
    KEY `ix_dtux_unit` (`unit_code`),
    CONSTRAINT `fk_dtux_unit` FOREIGN KEY (`unit_code`) REFERENCES `dim_area` (`unit_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

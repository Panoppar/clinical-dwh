-- ============================================================================
-- GOLD LAYER — dim_industry_division (kmch-ml input-parity gap 3)
-- New file, does not touch any table in sql/gold/01-08 -- those stay
-- exactly as-is.
--
-- TSIC 2009's 2-digit division code -> English name. A fixed, small,
-- static reference list -- seeded directly here (not ingested from any
-- live or file source), scoped to only the 34 divisions actually observed
-- across the DIW factory registry's 3 catchment provinces (not the full
-- national TSIC 2009 division list, which is longer and includes
-- divisions with zero factories here).
--
-- dim_industry.tsic_code's first 2 characters map to this table's
-- division_code -- but only for tsic_code values that are exactly 5
-- characters (proper TSIC 2009 codes). dim_industry also carries 3- and
-- 4-digit legacy/short codes (DIW's own "old or short code" factories,
-- confirmed live) which this table does not attempt to classify --
-- matching kmch-ml's own methodology of restricting location-quotient
-- analysis to TSIC-2009-5-digit-coded factories only.
-- ============================================================================

USE gold;

-- agg_industrial_concentration_by_unit(_division) (sql/gold/10, created
-- later in GOLD_SCRIPTS order) has an FK into this table -- on a re-run,
-- that table still exists from the previous run and blocks a plain DROP
-- TABLE without this guard. Same pattern sql/gold/04 uses for dim_area.
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `dim_industry_division`;

CREATE TABLE `dim_industry_division` (
    `division_code`      CHAR(2)      NOT NULL PRIMARY KEY,
    `division_name_en`    VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `dim_industry_division` (`division_code`, `division_name_en`) VALUES
('01', 'Crop and animal production'),
('02', 'Forestry and logging'),
('08', 'Other mining and quarrying'),
('10', 'Manufacture of food products'),
('11', 'Manufacture of beverages'),
('12', 'Manufacture of tobacco products'),
('13', 'Manufacture of textiles'),
('14', 'Manufacture of wearing apparel'),
('15', 'Manufacture of leather and related products'),
('16', 'Manufacture of wood and products of wood and cork'),
('17', 'Manufacture of paper and paper products'),
('18', 'Printing and reproduction of recorded media'),
('19', 'Manufacture of coke and refined petroleum products'),
('20', 'Manufacture of chemicals and chemical products'),
('21', 'Manufacture of pharmaceuticals'),
('22', 'Manufacture of rubber and plastics products'),
('23', 'Manufacture of other non-metallic mineral products'),
('24', 'Manufacture of basic metals'),
('25', 'Manufacture of fabricated metal products, except machinery'),
('26', 'Manufacture of computer, electronic and optical products'),
('27', 'Manufacture of electrical equipment'),
('28', 'Manufacture of machinery and equipment n.e.c.'),
('29', 'Manufacture of motor vehicles, trailers and semi-trailers'),
('30', 'Manufacture of other transport equipment'),
('31', 'Manufacture of furniture'),
('32', 'Other manufacturing'),
('33', 'Repair and installation of machinery and equipment'),
('35', 'Electricity, gas, steam and air conditioning supply'),
('36', 'Water collection, treatment and supply'),
('37', 'Sewerage'),
('38', 'Waste collection, treatment and disposal; materials recovery'),
('39', 'Remediation activities and other waste management services'),
('46', 'Wholesale trade'),
('52', 'Warehousing and support activities for transportation');

SET FOREIGN_KEY_CHECKS = 1;

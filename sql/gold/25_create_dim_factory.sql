-- ============================================================================
-- GOLD LAYER — dim_factory
-- factory_list has multiple registration records per factory_reg_no
-- (5,976 distinct factories across 11,862 rows, confirmed by inspection)
-- -- descriptive attributes here use the LATEST record per factory
-- (highest permit_year_ce, then silver_id as tiebreak), same
-- latest-wins convention as dim_geography's canonical-name pick.
-- All factory_list rows are province_code='10' (Bangkok-scoped source).
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `dim_factory`;

CREATE TABLE `dim_factory` (
    `factory_key`      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `factory_reg_no`     VARCHAR(50)  NOT NULL,
    `factory_name`         VARCHAR(500),
    `owner_name`             VARCHAR(500),
    `tsic_code`                VARCHAR(20),
    `category`                   VARCHAR(50),
    `class`                         TINYINT,
    `factory_type_desc`               TEXT,
    `business_activity`                 TEXT,
    UNIQUE KEY `ux_df_reg_no` (`factory_reg_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `dim_factory` (factory_reg_no, factory_name, owner_name, tsic_code, category, class, factory_type_desc, business_activity)
SELECT s.factory_reg_no, s.factory_name, s.owner_name, s.tsic_code, s.category, s.class, s.factory_type_desc, s.business_activity
FROM silver.factory_list s
JOIN (
    SELECT factory_reg_no, MAX(CONCAT(LPAD(IFNULL(permit_year_ce, 0), 6, '0'), LPAD(silver_id, 12, '0'))) AS pick
    FROM silver.factory_list
    GROUP BY factory_reg_no
) latest ON latest.factory_reg_no = s.factory_reg_no
    AND latest.pick = CONCAT(LPAD(IFNULL(s.permit_year_ce, 0), 6, '0'), LPAD(s.silver_id, 12, '0'));

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- GOLD LAYER — obt_population_by_geography
-- One row per (geography, month), fully denormalized -- what Metabase
-- actually queries, zero joins, zero runtime math.
--
-- Growth rates are computed via an explicit self-join on the exact prior
-- period's date_key, not a sequential window function (LAG()) -- this
-- source's real cadence is mostly one December snapshot per year, so a
-- naive LAG() "previous row in the partition" would silently compare
-- across a multi-year gap and mislabel it "MoM". The self-join correctly
-- returns NULL when no exact prior period exists, which is the honest
-- answer for sparse, irregular snapshots.
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `obt_population_by_geography`;

CREATE TABLE `obt_population_by_geography` (
    `obt_key`              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `geo_key`                INT UNSIGNED NOT NULL,
    `date_key`                 INT          NOT NULL,
    `admin_level`                VARCHAR(12)  NOT NULL,
    `province_name_th`             VARCHAR(150),
    `district_name_th`               VARCHAR(150),
    `subdistrict_name_th`              VARCHAR(150),
    `year_ce`                            SMALLINT     NOT NULL,
    `month`                                TINYINT      NOT NULL,
    `month_name`                             VARCHAR(20)  NOT NULL,
    `total_count`                              BIGINT,
    `male_count`                                 BIGINT,
    `female_count`                                BIGINT,
    `household_count`                               BIGINT,
    `pop_growth_mom_pct`                              DECIMAL(10,4),
    `pop_growth_yoy_pct`                                DECIMAL(10,4),
    `persons_per_household`                              DECIMAL(10,4),
    `sex_ratio`                                            DECIMAL(10,4) COMMENT 'males per 100 females',
    KEY `ix_opbg_geo_date` (`geo_key`, `date_key`),
    KEY `ix_opbg_year_month` (`year_ce`, `month`),
    KEY `ix_opbg_admin_level` (`admin_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

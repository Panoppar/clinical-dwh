-- ============================================================================
-- GOLD LAYER — agg_economic_summary_yearly
-- Grain: geo_key x year. Only fact_factory_registration has a real time
-- dimension (permit year) -- fact_catchment_place's local-area sources
-- are point-in-time snapshots with no year to aggregate by, so this
-- table is factory-only, unlike obt_economic_by_geography which covers
-- both.
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `agg_economic_summary_yearly`;

CREATE TABLE `agg_economic_summary_yearly` (
    `agg_key`                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `geo_key`                  INT UNSIGNED NULL,
    `year_ce`                    SMALLINT     NOT NULL,
    `factory_count`                INT NOT NULL,
    `total_investment_sum`           DECIMAL(24,2) NULL,
    `total_workers_sum`                 BIGINT NULL,
    `investment_per_worker`               DECIMAL(20,2) NULL,
    `yoy_investment_growth_pct`             DECIMAL(10,4) NULL,
    UNIQUE KEY `ux_aesy_geo_year` (`geo_key`, `year_ce`),
    KEY `ix_aesy_year` (`year_ce`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

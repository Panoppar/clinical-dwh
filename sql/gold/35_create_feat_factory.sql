-- ============================================================================
-- GOLD LAYER — feat_factory
-- Feature store pattern, entity grain: one row per factory (the
-- entity-level pattern example, as opposed to feat_geography_month's
-- geography x time grain) -- a flat vector ready for
-- clustering/segmentation. No FK constraints, same "standalone,
-- ML-readable without joining back into the warehouse" intent as
-- feat_geography_month.
--
-- Measures use each factory's LATEST registration record (same
-- latest-wins convention as dim_factory itself, by MAX date_key per
-- factory_key) rather than summing/averaging across registration years
-- -- this is a current-state snapshot feature vector, not a time series.
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `feat_factory`;

CREATE TABLE `feat_factory` (
    `feat_key`              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `factory_reg_no`          VARCHAR(50)  NOT NULL,
    `province_name_th`          VARCHAR(150),
    `tsic_code`                   VARCHAR(20),
    `permit_year_ce`                SMALLINT,
    `total_investment`                DECIMAL(20,2),
    `total_workers`                     INT,
    `male_workers`                        INT,
    `female_workers`                       INT,
    `total_horsepower`                       DECIMAL(20,2),
    `investment_per_worker`                    DECIMAL(20,2),
    `workforce_female_pct`                       DECIMAL(10,4),
    KEY `ix_ff_reg_no` (`factory_reg_no`),
    KEY `ix_ff_tsic` (`tsic_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

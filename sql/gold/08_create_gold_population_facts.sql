-- ============================================================================
-- GOLD LAYER — fact_population_by_area (kmch-ml input-parity gap 1, the
-- previously-deferred "DOPA population" gap, now built from files supplied
-- directly -- see docs/06_kmch_ml_gap_closure_plan.md).
-- New file, does not touch any table in sql/gold/01-07 -- those stay
-- exactly as-is.
--
-- Grain: one row per (unit, year). FK to dim_area (not dim_geography --
-- this data is already at dim_area's merged-unit grain, confirmed: all
-- 312 unit_codes present, none of the 13 post-2019 khwaeng-split codes).
-- data_source flags whether a row has the full age-sex breakdown ('full')
-- or pop_total only ('total_only', the 2560-2564 Samut Prakan/
-- Chachoengsao backfill -- see sql/silver/21's header note).
-- ============================================================================

USE gold;

-- Same FK-guard pattern as every other table with an FK into dim_area
-- (sql/gold/04, 06, 07) -- a plain DROP TABLE fails on a re-run otherwise.
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `fact_population_by_area`;

CREATE TABLE `fact_population_by_area` (
    `fact_id`          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `area_key`          INT UNSIGNED NOT NULL,
    `date_key`           INT UNSIGNED NOT NULL,
    `data_source`         VARCHAR(20) NOT NULL COMMENT 'full | total_only',

    `fine_male_0_4`        INT,
    `fine_female_0_4`        INT,
    `fine_male_5_9`            INT,
    `fine_female_5_9`            INT,
    `fine_male_10_14`              INT,
    `fine_female_10_14`              INT,
    `fine_male_15_17`                  INT,
    `fine_female_15_17`                  INT,
    `fine_male_18_22`                      INT,
    `fine_female_18_22`                      INT,
    `fine_male_23_29`                          INT,
    `fine_female_23_29`                          INT,
    `fine_male_30_39`                              INT,
    `fine_female_30_39`                              INT,
    `fine_male_40_49`                                  INT,
    `fine_female_40_49`                                  INT,
    `fine_male_50_59`                                      INT,
    `fine_female_50_59`                                      INT,
    `fine_male_60_plus`                                          INT,
    `fine_female_60_plus`                                          INT,
    `coarse_male_0_14`     INT,
    `coarse_female_0_14`     INT,
    `coarse_male_15_59`        INT,
    `coarse_female_15_59`        INT,
    `coarse_male_60_plus`          INT,
    `coarse_female_60_plus`          INT,

    `pop_male`         INT,
    `pop_female`         INT,
    `pop_total`            INT NOT NULL,
    `pop_age_known`          INT,
    `pop_unknown_age`          INT,

    UNIQUE KEY `ux_fpa_area_date` (`area_key`, `date_key`),
    KEY `ix_fpa_date` (`date_key`),
    CONSTRAINT `fk_fpa_area` FOREIGN KEY (`area_key`) REFERENCES `dim_area` (`area_key`),
    CONSTRAINT `fk_fpa_date` FOREIGN KEY (`date_key`) REFERENCES `dim_date` (`date_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

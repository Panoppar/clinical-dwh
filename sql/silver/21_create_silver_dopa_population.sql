-- ============================================================================
-- SILVER LAYER — dopa_population_by_unit_year (kmch-ml input-parity gap 1)
-- Merges bronze.dopa_population_year + bronze.dopa_population_supplement
-- into one typed table, grain (unit_code, year_ce). Confirmed zero
-- overlapping (unit_code, year_be) pairs between the two Bronze tables
-- before this was built -- a clean UNION, not a dedup/reconciliation.
--
-- data_source distinguishes which Bronze table a row came from:
--   'full'       -- bronze.dopa_population_year: fine/coarse age-sex bands + totals
--   'total_only' -- bronze.dopa_population_supplement: pop_total only
--                   (backfills the 5 years 2560-2564 missing from the main
--                   file for Samut Prakan/Chachoengsao units specifically)
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `dopa_population_by_unit_year`;

CREATE TABLE `dopa_population_by_unit_year` (
  `silver_id`               BIGINT       AUTO_INCREMENT PRIMARY KEY,
  `unit_code`                VARCHAR(20) NOT NULL COMMENT 'FK target: gold.dim_area.unit_code',
  `year_be`                   SMALLINT   NOT NULL,
  `year_ce`                    SMALLINT  NOT NULL,
  `ref_month`                   TINYINT  COMMENT 'NULL for total_only rows -- the supplement file does not carry this',
  `data_source`                  VARCHAR(20) NOT NULL COMMENT 'full | total_only',

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
  `pop_total`            INT NOT NULL COMMENT 'always present, from either source',
  `pop_age_known`          INT,
  `pop_unknown_age`          INT,
  `source_note`                VARCHAR(255) COMMENT 'source_file for full rows, the supplement''s own source label for total_only rows',

  UNIQUE KEY `ux_dpby_unit_year` (`unit_code`, `year_ce`),
  KEY `ix_dpby_year` (`year_ce`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

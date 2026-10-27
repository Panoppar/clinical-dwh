-- ============================================================================
-- BRONZE LAYER — DOPA population by area/year (kmch-ml input-parity gap 1,
-- "gap 4" in the original planning doc -- previously deferred pending
-- project-owner sign-off, now built from files supplied directly).
--
-- File-based, not a live API (a deliberate, scoped exception -- same
-- pattern as bronze.tambon_xwalk, see docs/06_kmch_ml_gap_closure_plan.md).
-- Landed via pipeline/ingest_file_dopa_population.py.
--
-- Two source files, two tables -- 1:1 fidelity, no transformation:
--   dopa_population_year: dim_population_year.csv (fine 5-yr age-sex bands
--     + coarse bands + totals, 9 years 2560-2568, all 312 dim_area units)
--   dopa_population_supplement: pop_total_supplement_2560_2564.csv
--     (pop_total only, 5 years 2560-2564, Samut Prakan/Chachoengsao only --
--     backfills a real gap: those 143 units are missing exactly those 5
--     years from the main file. Confirmed zero overlapping (unit_code,
--     year_be) pairs between the two files before building this -- they
--     are a clean union, not a conflict to reconcile.)
--
-- unit_code here is already at gold.dim_area's merged-unit grain (confirmed:
-- 312 distinct unit_codes in dim_population_year.csv, exactly matching
-- dim_area, with none of the 13 post-2019 khwaeng-split codes present) --
-- kmch-ml pre-aggregated this export to their own dim_area scheme already.
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `dopa_population_year`;
DROP TABLE IF EXISTS `dopa_population_supplement`;

CREATE TABLE `dopa_population_year` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'DOPA_POPULATION',

  `raw_unit_code`              VARCHAR(20),
  `raw_year_be`                 VARCHAR(10),
  `raw_ref_month`                VARCHAR(10),
  `raw_fine_male_0_4`             VARCHAR(20),
  `raw_fine_female_0_4`            VARCHAR(20),
  `raw_fine_male_5_9`               VARCHAR(20),
  `raw_fine_female_5_9`              VARCHAR(20),
  `raw_fine_male_10_14`               VARCHAR(20),
  `raw_fine_female_10_14`               VARCHAR(20),
  `raw_fine_male_15_17`                  VARCHAR(20),
  `raw_fine_female_15_17`                  VARCHAR(20),
  `raw_fine_male_18_22`                     VARCHAR(20),
  `raw_fine_female_18_22`                     VARCHAR(20),
  `raw_fine_male_23_29`                        VARCHAR(20),
  `raw_fine_female_23_29`                        VARCHAR(20),
  `raw_fine_male_30_39`                           VARCHAR(20),
  `raw_fine_female_30_39`                           VARCHAR(20),
  `raw_fine_male_40_49`                              VARCHAR(20),
  `raw_fine_female_40_49`                              VARCHAR(20),
  `raw_fine_male_50_59`                                 VARCHAR(20),
  `raw_fine_female_50_59`                                 VARCHAR(20),
  `raw_fine_male_60_plus`                                   VARCHAR(20),
  `raw_fine_female_60_plus`                                   VARCHAR(20),
  `raw_coarse_male_0_14`           VARCHAR(20),
  `raw_coarse_female_0_14`          VARCHAR(20),
  `raw_coarse_male_15_59`            VARCHAR(20),
  `raw_coarse_female_15_59`           VARCHAR(20),
  `raw_coarse_male_60_plus`            VARCHAR(20),
  `raw_coarse_female_60_plus`           VARCHAR(20),
  `raw_pop_male`             VARCHAR(20),
  `raw_pop_female`            VARCHAR(20),
  `raw_pop_total`              VARCHAR(20),
  `raw_pop_age_known`           VARCHAR(20),
  `raw_pop_unknown_age`          VARCHAR(20),
  `raw_source_file`               VARCHAR(255),

  KEY `ix_dpy_unit_year` (`raw_unit_code`, `raw_year_be`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `dopa_population_supplement` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'DOPA_POPULATION',

  `raw_unit_code`    VARCHAR(20),
  `raw_year_be`       VARCHAR(10),
  `raw_pop_total`      VARCHAR(20),
  `raw_source`          VARCHAR(100) COMMENT 'e.g. "DOPA stat_t60 (ธ.ค.)" -- which DOPA snapshot file this row came from',

  KEY `ix_dps_unit_year` (`raw_unit_code`, `raw_year_be`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

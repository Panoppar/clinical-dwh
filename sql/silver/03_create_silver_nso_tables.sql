-- ============================================================================
-- SILVER LAYER — NSO population registration & labor force survey
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `pop_indicator_lookup`;
DROP TABLE IF EXISTS `population_reference_age_sex`;
DROP TABLE IF EXISTS `labor_force_survey`;

-- Generic decode of every SDMX codelist in the structure metadata XML
-- (CL_POP_IND, CL_AGE, CL_SEX, CL_CWT, CL_AMPHOE, CL_TAMBON, CL_FREQ,
-- CL_UNIT, CL_POP_SUBJ) -- parsed from this dataflow's own metadata at
-- load time, not hardcoded from a prior project's memorized indicator
-- table (that was a different dataflow version; codes/meanings aren't
-- guaranteed stable across SDMX dataflow versions).
CREATE TABLE `pop_indicator_lookup` (
    `codelist_id`   VARCHAR(30)  NOT NULL COMMENT 'e.g. CL_POP_IND, CL_AGE, CL_SEX',
    `code`          VARCHAR(30)  NOT NULL COMMENT 'e.g. DEM_IND24, Y_LE1, M',
    `name_en`       VARCHAR(500),
    `name_th`       VARCHAR(500),
    PRIMARY KEY (`codelist_id`, `code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- UNION of pop_reg_national + pop_reg_province, decoded and typed.
-- is_headline_total: DEM_IND24 ("Population from registration") is the
-- one true national/province total in both source tables -- confirmed by
-- inspection (national carries DEM_IND24/48/50/109/49/95; province carries
-- only DEM_IND24/109 -- the set of components differs by level, so the
-- flag is keyed on the indicator code itself, not an assumed fixed set of
-- siblings). Always add `WHERE is_headline_total = 1` before summing
-- population across age/sex groups -- this project shipped a dashboard
-- with exactly this 2x bug once already (see docs/03, 2026-10 incident).
CREATE TABLE `population_reference_age_sex` (
    `silver_id`         BIGINT AUTO_INCREMENT PRIMARY KEY,
    `source_level`      VARCHAR(20)  NOT NULL COMMENT 'national | province',
    `pop_ind`           VARCHAR(20)  NOT NULL,
    `indicator_name_en` VARCHAR(500),
    `is_headline_total` TINYINT(1)   NOT NULL DEFAULT 0,
    `sex`               VARCHAR(10)  NOT NULL COMMENT 'M | F | _T',
    `age_code`          VARCHAR(20)  NOT NULL,
    `age_exact`         SMALLINT     COMMENT 'NULL when the age code is a bucket (le/ge/gt/lt/total) or non-numeric (LUNAR)',
    `age_qualifier`      VARCHAR(10) NOT NULL COMMENT 'exact | total | le | ge | gt | lt | other',
    `province_code`      VARCHAR(10),
    `province_name_en`   VARCHAR(100),
    `year_ce`             SMALLINT    NOT NULL,
    `obs_value`           BIGINT,
    KEY `ix_pras_indicator` (`pop_ind`),
    KEY `ix_pras_headline` (`is_headline_total`),
    KEY `ix_pras_province_year` (`province_code`, `year_ce`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- from pop_sur_survey. Kept close to source shape (SDMX-CSV's own
-- bilingual code+label pairing already serves as the lookup).
CREATE TABLE `labor_force_survey` (
    `silver_id`         BIGINT AUTO_INCREMENT PRIMARY KEY,
    `stat_list`          VARCHAR(50),
    `indicator_label_th` VARCHAR(500),
    `level_of_edu`        VARCHAR(30),
    `level_of_edu_th`     VARCHAR(300),
    `sex`                  VARCHAR(10),
    `sex_th`               VARCHAR(50),
    `age_gp`                VARCHAR(30),
    `age_gp_th`             VARCHAR(100),
    `area`                   VARCHAR(20),
    `area_th`                VARCHAR(200),
    `province_code`           VARCHAR(20),
    `province_th`             VARCHAR(200),
    `municipal`                VARCHAR(20),
    `municipal_th`              VARCHAR(200),
    `unit`                       VARCHAR(20),
    `unit_th`                    VARCHAR(100),
    `unit_mul`                    TINYINT,
    `freq`                         VARCHAR(10),
    `time_period`                   VARCHAR(20),
    `year_ce`                        SMALLINT,
    `quarter`                         TINYINT COMMENT 'NULL for annual observations',
    `obs_value`                       DECIMAL(20,2),
    `note`                             VARCHAR(1000),
    KEY `ix_lfs_province_year` (`province_code`, `year_ce`),
    KEY `ix_lfs_stat` (`stat_list`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

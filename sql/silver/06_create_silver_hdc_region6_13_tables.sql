-- ============================================================================
-- SILVER LAYER — HDC_region6_13_by_age_api, collapsed from 19 bronze tables
-- into 4 by shape family, with a `disease` column distinguishing them
-- (mirrors how this project's pre-restart HDC source already did this:
-- one unified table with a disease lineage column instead of one table
-- per disease). This is the SAME bronze source split by the original
-- export tool, not a cross-source merge.
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `hdc_incidence_monthly`;
DROP TABLE IF EXISTS `hdc_incidence_annual`;
DROP TABLE IF EXISTS `hdc_population_by_age`;
DROP TABLE IF EXISTS `hdc_death_by_age`;

CREATE TABLE `hdc_incidence_monthly` (
    `silver_id`      BIGINT AUTO_INCREMENT PRIMARY KEY,
    `disease`         VARCHAR(20) NOT NULL,
    `province_code`    VARCHAR(10),
    `province_name`     VARCHAR(150),
    `hospcode`           VARCHAR(20),
    `areacode`            VARCHAR(20),
    `b_year_be`            SMALLINT NOT NULL,
    `b_year_ce`             SMALLINT NOT NULL,
    `target`                 DECIMAL(20,2),
    `result`                  DECIMAL(20,2),
    `result10`                DECIMAL(20,2),
    `result11`                 DECIMAL(20,2),
    `result12`                  DECIMAL(20,2),
    `result01`                   DECIMAL(20,2),
    `result02`                    DECIMAL(20,2),
    `result03`                     DECIMAL(20,2),
    `result04`                      DECIMAL(20,2),
    `result05`                       DECIMAL(20,2),
    `result06`                        DECIMAL(20,2),
    `result07`                         DECIMAL(20,2),
    `result08`                          DECIMAL(20,2),
    `result09`                           DECIMAL(20,2),
    KEY `ix_him_disease_year` (`disease`, `b_year_ce`),
    KEY `ix_him_province` (`province_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `hdc_incidence_annual` (
    `silver_id`      BIGINT AUTO_INCREMENT PRIMARY KEY,
    `disease`         VARCHAR(20) NOT NULL DEFAULT 'ihd',
    `province_code`    VARCHAR(10),
    `province_name`     VARCHAR(150),
    `hospcode`           VARCHAR(20),
    `areacode`            VARCHAR(20),
    `b_year_be`            SMALLINT NOT NULL,
    `b_year_ce`             SMALLINT NOT NULL,
    `target`                 DECIMAL(20,2),
    `result`                  DECIMAL(20,2),
    `target1`                  DECIMAL(20,2),
    `result1`                   DECIMAL(20,2),
    KEY `ix_hia_year` (`b_year_ce`),
    KEY `ix_hia_province` (`province_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Unpivoted from the 5 pop_group/result_group column pairs into one row
-- per (disease, area, year, age_group).
CREATE TABLE `hdc_population_by_age` (
    `silver_id`       BIGINT AUTO_INCREMENT PRIMARY KEY,
    `disease`          VARCHAR(20) NOT NULL,
    `province_code`     VARCHAR(10),
    `province_name`      VARCHAR(150),
    `hospcode`            VARCHAR(20),
    `areacode`             VARCHAR(20),
    `b_year_be`             SMALLINT NOT NULL,
    `b_year_ce`              SMALLINT NOT NULL,
    `age_group`               TINYINT NOT NULL COMMENT '1..5, source-defined age bands, meaning varies by disease/report',
    `population`               DECIMAL(20,2),
    `result`                    DECIMAL(20,2),
    KEY `ix_hpa_disease_year` (`disease`, `b_year_ce`),
    KEY `ix_hpa_province` (`province_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Unpivoted from the 5 pt_group/death_group column pairs.
CREATE TABLE `hdc_death_by_age` (
    `silver_id`       BIGINT AUTO_INCREMENT PRIMARY KEY,
    `disease`          VARCHAR(20) NOT NULL,
    `province_code`     VARCHAR(10),
    `province_name`      VARCHAR(150),
    `hospcode`            VARCHAR(20),
    `areacode`             VARCHAR(20),
    `b_year_be`             SMALLINT NOT NULL,
    `b_year_ce`              SMALLINT NOT NULL,
    `age_group`               TINYINT NOT NULL COMMENT '1..5, source-defined age bands, meaning varies by disease/report',
    `person_time`              DECIMAL(20,2),
    `death_count`               DECIMAL(20,2),
    KEY `ix_hdb_disease_year` (`disease`, `b_year_ce`),
    KEY `ix_hdb_province` (`province_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

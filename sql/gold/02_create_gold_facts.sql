-- ============================================================================
-- GOLD LAYER — fact tables, one per source, grain close to the Silver
-- source but resolved against dim_geography/dim_date/dim_industry/
-- dim_hdc_report/dim_disease. fact_hdc_observation pivots Silver's EAV
-- shape into named measure columns (target/result/f3_rate/male/female/
-- total) for the headline fields the KPI tree's Health pillar needs
-- (K-HLT-03/04) -- every other field_name stays in Silver only.
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `fact_income`;
DROP TABLE IF EXISTS `fact_factory`;
DROP TABLE IF EXISTS `fact_community_population`;
DROP TABLE IF EXISTS `fact_disease_ranking`;
DROP TABLE IF EXISTS `fact_hdc_observation`;

-- Grain: one row per (province, year, source_income, soc_eco_class) --
-- same grain as silver.api_nso_income.
CREATE TABLE `fact_income` (
    `fact_id`           BIGINT AUTO_INCREMENT PRIMARY KEY,
    `geo_key`           INT UNSIGNED NOT NULL,
    `date_key`          INT UNSIGNED NOT NULL,
    `source_income1`    VARCHAR(255),
    `source_income2`    VARCHAR(255),
    `source_income3`    VARCHAR(255),
    `soc_eco_class1`    VARCHAR(255),
    `soc_eco_class2`    VARCHAR(255),
    `income_value`      DECIMAL(18,2),
    KEY `ix_fi_geo_date` (`geo_key`, `date_key`),
    CONSTRAINT `fk_fi_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`),
    CONSTRAINT `fk_fi_date` FOREIGN KEY (`date_key`) REFERENCES `dim_date` (`date_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Grain: one row per registered factory -- same grain as silver.api_diw_factory.
CREATE TABLE `fact_factory` (
    `fact_id`           BIGINT AUTO_INCREMENT PRIMARY KEY,
    `geo_key`           INT UNSIGNED NOT NULL COMMENT 'resolved at amphoe/district grain where available, else province',
    `industry_key`      INT UNSIGNED,
    `reg_no`            VARCHAR(100) NOT NULL,
    `factory_name`      VARCHAR(500),
    `capital`           DECIMAL(18,2),
    `workers`           INT,
    `horsepower`        DECIMAL(12,2),
    KEY `ix_ff_geo` (`geo_key`),
    KEY `ix_ff_industry` (`industry_key`),
    CONSTRAINT `fk_ff_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`),
    CONSTRAINT `fk_ff_industry` FOREIGN KEY (`industry_key`) REFERENCES `dim_industry` (`industry_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Grain: one row per (community, fiscal_year) -- same grain as silver.api_bma_community.
CREATE TABLE `fact_community_population` (
    `fact_id`               BIGINT AUTO_INCREMENT PRIMARY KEY,
    `geo_key`               INT UNSIGNED NOT NULL COMMENT 'resolved at subdistrict grain where available, else district',
    `date_key`              INT UNSIGNED NOT NULL,
    `name_of_community`     VARCHAR(500) NOT NULL,
    `type_of_community`     VARCHAR(255),
    `population`            INT,
    `male`                  INT,
    `female`                INT,
    KEY `ix_fcp_geo_date` (`geo_key`, `date_key`),
    CONSTRAINT `fk_fcp_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`),
    CONSTRAINT `fk_fcp_date` FOREIGN KEY (`date_key`) REFERENCES `dim_date` (`date_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Grain: one row per (province, disease, year) -- same grain as
-- silver.api_dds_disease_ranking. 0 rows until DDS's backend recovers.
CREATE TABLE `fact_disease_ranking` (
    `fact_id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
    `geo_key`            INT UNSIGNED NOT NULL,
    `date_key`           INT UNSIGNED NOT NULL,
    `disease_key`        INT UNSIGNED NOT NULL,
    `rank`               SMALLINT,
    `case_count`         DECIMAL(14,2),
    `rate_per_100k`      DECIMAL(14,4),
    `ipd_count`          DECIMAL(14,2),
    `death_count`        DECIMAL(14,2),
    `case_fatality_pct`  DECIMAL(8,4),
    KEY `ix_fdr_geo_date` (`geo_key`, `date_key`),
    CONSTRAINT `fk_fdr_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`),
    CONSTRAINT `fk_fdr_date` FOREIGN KEY (`date_key`) REFERENCES `dim_date` (`date_key`),
    CONSTRAINT `fk_fdr_disease` FOREIGN KEY (`disease_key`) REFERENCES `dim_disease` (`disease_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Grain: one row per (report, year, zone, record_index) -- pivoted from
-- silver.api_hdc_observations' EAV rows. geo_key is resolved from the
-- record's own a_name/a_code field when present (province_keyed layout);
-- NULL when the report uses a different layout (disease_ranking/unsupported,
-- see the field_name/field_value note in sql/silver/18) -- a NULL geo_key
-- here is a real "not area-resolvable from this report", not a loading gap.
CREATE TABLE `fact_hdc_observation` (
    `fact_id`         BIGINT AUTO_INCREMENT PRIMARY KEY,
    `report_key`      INT UNSIGNED NOT NULL,
    `date_key`        INT UNSIGNED NOT NULL,
    `zone`            VARCHAR(10) NOT NULL,
    `record_index`    INT NOT NULL,
    `geo_key`         INT UNSIGNED NULL,
    `area_name_raw`   VARCHAR(255) COMMENT 'a_name as the report itself stated it, kept verbatim alongside the resolved geo_key',
    `target`          DECIMAL(18,2),
    `result`          DECIMAL(18,2),
    `f3_rate`         DECIMAL(18,4) COMMENT 'the report''s own formula-calculated rate, e.g. result/target*100000',
    `male`            DECIMAL(18,2),
    `female`          DECIMAL(18,2),
    `total`           DECIMAL(18,2),
    KEY `ix_fho_report_date_zone` (`report_key`, `date_key`, `zone`),
    KEY `ix_fho_geo` (`geo_key`),
    CONSTRAINT `fk_fho_report` FOREIGN KEY (`report_key`) REFERENCES `dim_hdc_report` (`report_key`),
    CONSTRAINT `fk_fho_date` FOREIGN KEY (`date_key`) REFERENCES `dim_date` (`date_key`),
    CONSTRAINT `fk_fho_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

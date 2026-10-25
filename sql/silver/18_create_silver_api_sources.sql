-- ============================================================================
-- SILVER LAYER — live-API sources (cleansed + conformed from bronze.api_*)
-- NSO income, BMA community, DIW factory registry, DDS disease ranking,
-- HDC health-status observations. Each table casts Bronze's raw text
-- columns to real types and normalizes BE->CE years; dimension resolution
-- against gold.dim_geography/dim_factory/etc. stays a Gold concern, same
-- as every other Silver table in this project.
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `api_nso_income`;
DROP TABLE IF EXISTS `api_bma_community`;
DROP TABLE IF EXISTS `api_diw_factory`;
DROP TABLE IF EXISTS `api_dds_disease_ranking`;
DROP TABLE IF EXISTS `api_hdc_observations`;

-- ----------------------------------------------------------------------------
-- api_nso_income (from bronze.api_nso_income, 15,400 rows)
-- ----------------------------------------------------------------------------
CREATE TABLE `api_nso_income` (
    `silver_id`         BIGINT AUTO_INCREMENT PRIMARY KEY,
    `year_be`           SMALLINT     NOT NULL,
    `year_ce`           SMALLINT     NOT NULL,
    `province`          VARCHAR(255) NOT NULL,
    `source_income1`    VARCHAR(255),
    `source_income2`    VARCHAR(255),
    `source_income3`    VARCHAR(255),
    `soc_eco_class1`    VARCHAR(255),
    `soc_eco_class2`    VARCHAR(255),
    `value`             DECIMAL(18,2),
    `unit`              VARCHAR(100),
    `attribute_note`    VARCHAR(500) COMMENT 'NSO''s own footnote text, e.g. superscript-W marker meaning "0 from a small survey sample"',
    `source_agency`     VARCHAR(255),
    KEY `ix_ani_province_year` (`province`, `year_ce`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- api_bma_community (from bronze.api_bma_community, 6,027 rows)
-- ----------------------------------------------------------------------------
CREATE TABLE `api_bma_community` (
    `silver_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
    `fiscal_year_be`        SMALLINT     NOT NULL,
    `fiscal_year_ce`        SMALLINT     NOT NULL,
    `district`              VARCHAR(255) NOT NULL,
    `subdistrict`           VARCHAR(255) NOT NULL,
    `name_of_community`     VARCHAR(500) NOT NULL,
    `type_of_community`     VARCHAR(255),
    `population`            INT,
    `male`                  INT,
    `female`                INT,
    KEY `ix_abc_district_year` (`district`, `fiscal_year_ce`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- api_diw_factory (from bronze.api_diw_factory, 13,683 rows)
-- PII exclusion carries through from Bronze -- operator_name/phone were
-- never landed there, so there is nothing to cleanse or drop here either.
-- ----------------------------------------------------------------------------
CREATE TABLE `api_diw_factory` (
    `silver_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
    `reg_no`                VARCHAR(100) NOT NULL,
    `factory_name`          VARCHAR(500),
    `business_desc`         TEXT,
    `address_no`            VARCHAR(255),
    `moo`                   VARCHAR(100),
    `soi`                   VARCHAR(255),
    `road`                  VARCHAR(255),
    `tambon`                VARCHAR(255),
    `amphoe`                VARCHAR(255),
    `province`              VARCHAR(255),
    `postcode`              VARCHAR(20),
    `factory_type_code`     VARCHAR(100),
    `capital`               DECIMAL(18,2),
    `workers`               INT,
    `horsepower`            DECIMAL(12,2),
    `tsic`                  VARCHAR(100),
    `old_reg_no`            VARCHAR(100),
    KEY `ix_adf_province_amphoe` (`province`, `amphoe`),
    KEY `ix_adf_reg_no` (`reg_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- api_dds_disease_ranking (from bronze.api_dds_disease_ranking -- 0 rows as
-- of this build; DDS's own backend has been down since 2026-10-25, see
-- docs/03_external_reference_sources.md. Transform is written and ready,
-- just unverified against real data until DDS recovers.)
-- ----------------------------------------------------------------------------
CREATE TABLE `api_dds_disease_ranking` (
    `silver_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
    `year_ce`               SMALLINT     NOT NULL,
    `province_code`         VARCHAR(10)  NOT NULL,
    `rank`                  SMALLINT,
    `disease_name`          VARCHAR(500) NOT NULL,
    `case_count`            DECIMAL(14,2),
    `rate_per_100k`         DECIMAL(14,4),
    `ipd_count`             DECIMAL(14,2),
    `death_count`           DECIMAL(14,2),
    `case_fatality_pct`     DECIMAL(8,4),
    KEY `ix_addr_province_year` (`province_code`, `year_ce`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- api_hdc_observations (from bronze.api_hdc_observations + api_hdc_report_catalog)
-- Same convention as the existing hdc_indicator_observations (manual HDC
-- exports, sql/silver/05): field_value stays TEXT -- values across ~116
-- reports mix counts/rates/percentages with per-report meaning, cast per-
-- report in Gold, not here. Silver's job is resolving report_name (joined
-- from the catalog) and BE->CE year, not typing every value.
-- ----------------------------------------------------------------------------
CREATE TABLE `api_hdc_observations` (
    `silver_id`         BIGINT AUTO_INCREMENT PRIMARY KEY,
    `report_code`       VARCHAR(100) NOT NULL,
    `report_name`       VARCHAR(500),
    `year_be`           SMALLINT     NOT NULL,
    `year_ce`           SMALLINT     NOT NULL,
    `zone`              VARCHAR(10)  NOT NULL,
    `record_index`      INT          NOT NULL,
    `field_name`        VARCHAR(255) NOT NULL,
    `field_value`       VARCHAR(1000) COMMENT 'kept as text -- cast per-report in Gold, mirrors silver.hdc_indicator_observations',
    KEY `ix_aho_report_year` (`report_code`, `year_ce`),
    KEY `ix_aho_field` (`field_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

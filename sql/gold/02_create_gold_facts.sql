-- ============================================================================
-- GOLD LAYER — fact tables, one per source, grain close to the Silver
-- source but resolved against dim_geography/dim_date/dim_industry/
-- dim_hdc_report/dim_disease. fact_hdc_observation pivots Silver's EAV
-- shape into named measure columns (target/result/f3_rate/male/female/
-- total) for the headline fields the KPI tree's Health pillar needs
-- (K-HLT-03/04) -- every other field_name stays in Silver only.
--
-- INCREMENTAL (migrated 2026-11-03): CREATE TABLE IF NOT EXISTS, not
-- DROP+CREATE -- these tables are upserted via MERGE
-- (pipeline/transform_gold_all_sources_incremental.py), not rebuilt from
-- scratch every run. ingestion_batch_id and each table's business-key
-- unique constraint are part of the base schema now, not a later ALTER
-- TABLE patch.
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

-- Grain: one row per (province, year, source_income1/2/3, soc_eco_class1/2)
-- -- same grain as silver.api_nso_income. business_key_hash exists because
-- a direct composite UNIQUE KEY over 5 VARCHAR(255) utf8mb4 columns would
-- exceed InnoDB's 3072-byte max index length -- confirmed live that
-- source_income1+soc_eco_class1 alone collide 1,232 distinct groups
-- (source_income2/3 carry real sub-breakdowns), so the full grain must be
-- in the key, just hashed instead of composited directly.
CREATE TABLE IF NOT EXISTS `fact_income` (
    `fact_id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
    `ingestion_batch_id` VARCHAR(100),
    `geo_key`            INT UNSIGNED NOT NULL,
    `date_key`           INT UNSIGNED NOT NULL,
    `source_income1`     VARCHAR(255),
    `source_income2`     VARCHAR(255),
    `source_income3`     VARCHAR(255),
    `soc_eco_class1`     VARCHAR(255),
    `soc_eco_class2`     VARCHAR(255),
    `income_value`       DECIMAL(18,2),
    `business_key_hash`  VARCHAR(16),
    KEY `ix_fi_geo_date` (`geo_key`, `date_key`),
    UNIQUE KEY `ux_income_business_key` (`business_key_hash`),
    CONSTRAINT `fk_fi_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`),
    CONSTRAINT `fk_fi_date` FOREIGN KEY (`date_key`) REFERENCES `dim_date` (`date_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Grain: one row per registered factory -- same grain as silver.api_diw_factory.
-- reg_no confirmed 100% unique in Silver (13,683 distinct == 13,683 rows)
-- -- safe as a direct natural key, no hashing needed.
-- area_key (kmch-ml input-parity gap 3) is additive: resolved separately
-- from geo_key, by matching DIW's own (amphoe, tambon) text against
-- gold.dim_tambon_unit_xwalk -- NULL where that match fails (DIW rows
-- still resolve geo_key as before regardless). dim_area is created later
-- in GOLD_SCRIPTS order (sql/gold/04) -- the forward FK reference here is
-- valid under this script's own FOREIGN_KEY_CHECKS=0 (confirmed by direct
-- testing), same as sql/gold/04's own backward reference to sql/gold/06.
CREATE TABLE IF NOT EXISTS `fact_factory` (
    `fact_id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
    `ingestion_batch_id` VARCHAR(100),
    `geo_key`            INT UNSIGNED NOT NULL COMMENT 'resolved at amphoe/district grain where available, else province',
    `area_key`           INT UNSIGNED COMMENT 'kmch-ml input-parity gap 3 -- subdistrict/dim_area grain, resolved via (amphoe,tambon) name match against dim_tambon_unit_xwalk; NULL where unmatched',
    `industry_key`       INT UNSIGNED,
    `reg_no`             VARCHAR(100) NOT NULL,
    `factory_name`       VARCHAR(500),
    `capital`            DECIMAL(18,2),
    `workers`            INT,
    `horsepower`         DECIMAL(12,2),
    KEY `ix_ff_geo` (`geo_key`),
    KEY `ix_ff_area` (`area_key`),
    KEY `ix_ff_industry` (`industry_key`),
    UNIQUE KEY `ux_factory_business_key` (`reg_no`),
    CONSTRAINT `fk_ff_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`),
    CONSTRAINT `fk_ff_area` FOREIGN KEY (`area_key`) REFERENCES `dim_area` (`area_key`),
    CONSTRAINT `fk_ff_industry` FOREIGN KEY (`industry_key`) REFERENCES `dim_industry` (`industry_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Grain: one row per (community, fiscal_year) -- same grain as
-- silver.api_bma_community. Confirmed live zero collisions on
-- (geo_key, date_key, name_of_community) -- fits InnoDB's index length
-- limit (name_of_community VARCHAR(500) utf8mb4 = 2000 bytes + 2 INTs),
-- so this is a direct composite key, no hashing needed.
CREATE TABLE IF NOT EXISTS `fact_community_population` (
    `fact_id`               BIGINT AUTO_INCREMENT PRIMARY KEY,
    `ingestion_batch_id`    VARCHAR(100),
    `geo_key`               INT UNSIGNED NOT NULL COMMENT 'resolved at subdistrict grain where available, else district',
    `date_key`              INT UNSIGNED NOT NULL,
    `name_of_community`     VARCHAR(500) NOT NULL,
    `type_of_community`     VARCHAR(255),
    `population`            INT,
    `male`                  INT,
    `female`                INT,
    KEY `ix_fcp_geo_date` (`geo_key`, `date_key`),
    UNIQUE KEY `ux_community_business_key` (`geo_key`, `date_key`, `name_of_community`),
    CONSTRAINT `fk_fcp_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`),
    CONSTRAINT `fk_fcp_date` FOREIGN KEY (`date_key`) REFERENCES `dim_date` (`date_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Grain: one row per (province, disease, year) -- same grain as
-- silver.api_dds_disease_ranking. Fed by TWO incremental Gold builders:
-- _build_fact_disease_ranking (live province-grain API, 0 rows until DDS's
-- backend recovers) and _build_fact_disease_ranking_from_health_region
-- (skr13 PDF archive -> Bangkok only; skr6 is multi-province and stays
-- Silver-only, see that function's docstring).
CREATE TABLE IF NOT EXISTS `fact_disease_ranking` (
    `fact_id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
    `ingestion_batch_id` VARCHAR(100),
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
    UNIQUE KEY `ux_disease_business_key` (`geo_key`, `date_key`, `disease_key`),
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
CREATE TABLE IF NOT EXISTS `fact_hdc_observation` (
    `fact_id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
    `ingestion_batch_id` VARCHAR(100),
    `report_key`         INT UNSIGNED NOT NULL,
    `date_key`           INT UNSIGNED NOT NULL,
    `zone`               VARCHAR(10) NOT NULL,
    `record_index`       INT NOT NULL,
    `geo_key`            INT UNSIGNED NULL,
    `area_name_raw`      VARCHAR(255) COMMENT 'a_name as the report itself stated it, kept verbatim alongside the resolved geo_key',
    `target`             DECIMAL(18,2),
    `result`             DECIMAL(18,2),
    `f3_rate`            DECIMAL(18,4) COMMENT 'the report''s own formula-calculated rate, e.g. result/target*100000',
    `male`               DECIMAL(18,2),
    `female`             DECIMAL(18,2),
    `total`              DECIMAL(18,2),
    KEY `ix_fho_report_date_zone` (`report_key`, `date_key`, `zone`),
    KEY `ix_fho_geo` (`geo_key`),
    UNIQUE KEY `ux_hdc_business_key` (`report_key`, `date_key`, `zone`, `record_index`),
    CONSTRAINT `fk_fho_report` FOREIGN KEY (`report_key`) REFERENCES `dim_hdc_report` (`report_key`),
    CONSTRAINT `fk_fho_date` FOREIGN KEY (`date_key`) REFERENCES `dim_date` (`date_key`),
    CONSTRAINT `fk_fho_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

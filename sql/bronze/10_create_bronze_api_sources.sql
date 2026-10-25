-- ============================================================================
-- BRONZE LAYER TABLE DESIGN — live-API sources (landed via SeaweedFS, see
-- pipeline/landing_store.py), adapted from kmch-ml's (Paiiyahh/kmch-ml,
-- private repo) existing API-backed ingestion.
--
-- These sources overlap topically with existing Bronze tables (NSO income
-- vs. pop_reg_*, BMA vs. community_count_by_district_bkk, DDS vs.
-- dds_health_region_disease_report, HDC vs. hdc_manual_exports/
-- hdc_region6_13, DIW vs. factory_list) but are NOT the same grain or
-- vintage -- kept under a distinct `api_` prefix rather than merged.
-- Reconciliation against the existing equivalents is explicit follow-up
-- work, out of scope here.
--
-- Built one source at a time (NSO+BMA, then DIW, then DDS, then HDC); this
-- file grows with each stage rather than being split per source, matching
-- the one-file-per-source-folder convention used elsewhere in sql/bronze/.
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `api_nso_income`;
DROP TABLE IF EXISTS `api_bma_community`;
DROP TABLE IF EXISTS `api_diw_factory`;
DROP TABLE IF EXISTS `api_dds_disease_ranking`;
DROP TABLE IF EXISTS `api_hdc_observations`;
DROP TABLE IF EXISTS `api_hdc_report_catalog`;

-- ----------------------------------------------------------------------------
-- api_nso_income
-- Source: NSO catalogAPI, table SFD_SPB0802_66 (avg monthly household
-- income by source + socio-economic class, per province) --
-- https://catalogapi.nso.go.th/api/index?table=SFD_SPB0802_66&format=csv
-- Confirmed by direct request: CSV, utf-8-sig, 11 columns, ~15,400 rows.
-- Requires a browser-like User-Agent header -- the endpoint sits behind a
-- WAF that blocks the default python-requests/curl UA with an HTTP 418
-- block page (confirmed by direct testing, not documented anywhere).
-- ----------------------------------------------------------------------------
CREATE TABLE `api_nso_income` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_sheet_name`   VARCHAR(255)  NULL,
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'NSO',

  `raw_year`             VARCHAR(50),
  `raw_province`          VARCHAR(255),
  `raw_source_income1`     VARCHAR(255),
  `raw_source_income2`     VARCHAR(255),
  `raw_source_income3`     VARCHAR(255),
  `raw_soc_eco_class1`      VARCHAR(255),
  `raw_soc_eco_class2`      VARCHAR(255),
  `raw_value`                VARCHAR(100),
  `raw_unit`                  VARCHAR(100),
  `raw_attribute`              VARCHAR(500),
  `raw_source`                  VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- api_bma_community
-- Source: BMA (Bangkok Metropolitan Administration) community registry,
-- CKAN package soc_626755a649135 -- https://data.bangkok.go.th/api/3/action
-- One CSV resource per fiscal year (currently 2565/2566/2567), each landed
-- separately under its own stable CKAN resource id. Individual community
-- records (not pre-aggregated), distinct grain from the existing
-- other_health.community_count_by_district_bkk (district-level counts).
-- ----------------------------------------------------------------------------
CREATE TABLE `api_bma_community` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_sheet_name`   VARCHAR(255)  NULL,
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'BMA',

  `raw_fiscal_year`           VARCHAR(50),
  `raw_district`               VARCHAR(255),
  `raw_subdistrict`             VARCHAR(255),
  `raw_name_of_community`        VARCHAR(500),
  `raw_type_of_community`         VARCHAR(255),
  `raw_number_of_population`      VARCHAR(50),
  `raw_male`                        VARCHAR(50),
  `raw_female`                       VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- api_diw_factory
-- Source: DIW (Dept. of Industrial Works) factory registry, userdb.diw.go.th
-- -- live amphoe-by-amphoe crawl across 3 provinces (Bangkok, Samut Prakan,
-- Chachoengsao), each amphoe landed as its own legacy .xls (BIFF, cp874)
-- response. Likely a broader/more current version of the existing
-- factory_list snapshot (one-time 2024 extract) -- kept separate, not merged.
--
-- PII EXCLUSION (intentional, not an oversight): DIW's raw response also
-- includes operator_name (factory owner's personal name) and phone number.
-- kmch-ml's own documented data-handling rule for this exact source is that
-- these must "stay local... never add them, never print them in outputs" --
-- both columns are dropped during the Bronze shred (extract_load_api_diw.py)
-- and never land in this table, even though every other column is kept
-- 1:1 per Bronze's normal no-transformation convention.
-- ----------------------------------------------------------------------------
CREATE TABLE `api_diw_factory` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_sheet_name`   VARCHAR(255)  NULL,
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'DIW',

  `raw_reg_no`               VARCHAR(100),
  `raw_factory_name`          VARCHAR(500),
  `raw_business_desc`           TEXT,
  `raw_address_no`                VARCHAR(255),
  `raw_moo`                         VARCHAR(100),
  `raw_soi`                          VARCHAR(255),
  `raw_road`                          VARCHAR(255),
  `raw_tambon`                         VARCHAR(255),
  `raw_amphoe`                          VARCHAR(255),
  `raw_province`                         VARCHAR(255),
  `raw_postcode`                          VARCHAR(50),
  `raw_factory_type_code`                   VARCHAR(100),
  `raw_capital`                              VARCHAR(100),
  `raw_workers`                               VARCHAR(50),
  `raw_horsepower`                             VARCHAR(50),
  `raw_tsic`                                    VARCHAR(100),
  `raw_old_reg_no`                                VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- api_dds_disease_ranking
-- Source: DDS (doe.moph.go.th) priority notifiable-disease ranking report
-- (Table 1 of the PDF), province grain, 3 target provinces. Likely the same
-- underlying DDS output as the existing dds_health_region_disease_report
-- (manually exported) -- reconciliation is explicit follow-up, out of scope.
--
-- DDS keeps no archive of a finished year once it stops serving it, so the
-- landing-zone object key (the full source PDF) is this table's only
-- durable link back to the original document -- source_file_name here is
-- load-bearing, not just a convenience pointer.
-- ----------------------------------------------------------------------------
CREATE TABLE `api_dds_disease_ranking` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key (source PDF)',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_sheet_name`   VARCHAR(255)  NULL,
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'DDS',

  `raw_year`                VARCHAR(50),
  `raw_province_code`        VARCHAR(50),
  `raw_rank`                  VARCHAR(50),
  `raw_disease_name`           VARCHAR(500),
  `raw_case_count`               VARCHAR(100),
  `raw_rate_per_100k`             VARCHAR(100),
  `raw_ipd_count`                  VARCHAR(100),
  `raw_death_count`                 VARCHAR(100),
  `raw_case_fatality_pct`             VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- api_hdc_report_catalog
-- Source: HDC (Health Data Center, MOPH) report-catalog API
-- (api-center-hdc.moph.go.th) -- one row per discovered health-status
-- report, giving report_code a resolvable name/subcatalog/year-list.
-- Reference/lookup data, not fact data -- small table.
-- ----------------------------------------------------------------------------
CREATE TABLE `api_hdc_report_catalog` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_sheet_name`   VARCHAR(255)  NULL,
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'HDC',

  `raw_report_code`          VARCHAR(100),
  `raw_report_name`           VARCHAR(500),
  `raw_subcatalog_id`          VARCHAR(100),
  `raw_subcatalog_name`         VARCHAR(255),
  `raw_catalog_label`            VARCHAR(500),
  `raw_active`                     VARCHAR(10),
  `raw_byear_list`                  VARCHAR(255) COMMENT 'Comma-separated list of fiscal years this report currently exposes'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- api_hdc_observations
-- Source: HDC health-status data API (api-hdc.moph.go.th), one row per
-- (report, year, zone, record, field) -- generic EAV shred rather than one
-- table per report shape, since live HDC reports vary in column layout per
-- report (confirmed: province_keyed / disease_ranking / unsupported
-- layouts, numeric columns discovered dynamically). Mirrors the existing
-- hdc_manual_exports schema_registry/report_catalog -> Silver
-- hdc_indicator_observations pattern, just applied directly at Bronze
-- instead of via a hybrid raw_data JSON column, since live HDC's shape
-- varies even more than the manual exports' did.
-- Partial overlap with the existing hdc_manual_exports/hdc_region6_13
-- tables (broader scope, live rather than manually exported) -- kept
-- separate, not merged.
-- ----------------------------------------------------------------------------
CREATE TABLE `api_hdc_observations` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_sheet_name`   VARCHAR(255)  NULL,
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'HDC',

  `raw_report_code`   VARCHAR(100)  NOT NULL,
  `raw_year`           VARCHAR(50)   NOT NULL,
  `raw_zone`             VARCHAR(10)   NOT NULL,
  `raw_record_index`      INT           NOT NULL COMMENT 'Position of this record within the report response (0-based)',
  `raw_field_name`          VARCHAR(255)  NOT NULL,
  `raw_field_value`           TEXT,

  KEY `ix_api_hdc_obs_report_year_zone` (`raw_report_code`, `raw_year`, `raw_zone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

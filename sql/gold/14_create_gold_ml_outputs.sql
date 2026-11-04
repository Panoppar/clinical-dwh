-- ============================================================================
-- GOLD LAYER — ml_area_community_type / ml_area_profile_cluster
--
-- Write-back tables for the kmch-ml community-labels project
-- (C:\Users\PunPun\Desktop\Workspace\KMITL\ML), a separate containerized
-- project that reads this warehouse's gold schema (via the kmch_ml_rw
-- account, sql/00_init_schemas_and_grants.sql) and writes its rule-based
-- + ML cluster labels back here on a daily 2 AM schedule.
--
-- Grain carries run_date and is append-only (one full row set per run, not
-- upserted) -- unlike every other fact table in this warehouse, this one
-- deliberately keeps full history across runs so label drift over time can
-- be analyzed, rather than only exposing "current state". The companion
-- view below exposes just the latest run for dashboard/current-state
-- consumption, matching the shape the source notebook's own
-- area_community_type_wide.csv file had (always just the latest run).
-- ============================================================================

USE gold;

CREATE TABLE IF NOT EXISTS `ml_area_community_type` (
    `fact_id`            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `area_key`           INT UNSIGNED NOT NULL,
    `axis`               VARCHAR(20) NOT NULL COMMENT 'geography | demography',
    `rule_id`            VARCHAR(10) NOT NULL COMMENT 'CL-G1 | CL-G2 | CL-G3 | CL-D1 | CL-D2 | CL-D3',
    `label`              VARCHAR(50) NOT NULL,
    `criterion_value`    DECIMAL(14,4),
    `threshold`          VARCHAR(255),
    `criterion_detail`   JSON,
    `method`             VARCHAR(50),
    `source_level`       VARCHAR(50),
    `source_id`          VARCHAR(100),
    `data_year`          SMALLINT,
    `rule_version`       VARCHAR(20) NOT NULL,
    `run_date`           DATE NOT NULL,
    UNIQUE KEY `ux_mact_area_rule_date` (`area_key`, `rule_id`, `run_date`),
    KEY `ix_mact_run_date` (`run_date`),
    CONSTRAINT `fk_mact_area` FOREIGN KEY (`area_key`) REFERENCES `dim_area` (`area_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ml_area_profile_cluster` (
    `fact_id`             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `area_key`            INT UNSIGNED NOT NULL,
    `cluster_id`          VARCHAR(10) NOT NULL,
    `profile_name`        VARCHAR(255),
    `dist_to_centroid`    DECIMAL(10,4),
    `second_nearest_gap`  DECIMAL(10,4),
    `stability`           DECIMAL(6,4),
    `unstable`            TINYINT(1) NOT NULL,
    `k`                   TINYINT NOT NULL,
    `algorithm`           VARCHAR(20) NOT NULL,
    `seed`                INT NOT NULL,
    `feature_version`     VARCHAR(20) NOT NULL,
    `ml4_rule`            VARCHAR(20) COMMENT 'e.g. ML4-R2 -- which ML4 model revision produced this row (the 3-feature original vs. the 5-feature R2 revision), carried through so both can coexist in history',
    `status`              VARCHAR(20) COMMENT 'e.g. parallel_R2 -- free-text run-status tag from the producing pipeline, not used by any query here',
    `run_date`            DATE NOT NULL,
    UNIQUE KEY `ux_mapc_area_date` (`area_key`, `run_date`),
    CONSTRAINT `fk_mapc_area` FOREIGN KEY (`area_key`) REFERENCES `dim_area` (`area_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Additive migration for installs that already created ml_area_profile_cluster
-- before ml4_rule/status existed (CREATE TABLE IF NOT EXISTS above is a no-op
-- against an existing table). `ADD COLUMN IF NOT EXISTS` itself isn't
-- actually valid syntax on this server (confirmed live 2026-11-04, ERROR
-- 1064 even on a bare `ADD COLUMN IF NOT EXISTS col INT`, despite docs
-- suggesting 8.0.29+ support) -- information_schema + dynamic SQL is the
-- version-safe way to make this idempotent instead.
SET @ml4_rule_exists := (
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'ml_area_profile_cluster' AND column_name = 'ml4_rule'
);
SET @ml4_rule_sql := IF(@ml4_rule_exists = 0,
    'ALTER TABLE `ml_area_profile_cluster` ADD COLUMN `ml4_rule` VARCHAR(20) COMMENT ''e.g. ML4-R2 -- which ML4 model revision produced this row (the 3-feature original vs. the 5-feature R2 revision), carried through so both can coexist in history'' AFTER `feature_version`',
    'SELECT 1');
PREPARE ml4_rule_stmt FROM @ml4_rule_sql;
EXECUTE ml4_rule_stmt;
DEALLOCATE PREPARE ml4_rule_stmt;

SET @status_exists := (
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'ml_area_profile_cluster' AND column_name = 'status'
);
SET @status_sql := IF(@status_exists = 0,
    'ALTER TABLE `ml_area_profile_cluster` ADD COLUMN `status` VARCHAR(20) COMMENT ''e.g. parallel_R2 -- free-text run-status tag from the producing pipeline, not used by any query here'' AFTER `ml4_rule`',
    'SELECT 1');
PREPARE status_stmt FROM @status_sql;
EXECUTE status_stmt;
DEALLOCATE PREPARE status_stmt;

CREATE OR REPLACE VIEW `vw_ml_area_community_type_wide` AS
SELECT a.unit_code, a.unit_th, a.province_code, a.amphoe_code, a.is_catchment,
       MAX(CASE WHEN t.rule_id = 'CL-D1' THEN t.label END) AS `CL-D1`,
       MAX(CASE WHEN t.rule_id = 'CL-D2' THEN t.label END) AS `CL-D2`,
       MAX(CASE WHEN t.rule_id = 'CL-D3' THEN t.label END) AS `CL-D3`,
       MAX(CASE WHEN t.rule_id = 'CL-G1' THEN t.label END) AS `CL-G1`,
       MAX(CASE WHEN t.rule_id = 'CL-G2' THEN t.label END) AS `CL-G2`,
       MAX(CASE WHEN t.rule_id = 'CL-G3' THEN t.label END) AS `CL-G3`,
       t.rule_version, t.run_date
FROM ml_area_community_type t
JOIN dim_area a ON a.area_key = t.area_key
WHERE t.run_date = (SELECT MAX(run_date) FROM ml_area_community_type)
GROUP BY a.unit_code, a.unit_th, a.province_code, a.amphoe_code, a.is_catchment,
         t.rule_version, t.run_date;

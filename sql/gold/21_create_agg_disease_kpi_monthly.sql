-- ============================================================================
-- GOLD LAYER — agg_disease_kpi_monthly
-- Pre-computed KPIs from the earlier KPI catalog: case-fatality rate,
-- target-attainment %, YoY change. Two natural grains feed this table
-- (same UNION-not-join approach as the OBT, for the same reason):
-- fact_disease_incidence_hdc is genuinely monthly (target_attainment_pct
-- + YoY), while fact_disease_event's case-fatality rate is only
-- meaningful for DDS (the only source with both a patient count and a
-- death count in the same row) and is year-grain, not monthly --
-- case_fatality rows carry month=NULL rather than a fabricated month.
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `agg_disease_kpi_monthly`;

CREATE TABLE `agg_disease_kpi_monthly` (
    `agg_key`                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `geo_key`                  INT UNSIGNED NULL,
    `date_key`                   INT          NOT NULL,
    `disease_key`                  INT UNSIGNED NOT NULL,
    `year_ce`                        SMALLINT     NOT NULL,
    `month`                            TINYINT      NULL COMMENT 'NULL for year-grain case-fatality rows',
    `case_fatality_rate_pct`             DECIMAL(6,2)  NULL,
    `target_attainment_pct`                DECIMAL(10,4) NULL COMMENT 'result / target x 100',
    `yoy_change_pct`                         DECIMAL(10,4) NULL,
    `kpi_type`                                  VARCHAR(20)  NOT NULL COMMENT 'case_fatality | target_attainment',
    `source_system`                               VARCHAR(20) NOT NULL,
    KEY `ix_adkm_geo_date` (`geo_key`, `date_key`),
    KEY `ix_adkm_disease` (`disease_key`),
    KEY `ix_adkm_kpi_type` (`kpi_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

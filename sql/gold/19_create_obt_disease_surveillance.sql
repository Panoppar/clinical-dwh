-- ============================================================================
-- GOLD LAYER — obt_disease_surveillance
-- One denormalized row per (geography, date, disease) for Metabase --
-- zero joins, zero runtime math. Combines both disease fact tables via
-- UNION ALL rather than a join, since they're genuinely different grains
-- (fact_disease_event: mostly year-grain, count/death-based;
-- fact_disease_incidence_hdc: month-grain, target/result-based) --
-- each side populates the columns it has and leaves the rest NULL,
-- distinguished by source_system/grain rather than forcing a false
-- common shape.
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `obt_disease_surveillance`;

CREATE TABLE `obt_disease_surveillance` (
    `obt_key`                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `geo_key`                    INT UNSIGNED NULL,
    `date_key`                     INT          NOT NULL,
    `disease_key`                    INT UNSIGNED NOT NULL,
    `province_name_th`                 VARCHAR(150),
    `district_name_th`                   VARCHAR(150),
    `subdistrict_name_th`                  VARCHAR(150),
    `disease_name`                            VARCHAR(300) NOT NULL,
    `year_ce`                                  SMALLINT     NOT NULL,
    `month`                                      TINYINT      NOT NULL,
    `sex`                                          VARCHAR(10)  NULL,
    `health_region_code`                            VARCHAR(20)  NULL,
    `case_count`                                      BIGINT NULL,
    `death_count`                                       BIGINT NULL,
    `rate_per_100k`                                       DECIMAL(12,4) NULL,
    `case_fatality_rate_pct`                                DECIMAL(6,2) NULL,
    `target`                                                  DECIMAL(20,2) NULL,
    `result`                                                    DECIMAL(20,2) NULL,
    `target_attainment_pct`                                       DECIMAL(10,4) NULL COMMENT 'result / target x 100',
    `grain`                                                         VARCHAR(20)  NOT NULL COMMENT 'event_year | event_annual_hdc | incidence_monthly | incidence_annual',
    `source_system`                                                   VARCHAR(20) NOT NULL,
    KEY `ix_ods_geo_date` (`geo_key`, `date_key`),
    KEY `ix_ods_disease` (`disease_key`),
    KEY `ix_ods_year_month` (`year_ce`, `month`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

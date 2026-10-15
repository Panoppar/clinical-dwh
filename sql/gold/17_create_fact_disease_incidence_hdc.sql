-- ============================================================================
-- GOLD LAYER — fact_disease_incidence_hdc
-- HDC's target/result KPI-tracking data -- genuinely different measure
-- shape from fact_disease_event (a target vs. actual pair, not a simple
-- case/death count), so it gets its own fact table per the plan.
--
-- grain='monthly' rows come from hdc_incidence_monthly, unpivoted from
-- its result10/11/12/01..09 columns (Thai government fiscal year order:
-- Oct-Dec of b_year_ce-1, then Jan-Sep of b_year_ce) into one row per
-- calendar month; grain='annual' rows come from hdc_incidence_annual
-- (which only tracks disease='ihd', confirmed by inspection -- the other
-- 10 HDC diseases have no annual incidence-target series). target_alt/
-- result_alt hold hdc_incidence_annual's second target/result pair
-- (target1/result1 in Silver) -- confirmed present and numerically
-- close-but-different from target/result, but without source
-- documentation to confirm exactly what distinguishes them; kept
-- separate rather than guessing which one is "the" KPI.
--
-- geo_key resolves to DISTRICT level via areacode's first 4 digits,
-- additionally cross-checked against the row's own province_code
-- (confirmed 100% match rate against dim_geography when both agree,
-- 1669/1669 distinct areacodes) -- hospcode/areacode themselves are kept
-- as plain traceability columns since they're finer-grained than any
-- dim_geography level (a hospital's catchment area, not an
-- administrative unit).
--
-- 21 distinct source rows (252 of 498,936 monthly rows once unpivoted --
-- 0.05%) have province_code disagreeing with areacode's own embedded
-- province prefix (e.g. province_code='11' but areacode starts '10') --
-- confirmed a genuine source data inconsistency (likely a hospital whose
-- reported province differs from a specific cross-border catchment
-- area's code), not a join bug. geo_key stays NULL for these rather than
-- picking one of the two disagreeing fields arbitrarily.
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `fact_disease_incidence_hdc`;

CREATE TABLE `fact_disease_incidence_hdc` (
    `fact_key`            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `geo_key`               INT UNSIGNED NULL,
    `date_key`                INT          NOT NULL,
    `disease_key`               INT UNSIGNED NOT NULL,
    `grain`                        VARCHAR(10)  NOT NULL COMMENT 'monthly | annual',
    `hospcode`                       VARCHAR(20)  NULL,
    `areacode`                         VARCHAR(20)  NULL,
    `target`                             DECIMAL(20,2) NULL,
    `result`                              DECIMAL(20,2) NULL,
    `target_alt`                            DECIMAL(20,2) NULL COMMENT 'annual grain only, see header comment',
    `result_alt`                              DECIMAL(20,2) NULL COMMENT 'annual grain only, see header comment',
    `source_system`                             VARCHAR(20) NOT NULL DEFAULT 'hdc',
    KEY `ix_fdih_geo_date` (`geo_key`, `date_key`),
    KEY `ix_fdih_disease` (`disease_key`),
    KEY `ix_fdih_grain` (`grain`),
    KEY `ix_fdih_facility` (`hospcode`, `areacode`, `disease_key`, `grain`, `date_key`) COMMENT 'supports the YoY self-join in agg_disease_kpi_monthly -- without it, a 507K-row self-join on this facility-grain key becomes a full scan and takes well over an hour',
    CONSTRAINT `fk_fdih_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`),
    CONSTRAINT `fk_fdih_date` FOREIGN KEY (`date_key`) REFERENCES `dim_date` (`date_key`),
    CONSTRAINT `fk_fdih_disease` FOREIGN KEY (`disease_key`) REFERENCES `dim_disease` (`disease_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

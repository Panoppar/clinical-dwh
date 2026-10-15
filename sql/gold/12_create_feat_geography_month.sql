-- ============================================================================
-- GOLD LAYER — feat_geography_month
-- Feature store pattern: grain = geo_key x date_key (month), flat and wide
-- for the Bayesian spatial-temporal model. No FK constraints -- this
-- table is meant to be read standalone by an ML pipeline without joining
-- back into the warehouse; geography codes are kept as plain columns for
-- exactly that reason.
--
-- pop_density_proxy is literally total_count, not a real density (no
-- land-area source exists in this warehouse yet) -- a documented
-- stand-in, not a real metric; rename/replace once an area source exists.
--
-- pct_age_* only populates where age-breakdown data exists for that
-- geo_key+month: NSO (country + province, sparse years/months, only
-- 2024 has full single-year-of-age detail) and other_health (Bangkok
-- subdistricts). Same real data-availability gap as
-- agg_population_summary_yearly, just at monthly instead of yearly grain.
--
-- total_count_lag1/lag12 are NULL at the earliest period for any given
-- geo_key (no prior period to lag from) and whenever this source's
-- actual snapshot cadence skips the exact prior month/year -- expected,
-- not a bug, same self-join-on-exact-date reasoning as the OBT's growth
-- rates.
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `feat_geography_month`;

CREATE TABLE `feat_geography_month` (
    `feat_key`              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `geo_key`                  INT UNSIGNED NOT NULL,
    `date_key`                   INT          NOT NULL,
    `admin_level`                  VARCHAR(12)  NOT NULL,
    `province_code`                  VARCHAR(10),
    `district_code`                    VARCHAR(15),
    `subdistrict_code`                   VARCHAR(15),
    `year_ce`                              SMALLINT     NOT NULL,
    `month`                                  TINYINT      NOT NULL,
    `total_count`                              BIGINT,
    `pop_density_proxy`                          BIGINT COMMENT 'stand-in = total_count; no land-area source exists yet',
    `pct_age_0_14`                                  DECIMAL(10,4),
    `pct_age_15_64`                                    DECIMAL(10,4),
    `pct_age_65_plus`                                     DECIMAL(10,4),
    `sex_ratio`                                              DECIMAL(10,4) COMMENT 'males per 100 females',
    `total_count_lag1`                                        BIGINT COMMENT 'exact prior month, same geo',
    `total_count_lag12`                                          BIGINT COMMENT 'exact prior year, same month',
    KEY `ix_fgm_geo_date` (`geo_key`, `date_key`),
    KEY `ix_fgm_year_month` (`year_ce`, `month`),
    KEY `ix_fgm_admin_level` (`admin_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

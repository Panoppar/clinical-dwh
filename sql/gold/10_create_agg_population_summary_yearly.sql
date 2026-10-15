-- ============================================================================
-- GOLD LAYER — agg_population_summary_yearly
-- Grain: geo_key x year. Coarser than the OBT, pre-joining age/sex data
-- for ratios that would otherwise need a runtime join in every dashboard
-- card.
--
-- age_dependency_ratio / aging_index / non_thai_national_pct are only
-- populated where age-breakdown data exists for that geo_key: NSO covers
-- country + the 77 provinces; other_health covers Bangkok's subdistricts
-- only. Districts and non-Bangkok subdistricts have no age-breakdown
-- source at all -- NULL here, not a bug, a real data-availability gap.
-- Within NSO specifically, confirmed by inspection: the single
-- age-independent grand total (DEM_IND24, sex=total, age_qualifier=
-- 'total') spans 2017-2025, but the detailed single-year-of-age
-- breakdown needed for age_dependency_ratio/aging_index exists only for
-- 2024 -- so non_thai_national_pct populates for all 9 years while the
-- two age-band ratios populate for 2024 only. Different publication
-- detail levels per year, not a join bug (confirmed: the 2024 figures
-- -- 41.65% dependency ratio, aging index 94.19 -- are plausible and
-- consistent with Thailand's known aging-population trend).
-- The two sources also differ in HOW a "total population in an age
-- range" is derived (NSO: sex='total' rows exist directly under its
-- headline indicator DEM_IND24; other_health's age_bracket rows have no
-- pre-summed total, only male/female, so those are summed explicitly) --
-- handled per-source in the load query, not assumed to be the same shape.
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `agg_population_summary_yearly`;

CREATE TABLE `agg_population_summary_yearly` (
    `agg_key`              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `geo_key`                INT UNSIGNED NOT NULL,
    `year_ce`                  SMALLINT     NOT NULL,
    `admin_level`                VARCHAR(12)  NOT NULL,
    `total_count`                  BIGINT       COMMENT 'December snapshot for that year, where available',
    `yoy_growth_pct`                 DECIMAL(10,4),
    `age_dependency_ratio`             DECIMAL(10,4) COMMENT '(pop <15 + pop >=65) / pop 15-64 x 100',
    `aging_index`                        DECIMAL(10,4) COMMENT 'pop >=65 / pop <15 x 100',
    `non_thai_national_pct`                DECIMAL(10,4) COMMENT 'NSO only (DEM_IND49/DEM_IND24) -- not available for other_health geographies',
    UNIQUE KEY `ux_apsy_geo_year` (`geo_key`, `year_ce`),
    KEY `ix_apsy_year` (`year_ce`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

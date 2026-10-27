-- ============================================================================
-- GOLD LAYER — industrial location quotient / concentration (kmch-ml
-- input-parity gap 3). New file, does not touch any table in sql/gold/
-- 01-09 -- those stay exactly as-is.
--
-- Recomputed from fact_factory + dim_industry_division on every refresh
-- (not loaded as a static copy of kmch-ml's own CSV snapshot) -- matches
-- this warehouse's existing philosophy of computing once in Gold and
-- re-deriving as the source is re-crawled.
--
-- Methodology (reverse-engineered from kmch-ml's track_c_lq.csv /
-- track_c_unit_summary.csv and confirmed exactly against their own
-- numbers before this was built):
--   - Scoped to factories with a proper TSIC-2009 5-digit code only
--     (dim_industry.tsic_code length = 5) -- DIW's "old or short code"
--     and uncoded factories are excluded from n_factories/workers/
--     unit_factories/unit_workers here, same as kmch-ml's own
--     factories_tsic2009_5digit filter.
--   - "region" = the whole 3-catchment-province scope combined, not
--     per-province -- confirmed: kmch-ml's region_share_workers for a
--     given division is identical across all 3 provinces in their export.
--   - lq_workers = share_of_unit_workers / region_share_workers
--     lq_factories = share_of_unit_factories / region_share_factories
--     (both exact-match kmch-ml's own values to high precision when
--     recomputed this way.)
--   - small_n = n_factories < 3 (exact match against kmch-ml's flag).
--   - industrial_concentration here is a best-effort approximation
--     (lq_workers >= 2 AND NOT small_n), ~91% agreement against kmch-ml's
--     reference export -- their exact rule could not be fully
--     reverse-engineered from the data alone (likely a statistical
--     significance test, not a flat threshold). Documented as approximate,
--     not claimed as exact parity.
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `agg_industrial_concentration_by_unit_division`;
DROP TABLE IF EXISTS `agg_industrial_concentration_by_unit`;

-- Grain: one row per (unit, division) -- matches track_c_lq.csv.
CREATE TABLE `agg_industrial_concentration_by_unit_division` (
    `agg_id`                      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `area_key`                     INT UNSIGNED NOT NULL,
    `division_code`                 CHAR(2)      NOT NULL,
    `n_factories`                     INT NOT NULL COMMENT 'factories in this unit x division, TSIC-2009-5-digit-coded only',
    `workers`                           INT NOT NULL,
    `unit_factories`                      INT NOT NULL COMMENT 'total TSIC-2009-5-digit-coded factories in this unit, all divisions',
    `unit_workers`                          INT NOT NULL,
    `share_of_unit_workers`                   DECIMAL(10,6),
    `region_share_workers`                      DECIMAL(10,6) COMMENT 'this division''s share of workers across the whole 3-province catchment, not per-province',
    `lq_workers`                                  DECIMAL(12,4),
    `lq_factories`                                  DECIMAL(12,4),
    `small_n`                                        TINYINT(1) NOT NULL COMMENT 'n_factories < 3',
    `industrial_concentration`                         TINYINT(1) NOT NULL COMMENT 'best-effort approximation, see file header note -- not exact parity with kmch-ml''s own flag',
    UNIQUE KEY `ux_aicud_area_division` (`area_key`, `division_code`),
    KEY `ix_aicud_division` (`division_code`),
    CONSTRAINT `fk_aicud_area` FOREIGN KEY (`area_key`) REFERENCES `dim_area` (`area_key`),
    CONSTRAINT `fk_aicud_division` FOREIGN KEY (`division_code`) REFERENCES `dim_industry_division` (`division_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Grain: one row per unit -- matches track_c_unit_summary.csv.
CREATE TABLE `agg_industrial_concentration_by_unit` (
    `agg_id`                          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `area_key`                         INT UNSIGNED NOT NULL UNIQUE,
    `factories_registered`              INT NOT NULL COMMENT 'ALL factories in this unit, regardless of TSIC classification',
    `workers_registered`                  INT NOT NULL,
    `factories_tsic2009_5digit`             INT NOT NULL COMMENT 'subset with a proper TSIC-2009 5-digit code -- the base for every LQ figure here',
    `share_workers_not_classified`            DECIMAL(10,6) COMMENT 'transparency metric only, not used in the LQ calc itself',
    `top_division_code`                         CHAR(2),
    `top_division_workers`                        INT,
    `top_division_lq`                               DECIMAL(12,4),
    `n_concentrated_divisions`                        INT NOT NULL COMMENT 'count of divisions in this unit flagged industrial_concentration=1',
    `industrial_concentration`                          TINYINT(1) NOT NULL COMMENT '1 if any division in this unit is flagged concentrated',
    CONSTRAINT `fk_aicu_area` FOREIGN KEY (`area_key`) REFERENCES `dim_area` (`area_key`),
    CONSTRAINT `fk_aicu_division` FOREIGN KEY (`top_division_code`) REFERENCES `dim_industry_division` (`division_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

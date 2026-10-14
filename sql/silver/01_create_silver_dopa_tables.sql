-- ============================================================================
-- SILVER LAYER — DOPA population by administrative area and month
--
-- Conforms bronze.dopa_population_by_area_month into one canonical row per
-- (yymm, admin_level, area_code). Bronze deliberately kept every source
-- variant (pipe-delimited historical series, html yearly snapshots, a
-- corrupted-text/clean-text pair, a triplicated file) with zero
-- deduplication -- Silver's job is to pick exactly one row per real-world
-- fact so a naive SUM() doesn't double- or triple-count.
--
-- Canonical-variant rule, verified empirically against bronze (not assumed):
--   - province: only one schema_variant exists, nothing to pick.
--   - district: long_format_pipe_delimited, raw_source_clean_text, and
--     raw_source_corrupted_text all cover the identical 28 months
--     (yymm 3612-6312) with IDENTICAL totals (5,075,930,076 each, confirmed
--     by direct query) -- keep long_format_pipe_delimited, drop the other
--     two entirely. html_yearly_snapshot covers only yymm=6712, which the
--     pipe file doesn't reach, so it's additive, not a duplicate -- kept.
--   - subdistrict: long_format_pipe_delimited covers yymm 3612-6312.
--     html_yearly_snapshot covers yymm 6012-6712, overlapping the pipe file
--     for 6012/6112/6212/6312 -- confirmed identical row counts AND
--     identical total-population sums for all 4 overlapping months, so the
--     pipe file wins there; html_yearly_snapshot is kept only for its
--     non-overlapping months (6412-6712). html_yearly_snapshot_triplicated
--     (yymm=6812) already carries is_duplicate_row from bronze -- only the
--     first copy (is_duplicate_row=0) survives into Silver.
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `population_by_area_month`;

CREATE TABLE `population_by_area_month` (
    `silver_id`       BIGINT AUTO_INCREMENT PRIMARY KEY,
    `admin_level`     VARCHAR(20)  NOT NULL,
    `yymm`            VARCHAR(4)   NOT NULL,
    `year_be`         SMALLINT     NOT NULL,
    `year_ce`         SMALLINT     NOT NULL,
    `month`           TINYINT      NOT NULL,
    `cc_code`         VARCHAR(10),
    `cc_desc`         VARCHAR(100),
    `rcode_code`      VARCHAR(10),
    `rcode_desc`      VARCHAR(150),
    `ccaatt_code`     VARCHAR(10),
    `ccaatt_desc`     VARCHAR(150),
    `ccaattmm_code`   VARCHAR(10),
    `ccaattmm_desc`   VARCHAR(150),
    `male`            BIGINT,
    `female`          BIGINT,
    `total`           BIGINT,
    `house`           BIGINT,
    -- is_rollup_row: every admin_level file embeds coarser rollup totals
    -- alongside its own leaf-level rows (confirmed by inspection: the
    -- "province" file has a cc_code='0' whole-country row next to 77 real
    -- provinces -- unfiltered SUM() returns exactly 2x the real total,
    -- 132,373,454 vs 66,186,727; the "district" file embeds both
    -- province-level AND country-level rollups via rcode_code='0' -- 78
    -- rollup rows, not 77, confirmed; "subdistrict" embeds all three
    -- coarser levels via ccaatt_code='0'). Always add
    -- `AND is_rollup_row = 0` before any SUM() grouped within one
    -- admin_level, or filter to the specific rollup level you want instead.
    `is_rollup_row`   TINYINT(1)   NOT NULL DEFAULT 0,
    `source_schema_variant` VARCHAR(50) NOT NULL COMMENT 'which bronze variant won the canonical pick, for lineage',
    KEY `ix_spam_level_yymm` (`admin_level`, `yymm`),
    KEY `ix_spam_codes` (`cc_code`, `rcode_code`, `ccaatt_code`),
    KEY `ix_spam_rollup` (`is_rollup_row`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

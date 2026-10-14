-- ============================================================================
-- SILVER LAYER — other_health's population tables
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `population_by_age_subdistrict_bkk`;
DROP TABLE IF EXISTS `population_by_tambon_national`;
DROP TABLE IF EXISTS `elderly_dependency_by_district`;

-- Unpivoted from bronze's 219-key age_sex_data JSON (one row per village
-- per original key -> one row per village per (component_type, sex, age)
-- here). component_type distinguishes the 204 regular age/sex brackets
-- from the 5 special non-age categories bronze's source carried
-- (lunar-calendar birth year, central house registration, non-Thai
-- nationals, mid-move, and the grand total) -- same modeling pattern as
-- NSO's DEM_IND24/48/50/109 components, built in from the start this time
-- instead of discovered via a shipped bug.
-- is_headline_total: true only for component_type='grand_total' AND
-- sex='total' -- the one real population figure. Always filter to this
-- (or to a specific component_type + sex) before summing; summing
-- everything blindly double/triple counts across both the 5 special
-- categories and the male/female/total sex dimension.
CREATE TABLE `population_by_age_subdistrict_bkk` (
    `silver_id`        BIGINT AUTO_INCREMENT PRIMARY KEY,
    `year_ce`           SMALLINT     NOT NULL,
    `month`              TINYINT      NOT NULL,
    `province_code`       VARCHAR(20),
    `province_name`        VARCHAR(100),
    `registrar_code`        VARCHAR(20),
    `registrar_name`         VARCHAR(150),
    `tambon_code`              VARCHAR(20),
    `tambon_name`               VARCHAR(150),
    `village_code`               VARCHAR(20),
    `village_name`                VARCHAR(150),
    `component_type`               VARCHAR(20) NOT NULL COMMENT 'age_bracket | lunar_birth | central_house_reg | non_thai_national | mid_move | grand_total',
    `sex`                            VARCHAR(10) NOT NULL COMMENT 'male | female | total',
    `age_exact`                       SMALLINT    COMMENT 'NULL for the 5 non-age component_types',
    `age_qualifier`                    VARCHAR(10) COMMENT 'exact | lt | gt, NULL for non-age component_types',
    `is_headline_total`                 TINYINT(1)  NOT NULL DEFAULT 0,
    `population_count`                   BIGINT,
    KEY `ix_pasb_village` (`village_code`),
    KEY `ix_pasb_component` (`component_type`, `sex`),
    KEY `ix_pasb_headline` (`is_headline_total`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Deduped from the unflagged internal triplication (bronze keeps all 3
-- copies, no flag column exists there -- Silver keeps only the first).
CREATE TABLE `population_by_tambon_national` (
    `silver_id`     BIGINT AUTO_INCREMENT PRIMARY KEY,
    `yymm`           VARCHAR(4) NOT NULL,
    `year_be`         SMALLINT   NOT NULL,
    `year_ce`          SMALLINT   NOT NULL,
    `month`             TINYINT    NOT NULL,
    `cc_code`            VARCHAR(10),
    `cc_desc`             VARCHAR(100),
    `rcode_code`           VARCHAR(10),
    `rcode_desc`            VARCHAR(150),
    `ccaatt_code`             VARCHAR(10),
    `ccaatt_desc`              VARCHAR(150),
    `ccaattmm_code`             VARCHAR(10),
    `ccaattmm_desc`              VARCHAR(150),
    `male`                        BIGINT,
    `female`                      BIGINT,
    `total`                        BIGINT,
    `house`                         BIGINT,
    -- Same embedded-rollup design as DOPA's files (confirmed: this is
    -- literally the same Dec-2025 nationwide snapshot, just delivered via
    -- a different folder) -- ccaatt_code='0' marks a coarser rollup
    -- (country/province/district) nested among the real tambon rows.
    `is_rollup_row`                   TINYINT(1) NOT NULL DEFAULT 0,
    KEY `ix_ptn_codes` (`cc_code`, `rcode_code`, `ccaatt_code`),
    KEY `ix_ptn_rollup` (`is_rollup_row`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- UNDOCUMENTED ANOMALY (found independently): bronze carries 2 files whose
-- filenames suggest disjoint fiscal years (_2566, _2568) but actually
-- overlap -- confirmed by inspection: the "_2566" file holds BE2566 AND
-- BE2567 data; the "_2568" file holds BE2566, BE2567, AND BE2568, with
-- IDENTICAL figures for the 2 overlapping years (just a different district-
-- name prefix convention, "บางบ่อ" vs "อำเภอบางบ่อ"). The "_2566" file is
-- therefore a strict subset of "_2568" -- Silver uses "_2568" exclusively.
-- Also carries a "รวม" (total) row per fiscal year alongside the district
-- breakdown -- confirmed by inspection to equal the exact sum of that
-- year's districts (93+53+20+161+82+386=795 for BE2568) -- flagged
-- is_aggregate_row rather than dropped, consistent with this project's
-- established pattern elsewhere.
CREATE TABLE `elderly_dependency_by_district` (
    `silver_id`         BIGINT AUTO_INCREMENT PRIMARY KEY,
    `fiscal_year_be`      SMALLINT    NOT NULL,
    `fiscal_year_ce`       SMALLINT   NOT NULL,
    `district_name`         VARCHAR(100) NOT NULL,
    `bedridden_count`        BIGINT,
    `homebound_count`         BIGINT,
    `socially_isolated_count`  BIGINT,
    `unit`                      VARCHAR(50),
    `source_attribution`        VARCHAR(300),
    `is_aggregate_row`           TINYINT(1) NOT NULL DEFAULT 0,
    KEY `ix_edd_year` (`fiscal_year_ce`),
    KEY `ix_edd_aggregate` (`is_aggregate_row`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

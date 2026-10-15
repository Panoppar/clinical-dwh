-- ============================================================================
-- GOLD LAYER — fact_disease_event
-- Grain: geo_key(nullable) x date_key x disease_key x age_sex_key(nullable).
-- Covers the 7 "count/death-based" disease sources (DDS, cause_of_death,
-- ncd_mortality, sick_298group, compare_cases). is_aggregate_row=0
-- already applied at load -- same structural-incapability principle as
-- fact_population_by_area's rollup rows.
--
-- geo_key is nullable: compare_cases_by_disease/surveillance_top_diseases
-- have no geography breakdown at all (mapped to the 'country' geo_key
-- instead, since they're genuinely national-level counts) while
-- compare_cases_by_subdistrict has one real unmatched placeholder row
-- ("(ไม่ระบุ/ไม่มีแขวง)" -- not specified/no subdistrict) that stays
-- NULL rather than being dropped or guessed.
--
-- health_region_code is DDS-only (Thai MOPH health-service zones, e.g.
-- "skr13") -- NOT the same hierarchy as dim_geography (a health region
-- spans multiple provinces, not a strict parent/child fit), so it's kept
-- as a plain descriptive column, not FK'd.
--
-- case_count/death_count/rate_per_100k are deliberately generic slots
-- shared across sources that measure the same underlying concept
-- differently (cause_of_death's total_count IS a death count; DDS's
-- patient_count is a case count; ncd_mortality's death_rate_per_100k and
-- cause_of_death's rate_per_100k both land in rate_per_100k). ipd_count
-- and case_fatality_rate_pct are DDS-only measures with no equivalent
-- elsewhere, kept as their own nullable columns rather than overloaded.
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `fact_disease_event`;

CREATE TABLE `fact_disease_event` (
    `fact_key`                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `geo_key`                   INT UNSIGNED NULL,
    `date_key`                    INT          NOT NULL,
    `disease_key`                   INT UNSIGNED NOT NULL,
    `age_sex_key`                     INT UNSIGNED NULL,
    `health_region_code`                VARCHAR(20)  NULL COMMENT 'DDS only, e.g. skr13 -- not FK''d, spans multiple provinces',
    `case_count`                          BIGINT NULL,
    `death_count`                          BIGINT NULL,
    `rate_per_100k`                         DECIMAL(12,4) NULL,
    `ipd_count`                               BIGINT NULL COMMENT 'DDS only',
    `case_fatality_rate_pct`                    DECIMAL(6,2) NULL COMMENT 'DDS only, source-provided',
    `source_system`                               VARCHAR(20) NOT NULL,
    KEY `ix_fde_geo_date` (`geo_key`, `date_key`),
    KEY `ix_fde_disease` (`disease_key`),
    CONSTRAINT `fk_fde_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`),
    CONSTRAINT `fk_fde_date` FOREIGN KEY (`date_key`) REFERENCES `dim_date` (`date_key`),
    CONSTRAINT `fk_fde_disease` FOREIGN KEY (`disease_key`) REFERENCES `dim_disease` (`disease_key`),
    CONSTRAINT `fk_fde_age_sex` FOREIGN KEY (`age_sex_key`) REFERENCES `dim_age_sex` (`age_sex_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

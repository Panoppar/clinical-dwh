-- ============================================================================
-- SILVER LAYER — other_health's disease/surveillance tables
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `sick_298group_long`;
DROP TABLE IF EXISTS `sick_298group_wide`;
DROP TABLE IF EXISTS `surveillance_top_diseases`;
DROP TABLE IF EXISTS `compare_cases_by_disease`;
DROP TABLE IF EXISTS `compare_cases_by_subdistrict`;
DROP TABLE IF EXISTS `ncd_mortality_by_disease`;
DROP TABLE IF EXISTS `cause_of_death_top10_with_rate`;
DROP TABLE IF EXISTS `cause_of_death_top10_no_rate`;

-- sick_298group_long / _wide: checked for a merge (per plan) and found
-- real complexity, not a clean redundancy -- for the overlapping
-- (province, year) combos, matching disease groups have IDENTICAL
-- figures (confirmed: 104 เบาหวาน = 77,533/132,162 in both), but "_long"
-- carries ~32 distinct disease groups per combo while "_wide" carries
-- only 16 -- neither is a strict superset of the other. Kept as 2
-- separate Silver tables rather than forcing a merge that would need to
-- guess which source is "more complete."
-- disease_group='รวม' (all diseases combined) coexists with individual
-- disease groups for the same (province, year, sex) -- confirmed by
-- inspection (real case_count values, not a blank placeholder). Flagged.
CREATE TABLE `sick_298group_long` (
    `silver_id`     BIGINT AUTO_INCREMENT PRIMARY KEY,
    `year_be`         SMALLINT NOT NULL,
    `year_ce`          SMALLINT NOT NULL,
    `province`          VARCHAR(100) NOT NULL,
    `disease_group`       VARCHAR(300) NOT NULL,
    `sex`                   VARCHAR(10) NOT NULL,
    `case_count`             BIGINT,
    `is_aggregate_row`        TINYINT(1) NOT NULL DEFAULT 0,
    KEY `ix_s298l_province_year` (`province`, `year_ce`),
    KEY `ix_s298l_aggregate` (`is_aggregate_row`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `sick_298group_wide` (
    `silver_id`     BIGINT AUTO_INCREMENT PRIMARY KEY,
    `year_be`         SMALLINT NOT NULL,
    `year_ce`          SMALLINT NOT NULL,
    `province`          VARCHAR(100) NOT NULL,
    `disease_group`       VARCHAR(300) NOT NULL,
    `male_count`            BIGINT,
    `female_count`           BIGINT,
    `total_count`             BIGINT,
    `is_aggregate_row`         TINYINT(1) NOT NULL DEFAULT 0,
    KEY `ix_s298w_province_year` (`province`, `year_ce`),
    KEY `ix_s298w_aggregate` (`is_aggregate_row`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- UNION of the 2566/2567 bronze tables (differing column sets: 2566 has
-- a unit column and uses 'โรค'; 2567 drops the unit and uses 'ชื่อโรค').
CREATE TABLE `surveillance_top_diseases` (
    `silver_id`     BIGINT AUTO_INCREMENT PRIMARY KEY,
    `year_be`         SMALLINT NOT NULL,
    `year_ce`          SMALLINT NOT NULL,
    `disease_name`      VARCHAR(300) NOT NULL,
    `case_count`          BIGINT,
    `unit`                  VARCHAR(50) COMMENT 'NULL for the 2567 extract, which dropped this column',
    KEY `ix_std_year` (`year_ce`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- "รวมทั้งหมด (ยอดจริง)" grand-total row -- confirmed equal to the exact
-- sum of the other rows (55,054 for 2024), same defect class/same literal
-- figures as the pre-restart project's other_health_disease_cases fix.
CREATE TABLE `compare_cases_by_disease` (
    `silver_id`     BIGINT AUTO_INCREMENT PRIMARY KEY,
    `disease_name`    VARCHAR(300) NOT NULL,
    `count_2024`        BIGINT,
    `count_2025`          BIGINT,
    `diff`                  BIGINT,
    `is_aggregate_row`       TINYINT(1) NOT NULL DEFAULT 0,
    KEY `ix_ccbd_aggregate` (`is_aggregate_row`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `compare_cases_by_subdistrict` (
    `silver_id`     BIGINT AUTO_INCREMENT PRIMARY KEY,
    `district_name`   VARCHAR(100) NOT NULL,
    `subdistrict_name`  VARCHAR(100),
    `count_2024`          BIGINT,
    `count_2025`            BIGINT,
    `diff`                    BIGINT,
    `is_aggregate_row`         TINYINT(1) NOT NULL DEFAULT 0,
    KEY `ix_ccbs_aggregate` (`is_aggregate_row`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Unpivoted from the 5-year x 3-metric wide structure (confirmed by
-- inspection: row-5 sub-headers read จำนวน | อัตรา | ประชากรกลางปี for
-- every year).
-- province='รวม' (nationwide total, health_region NULL for these rows)
-- sits alongside real province rows -- same aggregate-row class.
CREATE TABLE `ncd_mortality_by_disease` (
    `silver_id`         BIGINT AUTO_INCREMENT PRIMARY KEY,
    `disease`             VARCHAR(100) NOT NULL COMMENT 'from source_sheet_name',
    `health_region`         VARCHAR(100),
    `province`                VARCHAR(100) NOT NULL,
    `year_ce`                  SMALLINT    NOT NULL,
    `death_count`                DECIMAL(15,2),
    `death_rate_per_100k`          DECIMAL(15,6),
    `mid_year_population`           DECIMAL(15,2),
    `is_aggregate_row`               TINYINT(1) NOT NULL DEFAULT 0,
    KEY `ix_nmbd_disease_year` (`disease`, `year_ce`),
    KEY `ix_nmbd_province` (`province`),
    KEY `ix_nmbd_aggregate` (`is_aggregate_row`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Checked for a merge with _no_rate (per plan) and found real divergence
-- (not just a join artifact): 3 of the 5 overlapping fiscal years have
-- IDENTICAL figures between _with_rate and _no_rate, but 2 years (BE2564,
-- BE2565) diverge wildly (e.g. BE2565 total: 692 in _with_rate vs. 9,388
-- in _no_rate for the same cause/province/year) -- a genuine source data
-- discrepancy, not something Silver can resolve by picking a "canonical"
-- side without the data owner's input. Kept separate rather than merged.
-- The csv/mojibake-xlsx PAIR within _with_rate itself IS a true exact
-- duplicate (confirmed at bronze time) -- deduped to the csv here.
CREATE TABLE `cause_of_death_top10_with_rate` (
    `silver_id`     BIGINT AUTO_INCREMENT PRIMARY KEY,
    `year_be`         SMALLINT NOT NULL,
    `year_ce`          SMALLINT NOT NULL,
    `province`           VARCHAR(100) NOT NULL,
    `cause_of_death`       VARCHAR(300) NOT NULL,
    `male_count`             BIGINT,
    `female_count`             BIGINT,
    `total_count`               BIGINT,
    `rate_per_100k`               DECIMAL(10,2),
    `unit`                          VARCHAR(100),
    `source_attribution`             VARCHAR(300),
    `is_aggregate_row`                TINYINT(1) NOT NULL DEFAULT 0,
    KEY `ix_cdwr_province_year` (`province`, `year_ce`),
    KEY `ix_cdwr_aggregate` (`is_aggregate_row`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `cause_of_death_top10_no_rate` (
    `silver_id`     BIGINT AUTO_INCREMENT PRIMARY KEY,
    `year_be`         SMALLINT NOT NULL,
    `year_ce`          SMALLINT NOT NULL,
    `province`           VARCHAR(100) NOT NULL,
    `cause_of_death`       VARCHAR(300) NOT NULL,
    `male_count`             BIGINT,
    `female_count`             BIGINT,
    `total_count`               BIGINT,
    `unit`                        VARCHAR(100),
    `source_attribution`            VARCHAR(300),
    `is_aggregate_row`               TINYINT(1) NOT NULL DEFAULT 0,
    KEY `ix_cdnr_province_year` (`province`, `year_ce`),
    KEY `ix_cdnr_aggregate` (`is_aggregate_row`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

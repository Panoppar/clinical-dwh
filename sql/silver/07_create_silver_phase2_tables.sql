-- ============================================================================
-- Silver layer DDL — Phase 2 shared-drive data (HDC/DDS health
-- surveillance, Lat Krabang points of interest, KMCH places, other
-- health/population tables). See docs/03_external_reference_sources.md
-- for provenance and the usage-rights note on HDC/DDS data.
--
-- hdc_occupational_health and dds_pdf_report_inventory are intentionally
-- NOT promoted to Silver this round — the former is a generic JSON API
-- cache with no stable schema worth typing yet, the latter is a document
-- inventory (filenames/hashes), not tabular content to cleanse. Both stay
-- Bronze-only; that's a legitimate Medallion outcome, not an oversight.
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `hdc_disease_pop_age`;
DROP TABLE IF EXISTS `hdc_disease_incidence`;
DROP TABLE IF EXISTS `hdc_disease_death_age`;
DROP TABLE IF EXISTS `dds_yearly_disease_ranking`;
DROP TABLE IF EXISTS `lat_krabang_population_by_subdistrict`;
DROP TABLE IF EXISTS `lat_krabang_deaths_by_subdistrict`;
DROP TABLE IF EXISTS `lat_krabang_points_of_interest`;
DROP TABLE IF EXISTS `kmch_catchment_places`;
DROP TABLE IF EXISTS `other_health_disease_cases`;
DROP TABLE IF EXISTS `other_health_subdistrict_cases`;
DROP TABLE IF EXISTS `other_health_sick_by_group`;
DROP TABLE IF EXISTS `other_health_disease_by_year`;

CREATE TABLE `hdc_disease_pop_age` (
  `disease` VARCHAR(30) NOT NULL, `province_code` VARCHAR(10), `hospcode` VARCHAR(20),
  `areacode` VARCHAR(20), `year_ce` INT, `pop_group1` INT, `result_group1` INT,
  `pop_group2` INT, `result_group2` INT, `pop_group3` INT, `result_group3` INT,
  `pop_group4` INT, `result_group4` INT, `pop_group5` INT, `result_group5` INT,
  KEY `ix_shdpa_disease` (`disease`), KEY `ix_shdpa_areacode` (`areacode`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `hdc_disease_incidence` (
  `disease` VARCHAR(30) NOT NULL, `province_code` VARCHAR(10), `hospcode` VARCHAR(20),
  `areacode` VARCHAR(20), `year_ce` INT, `target` INT, `result` INT,
  KEY `ix_shdi_disease` (`disease`), KEY `ix_shdi_areacode` (`areacode`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `hdc_disease_death_age` (
  `disease` VARCHAR(30) NOT NULL, `province_code` VARCHAR(10), `hospcode` VARCHAR(20),
  `areacode` VARCHAR(20), `year_ce` INT, `pt_group1` INT, `death_group1` INT,
  `pt_group2` INT, `death_group2` INT, `pt_group3` INT, `death_group3` INT,
  `pt_group4` INT, `death_group4` INT, `pt_group5` INT, `death_group5` INT,
  KEY `ix_shda_disease` (`disease`), KEY `ix_shda_areacode` (`areacode`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `dds_yearly_disease_ranking` (
  `province_code` VARCHAR(10), `province_name_th` VARCHAR(100), `year_ce` INT,
  `disease_th` VARCHAR(100), `case_count` INT, `case_fatality_pct` DECIMAL(6,2),
  `death_count` INT, `rate_per_100k` DECIMAL(10,2), `rank_by_cases` INT,
  `implied_population` DECIMAL(15,2), `is_provisional` TINYINT(1), `note` TEXT,
  KEY `ix_sdyr_province` (`province_code`), KEY `ix_sdyr_disease` (`disease_th`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Lat Krabang: population/deaths kept distinct (different grain, both
-- numeric time series); the nine POI-style tables (universities, schools,
-- hospitals, religious sites, risk points, businesses, vocational
-- colleges) are consolidated here since they all share the same shape --
-- "a named place in Lat Krabang with an address" -- with type-specific
-- extras (investment amount, student counts, risk flags) kept in a JSON
-- column rather than exploding into a dozen nullable columns no other
-- type uses.
-- Both source files include a "รวม" (Total) row alongside the real
-- subdistricts, pre-summed by the source -- excluded at transform time
-- (08_transform_silver_phase2.sql) or any SUM() over this table silently
-- doubles the true total.
CREATE TABLE `lat_krabang_population_by_subdistrict` (
  `subdistrict_name_th` VARCHAR(100) NOT NULL, `sex` VARCHAR(10) NOT NULL, `count` INT,
  KEY `ix_slkp_subdistrict` (`subdistrict_name_th`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `lat_krabang_deaths_by_subdistrict` (
  `subdistrict_name_th` VARCHAR(100) NOT NULL, `sex` VARCHAR(10) NOT NULL, `count` INT,
  KEY `ix_slkd_subdistrict` (`subdistrict_name_th`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `lat_krabang_points_of_interest` (
  `poi_type` VARCHAR(20) NOT NULL,   -- university | vocational_college | school | hospital | religious_site | risk_point | business
  `name_th` VARCHAR(300),
  `address_th` TEXT,
  `attributes` JSON,                  -- type-specific fields, e.g. {"student_num": 1059} or {"investment_thb": 39000000}
  `source_added_date` DATE,
  KEY `ix_slpoi_type` (`poi_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `kmch_catchment_places` (
  `category` VARCHAR(50), `place_name_th` VARCHAR(200), `place_name_en` VARCHAR(200),
  `address_th` TEXT, `subdistrict_th` VARCHAR(100), `district_th` VARCHAR(100), `province_th` VARCHAR(100),
  `avg_distance_km` DECIMAL(6,2), `avg_travel_time_mins` INT, `market_potential` VARCHAR(100),
  KEY `ix_skcp_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `other_health_disease_cases` (
  `disease_th` VARCHAR(200) NOT NULL, `count_2567` INT, `count_2568` INT, `diff` INT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `other_health_subdistrict_cases` (
  `district_th` VARCHAR(100), `subdistrict_th` VARCHAR(100),
  `count_2567` INT, `count_2568` INT, `diff` INT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `other_health_sick_by_group` (
  `year_ce` INT, `province_th` VARCHAR(100), `disease_group_th` VARCHAR(200),
  `sex` VARCHAR(10), `count` INT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `other_health_disease_by_year` (
  `year_ce` INT, `disease_th` VARCHAR(200), `count` INT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Gold layer DDL — HDC/DDS/Lat Krabang dashboard-ready tables.
--
-- RESTRICTED DATA NOTE: Fact_HDC_* and Fact_DDS_* are built from data whose
-- redistribution rights are NOT confirmed with the data owner (see
-- docs/03_external_reference_sources.md). Promoting to Gold makes it
-- visible to the local Metabase instance (metabase_ro, gold-only) for the
-- project owner's own dashboards. If this Metabase instance is ever shared
-- with anyone beyond the person who accepted that risk, these specific
-- tables/dashboards need a second look first.
--
-- Age group note: HDC's age_group1..5 are the source system's own
-- age-band codes. The source data does not document the actual numeric
-- age boundaries anywhere in this export, so they are labeled generically
-- ("Age Group 1".."Age Group 5") rather than guessing ranges.
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `Fact_HDC_Pop_Age`;
CREATE TABLE `Fact_HDC_Pop_Age` (
  `disease` VARCHAR(30) NOT NULL,
  `province_code` INT NULL, `province_name_en` VARCHAR(100) NULL,
  `year_ce` INT NOT NULL, `age_group` VARCHAR(20) NOT NULL,
  `population` BIGINT, `cases` BIGINT,
  KEY `ix_fhpa_disease` (`disease`), KEY `ix_fhpa_province` (`province_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `Fact_HDC_Incidence`;
CREATE TABLE `Fact_HDC_Incidence` (
  `disease` VARCHAR(30) NOT NULL,
  `province_code` INT NULL, `province_name_en` VARCHAR(100) NULL,
  `year_ce` INT NOT NULL,
  `target` BIGINT, `result` BIGINT, `achievement_rate_pct` DECIMAL(6,2),
  KEY `ix_fhi_disease` (`disease`), KEY `ix_fhi_province` (`province_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `Fact_HDC_Death_Age`;
CREATE TABLE `Fact_HDC_Death_Age` (
  `disease` VARCHAR(30) NOT NULL,
  `province_code` INT NULL, `province_name_en` VARCHAR(100) NULL,
  `year_ce` INT NOT NULL, `age_group` VARCHAR(20) NOT NULL,
  `person_time` BIGINT, `deaths` BIGINT,
  KEY `ix_fhda_disease` (`disease`), KEY `ix_fhda_province` (`province_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `Fact_DDS_Disease_Ranking`;
CREATE TABLE `Fact_DDS_Disease_Ranking` (
  `province_code` INT NULL, `province_name_en` VARCHAR(100) NULL, `province_name_th` VARCHAR(100) NULL,
  `year_ce` INT NOT NULL, `disease_th` VARCHAR(100) NOT NULL,
  `case_count` BIGINT, `case_fatality_pct` DECIMAL(6,2), `death_count` BIGINT,
  `rate_per_100k` DECIMAL(10,2), `rank_by_cases` INT, `is_provisional` TINYINT(1),
  -- 1 = rollup category that double-counts its own subtypes in this same
  -- list (e.g. "ไข้เลือดออกรวม" vs "ไข้เด็งกี" + "ไข้เลือดออก").
  -- Add `AND is_aggregate_row = 0` before any SUM(case_count) by province.
  `is_aggregate_row` TINYINT(1) NOT NULL DEFAULT 0,
  KEY `ix_fddr_province` (`province_code`), KEY `ix_fddr_disease` (`disease_th`),
  KEY `ix_fddr_aggregate` (`is_aggregate_row`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Lat Krabang: unrestricted, same governance status as the rest of Gold.
-- Source rows exclude the "รวม" (Total) row present in Silver's source
-- files -- it's a pre-summed row, not a real subdistrict, and would
-- double-count any SUM() over this table if left in.
DROP TABLE IF EXISTS `Fact_Lat_Krabang_Population`;
CREATE TABLE `Fact_Lat_Krabang_Population` (
  `subdistrict_name_th` VARCHAR(100) NOT NULL, `sex` VARCHAR(10) NOT NULL, `population` BIGINT,
  KEY `ix_flkp_subdistrict` (`subdistrict_name_th`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `Fact_Lat_Krabang_Deaths`;
CREATE TABLE `Fact_Lat_Krabang_Deaths` (
  `subdistrict_name_th` VARCHAR(100) NOT NULL, `sex` VARCHAR(10) NOT NULL, `deaths` BIGINT,
  KEY `ix_flkd_subdistrict` (`subdistrict_name_th`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `Dim_Lat_Krabang_POI`;
CREATE TABLE `Dim_Lat_Krabang_POI` (
  `poi_type` VARCHAR(20) NOT NULL, `name_th` VARCHAR(300),
  `investment_thb` DECIMAL(15,2) NULL, `student_num` INT NULL, `risk_type` VARCHAR(10) NULL,
  KEY `ix_dlkp_type` (`poi_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

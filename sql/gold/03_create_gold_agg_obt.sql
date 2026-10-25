-- ============================================================================
-- GOLD LAYER — aggregate / OBT tables, one per dashboard (see
-- Dashboard_Design tab), plus the Level-3 strategic composite index.
-- Built from the fact tables in 02_create_gold_facts.sql; column names
-- map directly to the KPI IDs in the KPI_Tree tab (K-ECO-*, K-DEM-*,
-- K-HLT-*, K-STR-*).
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `agg_economic_by_province_year`;
DROP TABLE IF EXISTS `agg_population_by_district_year`;
DROP TABLE IF EXISTS `agg_health_kpi_by_province_year`;
DROP TABLE IF EXISTS `obt_regional_composite_index`;

-- Dashboard 2: Economic & Industrial Development. One row per (province, year).
CREATE TABLE `agg_economic_by_province_year` (
    `agg_id`                        BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_name`                 VARCHAR(150) NOT NULL,
    `year_ce`                       SMALLINT     NOT NULL,
    `avg_monthly_income`            DECIMAL(18,2) COMMENT 'K-ECO-01',
    `regular_income_share`          DECIMAL(8,4)  COMMENT 'K-ECO-02',
    `factory_count`                 INT           COMMENT 'K-ECO-03 (snapshot, not year-specific -- DIW is a single current-state crawl)',
    `avg_factory_capital`           DECIMAL(18,2) COMMENT 'K-ECO-04',
    `avg_workers_per_factory`       DECIMAL(10,2) COMMENT 'K-ECO-05',
    `total_industrial_workforce`    BIGINT        COMMENT 'K-ECO-06',
    `income_to_capital_ratio`       DECIMAL(14,6) COMMENT 'K-ECO-08',
    UNIQUE KEY `ux_aepy_province_year` (`province_name`, `year_ce`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dashboard 3: Population & Community. One row per (district, fiscal_year).
CREATE TABLE `agg_population_by_district_year` (
    `agg_id`                 BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_name`          VARCHAR(150) NOT NULL,
    `district_name`          VARCHAR(150) NOT NULL,
    `fiscal_year_ce`         SMALLINT     NOT NULL,
    `total_population`       BIGINT        COMMENT 'K-DEM-01',
    `sex_ratio`              DECIMAL(10,4) COMMENT 'K-DEM-02, male/female',
    `community_count`        INT           COMMENT 'K-DEM-03 total',
    `crowded_population_share` DECIMAL(8,4) COMMENT 'K-DEM-04',
    `yoy_growth_rate`        DECIMAL(10,6) COMMENT 'K-DEM-05, NULL for the earliest year in range',
    UNIQUE KEY `ux_apdy_district_year` (`province_name`, `district_name`, `fiscal_year_ce`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dashboard 4: Public Health Surveillance. One row per (province, year) --
-- province resolved only for HDC records whose report layout carries a
-- resolvable area (fact_hdc_observation.geo_key IS NOT NULL); DDS columns
-- stay NULL across the board until that source recovers.
CREATE TABLE `agg_health_kpi_by_province_year` (
    `agg_id`                          BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_name`                   VARCHAR(150) NOT NULL,
    `year_ce`                         SMALLINT     NOT NULL,
    `avg_disease_incidence_rate`      DECIMAL(14,4) COMMENT 'K-HLT-01 (DDS, pending)',
    `avg_case_fatality_pct`           DECIMAL(8,4)  COMMENT 'K-HLT-02 (DDS, pending)',
    `avg_ncd_target_attainment`       DECIMAL(10,4) COMMENT 'K-HLT-03, result/target averaged across HDC reports',
    `avg_hdc_calculated_rate`         DECIMAL(14,4) COMMENT 'K-HLT-04, avg F3 across HDC reports',
    `occupational_report_count`       INT           COMMENT 'K-HLT-05',
    `air_pollution_report_count`      INT           COMMENT 'K-HLT-06',
    `surveillance_completeness_pct`   DECIMAL(8,4)  COMMENT 'K-HLT-09',
    UNIQUE KEY `ux_ahky_province_year` (`province_name`, `year_ce`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dashboard 1: Executive Overview. One row per province, Level-3 KPIs
-- (K-STR-01/02/03), normalized 0-100 so they're comparable on one gauge
-- scale. Built from the 3 agg_ tables above.
CREATE TABLE `obt_regional_composite_index` (
    `obt_id`                                BIGINT AUTO_INCREMENT PRIMARY KEY,
    `province_name`                         VARCHAR(150) NOT NULL,
    `year_ce`                               SMALLINT     NOT NULL,
    `socioeconomic_health_vulnerability_index` DECIMAL(6,2) COMMENT 'K-STR-01, 0-100, higher = more vulnerable',
    `industrial_health_impact_index`           DECIMAL(6,2) COMMENT 'K-STR-02, 0-100, higher = more impact',
    `catchment_economic_vitality_score`        DECIMAL(6,2) COMMENT 'K-STR-03, 0-100, higher = more vitality',
    UNIQUE KEY `ux_orci_province_year` (`province_name`, `year_ce`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

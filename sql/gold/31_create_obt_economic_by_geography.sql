-- ============================================================================
-- GOLD LAYER — obt_economic_by_geography
-- One denormalized row per entity (factory registration or catchment
-- place) for Metabase -- zero joins, zero runtime math. Combines both
-- fact tables via UNION ALL (not a join), same reasoning as Stage 2's
-- disease OBT: fact_factory_registration has a real date dimension
-- (permit year) and fact_catchment_place doesn't (these local-area
-- sources are point-in-time snapshots, not a time series) -- each side
-- populates what it has.
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `obt_economic_by_geography`;

CREATE TABLE `obt_economic_by_geography` (
    `obt_key`                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `geo_key`                    INT UNSIGNED NULL,
    `date_key`                     INT          NULL COMMENT 'NULL for catchment-place rows -- no time dimension',
    `province_name_th`               VARCHAR(150),
    `district_name_th`                 VARCHAR(150),
    `subdistrict_name_th`                VARCHAR(150),
    `entity_name`                          VARCHAR(500) NOT NULL,
    `entity_type`                            VARCHAR(30)  NOT NULL COMMENT 'factory | kmch | business | religious | safety_risk | edu_school | edu_university | edu_vocational | hospital',
    `total_investment`                        DECIMAL(20,2) NULL COMMENT 'factory (THB) or business_establishment (investment_thb)',
    `total_workers`                              INT NULL,
    `male_workers`                                 INT NULL,
    `female_workers`                                 INT NULL,
    `total_horsepower`                                 DECIMAL(20,2) NULL,
    `avg_distance_km`                                    DECIMAL(10,2) NULL COMMENT 'kmch',
    `market_potential`                                     VARCHAR(255) NULL COMMENT 'kmch',
    `student_count`                                          INT NULL COMMENT 'edu_school',
    `source_system`                                            VARCHAR(20) NOT NULL,
    KEY `ix_oebg_geo_date` (`geo_key`, `date_key`),
    KEY `ix_oebg_entity_type` (`entity_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

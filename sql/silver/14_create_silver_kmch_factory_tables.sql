-- ============================================================================
-- SILVER LAYER — KMCH catchment places + Factory list
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `kmch_catchment_places`;
DROP TABLE IF EXISTS `factory_list`;

CREATE TABLE `kmch_catchment_places` (
    `silver_id`          BIGINT AUTO_INCREMENT PRIMARY KEY,
    `category`             VARCHAR(100),
    `place_name_th`          VARCHAR(500),
    `place_name_en`            VARCHAR(500),
    `address`                    VARCHAR(500),
    `sub_district`                 VARCHAR(255),
    `district`                       VARCHAR(255),
    `province`                         VARCHAR(255),
    `avg_distance_km`                   DECIMAL(10,2),
    `avg_travel_time_mins`                INT,
    `market_potential`                      VARCHAR(255),
    KEY `ix_kcp_category` (`category`),
    KEY `ix_kcp_district` (`district`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `factory_list` (
    `silver_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
    `factory_reg_no`          VARCHAR(50),
    `factory_fid`               VARCHAR(50),
    `tsic_code`                   VARCHAR(20),
    `factory_type_code`             VARCHAR(20),
    `factory_type_desc`               TEXT,
    `category`                          VARCHAR(50),
    `class`                                TINYINT,
    `permit_year_be`                         SMALLINT,
    `permit_year_ce`                           SMALLINT,
    `factory_name`                                VARCHAR(500),
    `owner_name`                                    VARCHAR(500),
    `business_activity`                               TEXT,
    `address_no`                                        VARCHAR(100),
    `moo`                                                  VARCHAR(50),
    `soi`                                                    VARCHAR(255),
    `road`                                                    VARCHAR(255),
    `sub_district`                                              VARCHAR(255),
    `district`                                                    VARCHAR(255),
    `province_code`                                                 VARCHAR(20),
    `province`                                                        VARCHAR(255),
    `postal_code`                                                       VARCHAR(20),
    `phone`                                                               VARCHAR(100),
    `building_value`                                                       DECIMAL(20,2),
    `land_value`                                                             DECIMAL(20,2),
    `machinery_value`                                                          DECIMAL(20,2),
    `working_capital`                                                            DECIMAL(20,2),
    `total_investment`                                                             DECIMAL(20,2),
    `male_workers`                                                                   INT,
    `female_workers`                                                                   INT,
    `total_workers`                                                                      INT,
    `total_horsepower`                                                                     DECIMAL(20,2),
    `factory_area_sqm`                                                                       DECIMAL(20,2),
    `building_area_sqm`                                                                        DECIMAL(20,2),
    KEY `ix_fl_year` (`permit_year_ce`),
    KEY `ix_fl_province` (`province`),
    KEY `ix_fl_tsic` (`tsic_code`),
    KEY `ix_fl_reg_no` (`factory_reg_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

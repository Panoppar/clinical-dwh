-- ============================================================================
-- GOLD LAYER — fact_catchment_place
-- Grain: one row per dim_place row. Generic measure slots shared across
-- 8 heterogeneous local-area sources, same pattern as
-- fact_disease_event -- each source populates the columns it has and
-- leaves the rest NULL.
--
-- geo_key only resolves for 1 of the 8 sources: kmch_catchment_places
-- has structured (district, sub_district) text (compound-matched the
-- same way as fact_factory_registration). The other 7 sources (business,
-- religious, safety_risk, edu_*, hospital) have either just a free-text
-- address or -- confirmed by inspection -- no geography column survived
-- their Bronze->Silver transform at all (safety_risk_point's bronze
-- table has a district column; silver's doesn't) -- geo_key stays NULL
-- rather than guessed from address text.
--
-- risk_flag_1..6 are safety_risk_point's r1-r6 columns, confirmed
-- binary (0/1) by inspection but with no surviving documentation of
-- what each specific flag represents -- kept as opaque flags rather
-- than guessing labels.
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `fact_catchment_place`;

CREATE TABLE `fact_catchment_place` (
    `fact_key`                 BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `place_key`                  INT UNSIGNED NOT NULL,
    `geo_key`                      INT UNSIGNED NULL,
    `investment_thb`                 DECIMAL(20,2) NULL COMMENT 'business_establishment',
    `avg_distance_km`                  DECIMAL(10,2) NULL COMMENT 'kmch',
    `avg_travel_time_mins`                INT NULL COMMENT 'kmch',
    `market_potential`                      VARCHAR(255) NULL COMMENT 'kmch',
    `student_count`                           INT NULL COMMENT 'edu_school',
    `classroom_count`                           INT NULL COMMENT 'edu_school',
    `teacher_count`                               INT NULL COMMENT 'edu_school',
    `student_m6_count`                             INT NULL COMMENT 'edu_school',
    `student_p3_count`                               INT NULL COMMENT 'edu_school',
    `risk_flag_1`                                      TINYINT NULL COMMENT 'safety_risk_point r1-r6, meaning undocumented',
    `risk_flag_2`                                        TINYINT NULL,
    `risk_flag_3`                                          TINYINT NULL,
    `risk_flag_4`                                            TINYINT NULL,
    `risk_flag_5`                                              TINYINT NULL,
    `risk_flag_6`                                                TINYINT NULL,
    KEY `ix_fcp_place` (`place_key`),
    KEY `ix_fcp_geo` (`geo_key`),
    CONSTRAINT `fk_fcp_place` FOREIGN KEY (`place_key`) REFERENCES `dim_place` (`place_key`),
    CONSTRAINT `fk_fcp_geo` FOREIGN KEY (`geo_key`) REFERENCES `dim_geography` (`geo_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

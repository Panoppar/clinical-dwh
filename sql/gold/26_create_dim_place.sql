-- ============================================================================
-- GOLD LAYER — dim_place
-- Generic place dimension covering 8 KMCH-catchment local-area sources,
-- each describing individual places rather than aggregated counts
-- (community_count_by_district_bkk, foreign_labor_permit_by_area_bkk,
-- and labor_force_survey are district/area-level aggregates, not
-- individual places -- out of scope for this place-grained dimension,
-- left available in Silver for a future Gold extension).
-- place_type is source-specific: kmch's own category taxonomy for kmch,
-- business_type for business, risk_type for safety_risk, and a fixed
-- label for the sources with no type column of their own.
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `dim_place`;

CREATE TABLE `dim_place` (
    `place_key`     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `source_system`   VARCHAR(30)  NOT NULL COMMENT 'kmch | business | religious | safety_risk | edu_school | edu_university | edu_vocational | hospital',
    `place_type`        VARCHAR(100),
    `place_name`           VARCHAR(500) NOT NULL,
    `address`                VARCHAR(1000),
    `silver_id`                BIGINT NOT NULL COMMENT 'traceability back to the source Silver row',
    UNIQUE KEY `ux_dp_source_silver` (`source_system`, `silver_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `dim_place` (source_system, place_type, place_name, address, silver_id)
SELECT 'kmch', category, place_name_th, address, silver_id FROM silver.kmch_catchment_places
UNION ALL
SELECT 'business', business_type, business_name, address, silver_id FROM silver.business_establishment
UNION ALL
SELECT 'religious', 'religious_site', site_name, address, silver_id FROM silver.religious_site
UNION ALL
SELECT 'safety_risk', risk_type, risk_name, NULL, silver_id FROM silver.safety_risk_point
UNION ALL
SELECT 'edu_school', 'school', school_name, NULL, silver_id FROM silver.edu_school
UNION ALL
SELECT 'edu_university', 'university', university_name, address, silver_id FROM silver.edu_university
UNION ALL
SELECT 'edu_vocational', 'vocational_college', college_name, address, silver_id FROM silver.edu_vocational_college
UNION ALL
SELECT 'hospital', 'hospital', hospital_name, address, silver_id FROM silver.health_hospital;

SET FOREIGN_KEY_CHECKS = 1;

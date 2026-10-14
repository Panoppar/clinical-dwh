-- ============================================================================
-- SILVER LAYER — Lat Krabang district office tables
-- (community table stays excluded entirely -- PII, see bronze.community's
-- comment and extract_load_lat_krabang.py's docstring)
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `edu_vocational_college`;
DROP TABLE IF EXISTS `edu_university`;
DROP TABLE IF EXISTS `edu_school`;
DROP TABLE IF EXISTS `health_hospital`;
DROP TABLE IF EXISTS `religious_site`;
DROP TABLE IF EXISTS `business_establishment`;
DROP TABLE IF EXISTS `safety_risk_point`;
DROP TABLE IF EXISTS `lat_krabang_population_by_subdistrict`;
DROP TABLE IF EXISTS `lat_krabang_deaths_by_subdistrict`;

CREATE TABLE `edu_vocational_college` (
    `silver_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `college_name` VARCHAR(500), `address` VARCHAR(1000), `remark` VARCHAR(1000)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `edu_university` (
    `silver_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `university_name` VARCHAR(500), `address` VARCHAR(1000), `remark` VARCHAR(1000)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `edu_school` (
    `silver_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `school_name` VARCHAR(500), `student_count` INT, `classroom_count` INT,
    `teacher_count` INT, `student_m6_count` INT, `student_p3_count` INT, `remark` VARCHAR(1000)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `health_hospital` (
    `silver_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `hospital_name` VARCHAR(500), `address` VARCHAR(1000), `remark` VARCHAR(1000)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `religious_site` (
    `silver_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `site_name` VARCHAR(500), `address` VARCHAR(1000), `remark` VARCHAR(1000)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `business_establishment` (
    `silver_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `business_name` VARCHAR(500), `business_type` VARCHAR(50), `investment_thb` DECIMAL(20,2),
    `address` VARCHAR(1000), `remark` VARCHAR(1000)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `safety_risk_point` (
    `silver_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `risk_name` VARCHAR(500), `risk_type` VARCHAR(50),
    `r1` VARCHAR(10), `r2` VARCHAR(10), `r3` VARCHAR(10), `r4` VARCHAR(10), `r5` VARCHAR(10), `r6` VARCHAR(10),
    `remark` VARCHAR(1000)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- "รวม" (district-wide total) row confirmed by inspection to equal the
-- exact sum of the 6 real subdistrict rows (84,355 = 14,116+31,576+...) --
-- excluded, same precedent as this project's pre-restart Lat Krabang fix.
CREATE TABLE `lat_krabang_population_by_subdistrict` (
    `silver_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `subdistrict_name` VARCHAR(100) NOT NULL,
    `male_count` BIGINT, `female_count` BIGINT, `total_count` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `lat_krabang_deaths_by_subdistrict` (
    `silver_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `subdistrict_name` VARCHAR(100) NOT NULL,
    `male_count` BIGINT, `female_count` BIGINT, `total_count` BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

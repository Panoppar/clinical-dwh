-- ============================================================================
-- Gold layer DDL — Dimension tables.
-- See docs/02_data_dictionary.md for the full design rationale and ERD.
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `Fact_Vaccination`;
DROP TABLE IF EXISTS `Fact_Screening_Response`;
DROP TABLE IF EXISTS `Fact_Patient_Registration`;
DROP TABLE IF EXISTS `Dim_Vaccine_Lot`;
DROP TABLE IF EXISTS `Dim_Vaccine`;
DROP TABLE IF EXISTS `Dim_Question`;
DROP TABLE IF EXISTS `Dim_Company`;
DROP TABLE IF EXISTS `Dim_Patient`;
DROP TABLE IF EXISTS `Dim_Date`;

CREATE TABLE `Dim_Date` (
  `date_key`      INT NOT NULL,                 -- YYYYMMDD
  `full_date`     DATE NOT NULL,
  `year`          SMALLINT NOT NULL,
  `quarter`       TINYINT NOT NULL,
  `month`         TINYINT NOT NULL,
  `month_name`    VARCHAR(20) NOT NULL,
  `day`           TINYINT NOT NULL,
  `day_of_week`   TINYINT NOT NULL,              -- 1=Mon .. 7=Sun (ISO)
  `day_name`      VARCHAR(20) NOT NULL,
  `is_weekend`    TINYINT(1) NOT NULL,
  `week_of_year`  TINYINT NOT NULL,
  PRIMARY KEY (`date_key`),
  UNIQUE KEY `uq_dim_date_full_date` (`full_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Dim_Patient` (
  `patient_sk`              INT NOT NULL AUTO_INCREMENT,
  `patient_id`               INT NOT NULL,
  `document_type`            VARCHAR(20) NOT NULL,
  `patient_type_code`        VARCHAR(30) NOT NULL,
  `patient_type_desc`        VARCHAR(50) NOT NULL,
  `sex`                      VARCHAR(10) NOT NULL,
  `age`                      INT NULL,
  `age_band`                 VARCHAR(10) NOT NULL,
  `has_underlying_disease`   TINYINT(1) NOT NULL,
  `is_deleted`                TINYINT(1) NOT NULL,
  `source_created_at`         DATETIME NOT NULL,
  `zip_code`                  VARCHAR(9) NULL,     -- postal code only (no street address) for geographic KPIs
  `district_code`             INT NULL,            -- resolved via silver.zip_code_primary_district; NULL if zip unmatched/invalid
  `district_name_en`          VARCHAR(100) NULL,
  `province_code`             INT NULL,
  `province_name_en`          VARCHAR(100) NULL,
  `is_geo_ambiguous`          TINYINT(1) NULL,      -- 1 if zip_code spans >1 district (district above is the most-likely pick, not certain)
  PRIMARY KEY (`patient_sk`),
  UNIQUE KEY `uq_dim_patient_patient_id` (`patient_id`),
  KEY `ix_dim_patient_zip_code` (`zip_code`),
  KEY `ix_dim_patient_district_code` (`district_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Dim_Company` (
  `company_sk`    INT NOT NULL,                 -- -1 = Not Applicable member
  `company_id`    INT NULL,                      -- NULL only for the -1 N/A row
  `company_name`  VARCHAR(255) NOT NULL,
  `is_active`     TINYINT(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`company_sk`),
  UNIQUE KEY `uq_dim_company_company_id` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Dim_Question` (
  `question_sk`        INT NOT NULL AUTO_INCREMENT,
  `question_id`        INT NOT NULL,
  `question_text_th`   TEXT NULL,
  `question_text_en`   TEXT NULL,
  `is_active`          TINYINT(1) NOT NULL,
  `display_order`      INT NOT NULL,
  PRIMARY KEY (`question_sk`),
  UNIQUE KEY `uq_dim_question_question_id` (`question_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Dim_Vaccine` (
  `vaccine_sk`     INT NOT NULL AUTO_INCREMENT,
  `vaccine_id`     INT NOT NULL,
  `vaccine_name`   VARCHAR(150) NOT NULL,
  PRIMARY KEY (`vaccine_sk`),
  UNIQUE KEY `uq_dim_vaccine_vaccine_id` (`vaccine_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Dim_Vaccine_Lot` (
  `lot_sk`               INT NOT NULL AUTO_INCREMENT,
  `lot_id`               INT NOT NULL,
  `vaccine_sk`           INT NOT NULL,
  `lot_number`           VARCHAR(100) NOT NULL,
  `initial_quantity`     INT NOT NULL,
  `remaining_quantity`   INT NOT NULL,
  `doses_administered`   INT NOT NULL,
  `utilization_rate`     DECIMAL(5,2) NOT NULL,
  PRIMARY KEY (`lot_sk`),
  UNIQUE KEY `uq_dim_vaccine_lot_lot_id` (`lot_id`),
  KEY `ix_dim_vaccine_lot_vaccine_sk` (`vaccine_sk`),
  CONSTRAINT `fk_dim_vaccine_lot_vaccine` FOREIGN KEY (`vaccine_sk`) REFERENCES `Dim_Vaccine` (`vaccine_sk`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

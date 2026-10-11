-- ============================================================================
-- Gold layer DDL — Fact tables.
-- Run AFTER 01_create_gold_dimensions.sql.
-- ============================================================================

USE gold;

CREATE TABLE `Fact_Patient_Registration` (
  `registration_sk`     INT NOT NULL AUTO_INCREMENT,
  `date_key`             INT NOT NULL,
  `patient_sk`           INT NOT NULL,
  `company_sk`           INT NOT NULL,
  `registration_count`   TINYINT(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`registration_sk`),
  UNIQUE KEY `uq_fact_patient_registration_patient` (`patient_sk`),
  KEY `ix_fpr_date_key` (`date_key`),
  KEY `ix_fpr_company_sk` (`company_sk`),
  CONSTRAINT `fk_fpr_date` FOREIGN KEY (`date_key`) REFERENCES `Dim_Date` (`date_key`),
  CONSTRAINT `fk_fpr_patient` FOREIGN KEY (`patient_sk`) REFERENCES `Dim_Patient` (`patient_sk`),
  CONSTRAINT `fk_fpr_company` FOREIGN KEY (`company_sk`) REFERENCES `Dim_Company` (`company_sk`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Fact_Screening_Response` (
  `screening_response_sk`   INT NOT NULL AUTO_INCREMENT,
  `date_key`                  INT NOT NULL,
  `patient_sk`                 INT NOT NULL,
  `company_sk`                 INT NOT NULL,
  `question_sk`                INT NOT NULL,
  `record_id`                  INT NOT NULL,       -- degenerate dimension (screening visit)
  `is_flagged`                 TINYINT(1) NOT NULL,
  `response_count`             TINYINT(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`screening_response_sk`),
  KEY `ix_fsr_date_key` (`date_key`),
  KEY `ix_fsr_patient_sk` (`patient_sk`),
  KEY `ix_fsr_company_sk` (`company_sk`),
  KEY `ix_fsr_question_sk` (`question_sk`),
  KEY `ix_fsr_record_id` (`record_id`),
  CONSTRAINT `fk_fsr_date` FOREIGN KEY (`date_key`) REFERENCES `Dim_Date` (`date_key`),
  CONSTRAINT `fk_fsr_patient` FOREIGN KEY (`patient_sk`) REFERENCES `Dim_Patient` (`patient_sk`),
  CONSTRAINT `fk_fsr_company` FOREIGN KEY (`company_sk`) REFERENCES `Dim_Company` (`company_sk`),
  CONSTRAINT `fk_fsr_question` FOREIGN KEY (`question_sk`) REFERENCES `Dim_Question` (`question_sk`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Fact_Vaccination` (
  `vaccination_sk`    INT NOT NULL AUTO_INCREMENT,
  `date_key`            INT NOT NULL,
  `patient_sk`           INT NOT NULL,
  `company_sk`           INT NOT NULL,
  `vaccine_sk`           INT NOT NULL,
  `lot_sk`               INT NOT NULL,
  `vaccination_id`       INT NOT NULL,
  `dose_count`           TINYINT(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`vaccination_sk`),
  UNIQUE KEY `uq_fact_vaccination_vaccination_id` (`vaccination_id`),
  KEY `ix_fv_date_key` (`date_key`),
  KEY `ix_fv_patient_sk` (`patient_sk`),
  KEY `ix_fv_company_sk` (`company_sk`),
  KEY `ix_fv_vaccine_sk` (`vaccine_sk`),
  KEY `ix_fv_lot_sk` (`lot_sk`),
  CONSTRAINT `fk_fv_date` FOREIGN KEY (`date_key`) REFERENCES `Dim_Date` (`date_key`),
  CONSTRAINT `fk_fv_patient` FOREIGN KEY (`patient_sk`) REFERENCES `Dim_Patient` (`patient_sk`),
  CONSTRAINT `fk_fv_company` FOREIGN KEY (`company_sk`) REFERENCES `Dim_Company` (`company_sk`),
  CONSTRAINT `fk_fv_vaccine` FOREIGN KEY (`vaccine_sk`) REFERENCES `Dim_Vaccine` (`vaccine_sk`),
  CONSTRAINT `fk_fv_lot` FOREIGN KEY (`lot_sk`) REFERENCES `Dim_Vaccine_Lot` (`lot_sk`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

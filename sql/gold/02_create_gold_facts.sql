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

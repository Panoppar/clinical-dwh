-- ============================================================================
-- Silver layer DDL — cleansed, conformed, constrained entity tables.
-- One Silver table per source business entity (not yet denormalized for BI
-- — that happens in Gold). Proper PK/FK constraints restored here since by
-- this point data has been deduplicated and typed.
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `screening_answer`;
DROP TABLE IF EXISTS `vaccination_record`;
DROP TABLE IF EXISTS `screening_record`;
DROP TABLE IF EXISTS `vaccine_lot`;
DROP TABLE IF EXISTS `company_employee`;
DROP TABLE IF EXISTS `employee`;
DROP TABLE IF EXISTS `student`;
DROP TABLE IF EXISTS `external_person`;
DROP TABLE IF EXISTS `contact`;
DROP TABLE IF EXISTS `patient`;
DROP TABLE IF EXISTS `screening_question`;
DROP TABLE IF EXISTS `vaccine`;
DROP TABLE IF EXISTS `company`;

CREATE TABLE `company` (
  `company_id` INT NOT NULL,
  `company_name` VARCHAR(255) NOT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL,
  `updated_at` DATETIME NULL,
  PRIMARY KEY (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `patient` (
  `patient_id` INT NOT NULL,
  `document_type` VARCHAR(20) NOT NULL,          -- ID_CARD | PASSPORT | UNKNOWN
  `id_card` VARCHAR(13) NULL,
  `passport_id` VARCHAR(50) NULL,
  `line_id` VARCHAR(100) NULL,
  `patient_type_code` VARCHAR(30) NOT NULL,      -- employee | student | company_employee | external | unknown
  `sex` VARCHAR(10) NOT NULL,                     -- male | female | unknown
  `prefix` VARCHAR(30) NULL,
  `first_name` VARCHAR(100) NOT NULL,
  `last_name` VARCHAR(100) NOT NULL,
  `full_name` VARCHAR(210) NOT NULL,
  `tel_no` VARCHAR(20) NOT NULL,
  `email` VARCHAR(255) NULL,
  `underlying_disease` TEXT NULL,
  `has_underlying_disease` TINYINT(1) NOT NULL DEFAULT 0,
  `age` INT NULL,                                 -- NULL if source value outside [0,120]
  `address` TEXT NULL,
  `zip_code` VARCHAR(9) NULL,
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL,
  `updated_at` DATETIME NULL,
  PRIMARY KEY (`patient_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `contact` (
  `contact_id` INT NOT NULL,
  `company_id` INT NOT NULL,
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL,
  `updated_at` DATETIME NULL,
  PRIMARY KEY (`contact_id`),
  KEY `ix_contact_company_id` (`company_id`),
  CONSTRAINT `fk_contact_company` FOREIGN KEY (`company_id`) REFERENCES `company` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `external_person` (
  `external_id` INT NOT NULL,
  `patient_id` INT NOT NULL,
  `created_at` DATETIME NOT NULL,
  PRIMARY KEY (`external_id`),
  UNIQUE KEY `uq_external_person_patient_id` (`patient_id`),
  CONSTRAINT `fk_external_person_patient` FOREIGN KEY (`patient_id`) REFERENCES `patient` (`patient_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `student` (
  `student_id` INT NOT NULL,
  `patient_id` INT NOT NULL,
  `created_at` DATETIME NOT NULL,
  PRIMARY KEY (`student_id`),
  UNIQUE KEY `uq_student_patient_id` (`patient_id`),
  CONSTRAINT `fk_student_patient` FOREIGN KEY (`patient_id`) REFERENCES `patient` (`patient_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `employee` (
  `employee_id` VARCHAR(20) NOT NULL,
  `patient_id` INT NOT NULL,
  `created_at` DATETIME NOT NULL,
  PRIMARY KEY (`employee_id`),
  UNIQUE KEY `uq_employee_patient_id` (`patient_id`),
  CONSTRAINT `fk_employee_patient` FOREIGN KEY (`patient_id`) REFERENCES `patient` (`patient_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `company_employee` (
  `employee_id` VARCHAR(20) NOT NULL,
  `company_id` INT NOT NULL,
  `patient_id` INT NOT NULL,
  `created_at` DATETIME NOT NULL,
  PRIMARY KEY (`employee_id`),
  UNIQUE KEY `uq_company_employee_patient_id` (`patient_id`),
  KEY `ix_company_employee_company_id` (`company_id`),
  CONSTRAINT `fk_company_employee_patient` FOREIGN KEY (`patient_id`) REFERENCES `patient` (`patient_id`),
  CONSTRAINT `fk_company_employee_company` FOREIGN KEY (`company_id`) REFERENCES `company` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `screening_question` (
  `question_id` INT NOT NULL,
  `question_text_th` TEXT NULL,
  `question_text_en` TEXT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `display_order` INT NOT NULL DEFAULT 0,
  PRIMARY KEY (`question_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `screening_record` (
  `record_id` INT NOT NULL,
  `patient_id` INT NOT NULL,
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL,
  PRIMARY KEY (`record_id`),
  KEY `ix_screening_record_patient_id` (`patient_id`),
  CONSTRAINT `fk_screening_record_patient` FOREIGN KEY (`patient_id`) REFERENCES `patient` (`patient_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `screening_answer` (
  `record_id` INT NOT NULL,
  `question_id` INT NOT NULL,
  `answer_flag` TINYINT(1) NOT NULL,
  `remark` TEXT NULL,
  `created_at` DATETIME NOT NULL,
  PRIMARY KEY (`record_id`, `question_id`),
  KEY `ix_screening_answer_question_id` (`question_id`),
  CONSTRAINT `fk_screening_answer_record` FOREIGN KEY (`record_id`) REFERENCES `screening_record` (`record_id`),
  CONSTRAINT `fk_screening_answer_question` FOREIGN KEY (`question_id`) REFERENCES `screening_question` (`question_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `vaccine` (
  `vaccine_id` INT NOT NULL,
  `vaccine_name` VARCHAR(150) NOT NULL,
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL,
  PRIMARY KEY (`vaccine_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `vaccine_lot` (
  `lot_id` INT NOT NULL,
  `vaccine_id` INT NOT NULL,
  `lot_number` VARCHAR(100) NOT NULL,
  `initial_quantity` INT NOT NULL,
  `remaining_quantity` INT NOT NULL,
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL,
  PRIMARY KEY (`lot_id`),
  KEY `ix_vaccine_lot_vaccine_id` (`vaccine_id`),
  CONSTRAINT `fk_vaccine_lot_vaccine` FOREIGN KEY (`vaccine_id`) REFERENCES `vaccine` (`vaccine_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `vaccination_record` (
  `vaccination_id` INT NOT NULL,
  `patient_id` INT NOT NULL,
  `lot_id` INT NOT NULL,
  `shot_date` DATETIME NOT NULL,
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL,
  PRIMARY KEY (`vaccination_id`),
  KEY `ix_vaccination_record_patient_id` (`patient_id`),
  KEY `ix_vaccination_record_lot_id` (`lot_id`),
  CONSTRAINT `fk_vaccination_record_patient` FOREIGN KEY (`patient_id`) REFERENCES `patient` (`patient_id`),
  CONSTRAINT `fk_vaccination_record_lot` FOREIGN KEY (`lot_id`) REFERENCES `vaccine_lot` (`lot_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

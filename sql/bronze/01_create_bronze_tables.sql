-- ============================================================================
-- Bronze layer DDL — raw, untransformed 1:1 replicas of every source table.
--
-- Rules for Bronze:
--   * Column names/types mirror the source exactly.
--   * All columns are NULLable (raw landing must never reject a row).
--   * No FK constraints (source referential integrity is not guaranteed to
--     land in dependency order during a parallel extract).
--   * Natural PK is kept as a plain column (`*_pk_hint`) for dedupe logic in
--     Silver, but is NOT declared PRIMARY KEY here, since Bronze is
--     truncate-and-reload on every run and must tolerate raw duplicates.
--   * Every table gets two lineage columns: `_bronze_loaded_at` and
--     `_source_system`, appended by the Python extractor at load time.
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `Company`;
CREATE TABLE `Company` (
  `company_id` INT,
  `company_name` VARCHAR(255),
  `created_at` TIMESTAMP NULL,
  `created_by` VARCHAR(100),
  `updated_at` TIMESTAMP NULL,
  `updated_by` VARCHAR(100),
  `deleted_at` TIMESTAMP NULL,
  `deleted_by` VARCHAR(100),
  `_bronze_loaded_at` TIMESTAMP NULL,
  `_source_system` VARCHAR(50),
  KEY `ix_company_id` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `Company_Employee`;
CREATE TABLE `Company_Employee` (
  `employee_id` VARCHAR(20),
  `company_id` INT,
  `patient_id` INT,
  `created_at` TIMESTAMP NULL,
  `created_by` VARCHAR(100),
  `updated_at` TIMESTAMP NULL,
  `updated_by` VARCHAR(100),
  `deleted_at` TIMESTAMP NULL,
  `deleted_by` VARCHAR(100),
  `_bronze_loaded_at` TIMESTAMP NULL,
  `_source_system` VARCHAR(50),
  KEY `ix_company_employee_patient_id` (`patient_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `Contact`;
CREATE TABLE `Contact` (
  `contact_id` INT,
  `company_id` INT,
  `created_at` TIMESTAMP NULL,
  `created_by` VARCHAR(100),
  `updated_at` TIMESTAMP NULL,
  `updated_by` VARCHAR(100),
  `deleted_at` TIMESTAMP NULL,
  `deleted_by` VARCHAR(100),
  `_bronze_loaded_at` TIMESTAMP NULL,
  `_source_system` VARCHAR(50),
  KEY `ix_contact_company_id` (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `Employee`;
CREATE TABLE `Employee` (
  `employee_id` VARCHAR(20),
  `patient_id` INT,
  `created_at` TIMESTAMP NULL,
  `created_by` VARCHAR(100),
  `updated_at` TIMESTAMP NULL,
  `updated_by` VARCHAR(100),
  `deleted_at` TIMESTAMP NULL,
  `deleted_by` VARCHAR(100),
  `_bronze_loaded_at` TIMESTAMP NULL,
  `_source_system` VARCHAR(50),
  KEY `ix_employee_patient_id` (`patient_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `External_Person`;
CREATE TABLE `External_Person` (
  `external_id` INT,
  `patient_id` INT,
  `created_at` TIMESTAMP NULL,
  `created_by` VARCHAR(100),
  `updated_at` TIMESTAMP NULL,
  `updated_by` VARCHAR(100),
  `deleted_at` TIMESTAMP NULL,
  `deleted_by` VARCHAR(100),
  `_bronze_loaded_at` TIMESTAMP NULL,
  `_source_system` VARCHAR(50),
  KEY `ix_external_person_patient_id` (`patient_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `Patient`;
CREATE TABLE `Patient` (
  `patient_id` INT,
  `document_type` VARCHAR(20),
  `id_card` VARCHAR(13),
  `passport_id` VARCHAR(50),
  `line_id` VARCHAR(100),
  `patient_type` VARCHAR(30),
  `sex` VARCHAR(10),
  `prefix` VARCHAR(30),
  `first_name` VARCHAR(100),
  `last_name` VARCHAR(100),
  `tel_no` VARCHAR(20),
  `email` VARCHAR(255),
  `underlying_disease` TEXT,
  `age` INT,
  `address` TEXT,
  `zip_code` VARCHAR(9),
  `created_at` TIMESTAMP NULL,
  `created_by` VARCHAR(100),
  `updated_at` TIMESTAMP NULL,
  `updated_by` VARCHAR(100),
  `deleted_at` TIMESTAMP NULL,
  `deleted_by` VARCHAR(100),
  `_bronze_loaded_at` TIMESTAMP NULL,
  `_source_system` VARCHAR(50),
  KEY `ix_patient_id` (`patient_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `Screening_Question`;
CREATE TABLE `Screening_Question` (
  `question_id` INT,
  `question_text` TEXT,
  `is_active` TINYINT(1),
  `display_order` INT,
  `created_at` TIMESTAMP NULL,
  `created_by` VARCHAR(100),
  `updated_at` TIMESTAMP NULL,
  `updated_by` VARCHAR(100),
  `deleted_at` TIMESTAMP NULL,
  `deleted_by` VARCHAR(100),
  `_bronze_loaded_at` TIMESTAMP NULL,
  `_source_system` VARCHAR(50),
  KEY `ix_screening_question_id` (`question_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `Screening_Record`;
CREATE TABLE `Screening_Record` (
  `record_id` INT,
  `patient_id` INT,
  `created_at` TIMESTAMP NULL,
  `created_by` VARCHAR(100),
  `updated_at` TIMESTAMP NULL,
  `updated_by` VARCHAR(100),
  `deleted_at` TIMESTAMP NULL,
  `deleted_by` VARCHAR(100),
  `_bronze_loaded_at` TIMESTAMP NULL,
  `_source_system` VARCHAR(50),
  KEY `ix_screening_record_id` (`record_id`),
  KEY `ix_screening_record_patient_id` (`patient_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `Screening_Answer`;
CREATE TABLE `Screening_Answer` (
  `record_id` INT,
  `question_id` INT,
  `answer` TINYINT(1),
  `remark` TEXT,
  `created_at` TIMESTAMP NULL,
  `created_by` VARCHAR(100),
  `updated_at` TIMESTAMP NULL,
  `updated_by` VARCHAR(100),
  `deleted_at` TIMESTAMP NULL,
  `deleted_by` VARCHAR(100),
  `_bronze_loaded_at` TIMESTAMP NULL,
  `_source_system` VARCHAR(50),
  KEY `ix_screening_answer_record_id` (`record_id`),
  KEY `ix_screening_answer_question_id` (`question_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `Student`;
CREATE TABLE `Student` (
  `student_id` INT,
  `patient_id` INT,
  `created_at` TIMESTAMP NULL,
  `created_by` VARCHAR(100),
  `updated_at` TIMESTAMP NULL,
  `updated_by` VARCHAR(100),
  `deleted_at` TIMESTAMP NULL,
  `deleted_by` VARCHAR(100),
  `_bronze_loaded_at` TIMESTAMP NULL,
  `_source_system` VARCHAR(50),
  KEY `ix_student_patient_id` (`patient_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `System_Audit_Log`;
CREATE TABLE `System_Audit_Log` (
  `audit_id` INT,
  `table_name` VARCHAR(100),
  `record_id` INT,
  `action_type` VARCHAR(20),
  `old_values` TEXT,
  `new_values` TEXT,
  `changed_by` VARCHAR(100),
  `changed_at` TIMESTAMP NULL,
  `_bronze_loaded_at` TIMESTAMP NULL,
  `_source_system` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
-- NOTE: System_Audit_Log is replicated to Bronze for completeness/audit
-- traceability but is intentionally NOT carried into Silver/Gold — it is
-- operational change-log noise, not a business entity for executive KPIs.

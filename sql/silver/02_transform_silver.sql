-- ============================================================================
-- Bronze -> Silver transformation.
-- Run AFTER 01_create_silver_tables.sql (which drops/recreates empty tables,
-- so this script never needs an explicit TRUNCATE).
--
-- Cleansing rules applied:
--   * Deduplication: ROW_NUMBER() per natural key, latest `updated_at`
--     (falling back to `created_at`) wins — defensive even though the
--     current full-refresh Bronze load should not itself introduce dupes.
--   * Enum standardization: `document_type`, `patient_type`, `sex` are
--     trimmed/lower-cased and validated against the known value set; any
--     unexpected/legacy value maps to an explicit 'UNKNOWN' rather than
--     silently nulling or failing the load.
--   * Timestamp casting: all *_at columns explicitly CAST to DATETIME.
--   * Soft-deletes are preserved (`is_deleted` flag) rather than dropped,
--     so Gold can decide whether to include them (default: excluded).
-- ============================================================================

USE silver;

-- ---------------------------------------------------------------------------
-- company
-- ---------------------------------------------------------------------------
INSERT INTO silver.company (company_id, company_name, is_active, created_at, updated_at)
SELECT company_id, company_name, is_active, created_at, updated_at
FROM (
  SELECT
    b.company_id,
    TRIM(b.company_name) AS company_name,
    IF(b.deleted_at IS NULL, 1, 0) AS is_active,
    CAST(b.created_at AS DATETIME) AS created_at,
    CAST(b.updated_at AS DATETIME) AS updated_at,
    ROW_NUMBER() OVER (
      PARTITION BY b.company_id
      ORDER BY COALESCE(b.updated_at, b.created_at) DESC
    ) AS rn
  FROM bronze.Company b
  WHERE b.company_id IS NOT NULL
) d
WHERE d.rn = 1;

-- ---------------------------------------------------------------------------
-- patient
-- ---------------------------------------------------------------------------
INSERT INTO silver.patient (
  patient_id, document_type, id_card, passport_id, line_id, patient_type_code,
  sex, prefix, first_name, last_name, full_name, tel_no, email,
  underlying_disease, has_underlying_disease, age, address, zip_code,
  is_deleted, created_at, updated_at
)
SELECT
  patient_id, document_type, id_card, passport_id, line_id, patient_type_code,
  sex, prefix, first_name, last_name, full_name, tel_no, email,
  underlying_disease, has_underlying_disease, age, address, zip_code,
  is_deleted, created_at, updated_at
FROM (
  SELECT
    b.patient_id,
    CASE LOWER(TRIM(b.document_type))
      WHEN 'id_card'  THEN 'ID_CARD'
      WHEN 'passport' THEN 'PASSPORT'
      ELSE 'UNKNOWN'
    END AS document_type,
    NULLIF(TRIM(b.id_card), '') AS id_card,
    NULLIF(TRIM(b.passport_id), '') AS passport_id,
    NULLIF(TRIM(b.line_id), '') AS line_id,
    CASE LOWER(TRIM(b.patient_type))
      WHEN 'employee'         THEN 'employee'
      WHEN 'student'          THEN 'student'
      WHEN 'company_employee' THEN 'company_employee'
      WHEN 'external'         THEN 'external'
      ELSE 'unknown'
    END AS patient_type_code,
    CASE LOWER(TRIM(b.sex))
      WHEN 'male'   THEN 'male'
      WHEN 'female' THEN 'female'
      ELSE 'unknown'
    END AS sex,
    NULLIF(TRIM(b.prefix), '') AS prefix,
    TRIM(b.first_name) AS first_name,
    TRIM(b.last_name) AS last_name,
    TRIM(CONCAT_WS(' ', NULLIF(TRIM(b.prefix), ''), TRIM(b.first_name), TRIM(b.last_name))) AS full_name,
    TRIM(b.tel_no) AS tel_no,
    NULLIF(TRIM(b.email), '') AS email,
    NULLIF(TRIM(b.underlying_disease), '') AS underlying_disease,
    IF(NULLIF(TRIM(b.underlying_disease), '') IS NOT NULL, 1, 0) AS has_underlying_disease,
    CASE WHEN b.age BETWEEN 0 AND 120 THEN b.age ELSE NULL END AS age,
    NULLIF(TRIM(b.address), '') AS address,
    NULLIF(TRIM(b.zip_code), '') AS zip_code,
    IF(b.deleted_at IS NOT NULL, 1, 0) AS is_deleted,
    CAST(b.created_at AS DATETIME) AS created_at,
    CAST(b.updated_at AS DATETIME) AS updated_at,
    ROW_NUMBER() OVER (
      PARTITION BY b.patient_id
      ORDER BY COALESCE(b.updated_at, b.created_at) DESC
    ) AS rn
  FROM bronze.Patient b
  WHERE b.patient_id IS NOT NULL
) d
WHERE d.rn = 1;

-- ---------------------------------------------------------------------------
-- contact
-- ---------------------------------------------------------------------------
INSERT INTO silver.contact (contact_id, company_id, is_deleted, created_at, updated_at)
SELECT contact_id, company_id, is_deleted, created_at, updated_at
FROM (
  SELECT
    b.contact_id, b.company_id,
    IF(b.deleted_at IS NOT NULL, 1, 0) AS is_deleted,
    CAST(b.created_at AS DATETIME) AS created_at,
    CAST(b.updated_at AS DATETIME) AS updated_at,
    ROW_NUMBER() OVER (PARTITION BY b.contact_id ORDER BY COALESCE(b.updated_at, b.created_at) DESC) AS rn
  FROM bronze.Contact b
  WHERE b.contact_id IS NOT NULL
    AND b.company_id IN (SELECT company_id FROM silver.company)
) d
WHERE d.rn = 1;

-- ---------------------------------------------------------------------------
-- external_person / student / employee / company_employee
-- (all subtype tables share the same dedupe + "parent patient must exist"
-- pattern, so they're kept structurally identical for readability)
-- ---------------------------------------------------------------------------
INSERT INTO silver.external_person (external_id, patient_id, created_at)
SELECT external_id, patient_id, created_at FROM (
  SELECT b.external_id, b.patient_id, CAST(b.created_at AS DATETIME) AS created_at,
    ROW_NUMBER() OVER (PARTITION BY b.patient_id ORDER BY COALESCE(b.updated_at, b.created_at) DESC) AS rn
  FROM bronze.External_Person b
  WHERE b.patient_id IN (SELECT patient_id FROM silver.patient)
) d WHERE d.rn = 1;

INSERT INTO silver.student (student_id, patient_id, created_at)
SELECT student_id, patient_id, created_at FROM (
  SELECT b.student_id, b.patient_id, CAST(b.created_at AS DATETIME) AS created_at,
    ROW_NUMBER() OVER (PARTITION BY b.patient_id ORDER BY COALESCE(b.updated_at, b.created_at) DESC) AS rn
  FROM bronze.Student b
  WHERE b.patient_id IN (SELECT patient_id FROM silver.patient)
) d WHERE d.rn = 1;

INSERT INTO silver.employee (employee_id, patient_id, created_at)
SELECT employee_id, patient_id, created_at FROM (
  SELECT b.employee_id, b.patient_id, CAST(b.created_at AS DATETIME) AS created_at,
    ROW_NUMBER() OVER (PARTITION BY b.patient_id ORDER BY COALESCE(b.updated_at, b.created_at) DESC) AS rn
  FROM bronze.Employee b
  WHERE b.patient_id IN (SELECT patient_id FROM silver.patient)
) d WHERE d.rn = 1;

INSERT INTO silver.company_employee (employee_id, company_id, patient_id, created_at)
SELECT employee_id, company_id, patient_id, created_at FROM (
  SELECT b.employee_id, b.company_id, b.patient_id, CAST(b.created_at AS DATETIME) AS created_at,
    ROW_NUMBER() OVER (PARTITION BY b.patient_id ORDER BY COALESCE(b.updated_at, b.created_at) DESC) AS rn
  FROM bronze.Company_Employee b
  WHERE b.patient_id IN (SELECT patient_id FROM silver.patient)
    AND b.company_id IN (SELECT company_id FROM silver.company)
) d WHERE d.rn = 1;

-- ---------------------------------------------------------------------------
-- screening_question
-- Source text is bilingual, "<Thai> / <English>" in one column — split on
-- the ' / ' delimiter. Caveat: relies on the delimiter not appearing inside
-- either language segment, true for the current questionnaire content.
-- ---------------------------------------------------------------------------
INSERT INTO silver.screening_question (question_id, question_text_th, question_text_en, is_active, display_order)
SELECT question_id, question_text_th, question_text_en, is_active, display_order FROM (
  SELECT
    b.question_id,
    TRIM(SUBSTRING_INDEX(b.question_text, ' / ', 1)) AS question_text_th,
    TRIM(SUBSTRING_INDEX(b.question_text, ' / ', -1)) AS question_text_en,
    b.is_active,
    b.display_order,
    ROW_NUMBER() OVER (PARTITION BY b.question_id ORDER BY COALESCE(b.updated_at, b.created_at) DESC) AS rn
  FROM bronze.Screening_Question b
  WHERE b.question_id IS NOT NULL
) d WHERE d.rn = 1;

-- ---------------------------------------------------------------------------
-- screening_record
-- ---------------------------------------------------------------------------
INSERT INTO silver.screening_record (record_id, patient_id, is_deleted, created_at)
SELECT record_id, patient_id, is_deleted, created_at FROM (
  SELECT
    b.record_id, b.patient_id,
    IF(b.deleted_at IS NOT NULL, 1, 0) AS is_deleted,
    CAST(b.created_at AS DATETIME) AS created_at,
    ROW_NUMBER() OVER (PARTITION BY b.record_id ORDER BY COALESCE(b.updated_at, b.created_at) DESC) AS rn
  FROM bronze.Screening_Record b
  WHERE b.patient_id IN (SELECT patient_id FROM silver.patient)
) d WHERE d.rn = 1;

-- ---------------------------------------------------------------------------
-- screening_answer (composite key record_id+question_id)
-- ---------------------------------------------------------------------------
INSERT INTO silver.screening_answer (record_id, question_id, answer_flag, remark, created_at)
SELECT record_id, question_id, answer_flag, remark, created_at FROM (
  SELECT
    b.record_id, b.question_id,
    IF(b.answer = 1, 1, 0) AS answer_flag,
    NULLIF(TRIM(b.remark), '') AS remark,
    CAST(b.created_at AS DATETIME) AS created_at,
    ROW_NUMBER() OVER (PARTITION BY b.record_id, b.question_id ORDER BY COALESCE(b.updated_at, b.created_at) DESC) AS rn
  FROM bronze.Screening_Answer b
  WHERE b.record_id IN (SELECT record_id FROM silver.screening_record)
    AND b.question_id IN (SELECT question_id FROM silver.screening_question)
) d WHERE d.rn = 1;


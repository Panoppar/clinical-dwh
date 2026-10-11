-- ============================================================================
-- Silver -> Gold: populate dimension tables.
-- Run AFTER 03_load_dim_date.sql.
-- ============================================================================

USE gold;

-- ---------------------------------------------------------------------------
-- Dim_Company — includes a synthetic company_sk = -1 "Not Applicable" member
-- so fact rows for non-corporate patients get a real FK instead of NULL.
-- ---------------------------------------------------------------------------
INSERT INTO Dim_Company (company_sk, company_id, company_name, is_active)
VALUES (-1, NULL, 'Not Applicable / Non-Corporate', 1);

INSERT INTO Dim_Company (company_sk, company_id, company_name, is_active)
SELECT
  ROW_NUMBER() OVER (ORDER BY company_id) AS company_sk,
  company_id,
  company_name,
  is_active
FROM silver.company;

-- ---------------------------------------------------------------------------
-- Dim_Patient
-- ---------------------------------------------------------------------------
INSERT INTO Dim_Patient (
  patient_id, document_type, patient_type_code, patient_type_desc,
  sex, age, age_band, has_underlying_disease, is_deleted, source_created_at,
  zip_code, district_code, district_name_en, province_code, province_name_en, is_geo_ambiguous
)
SELECT
  p.patient_id,
  p.document_type,
  p.patient_type_code,
  CASE p.patient_type_code
    WHEN 'employee'         THEN 'Internal Employee'
    WHEN 'student'          THEN 'Student'
    WHEN 'company_employee' THEN 'Corporate Employee'
    WHEN 'external'         THEN 'External / Visitor'
    ELSE 'Unknown'
  END AS patient_type_desc,
  p.sex,
  p.age,
  CASE
    WHEN p.age IS NULL        THEN 'Unknown'
    WHEN p.age < 18            THEN '<18'
    WHEN p.age BETWEEN 18 AND 29 THEN '18-29'
    WHEN p.age BETWEEN 30 AND 39 THEN '30-39'
    WHEN p.age BETWEEN 40 AND 49 THEN '40-49'
    WHEN p.age BETWEEN 50 AND 59 THEN '50-59'
    ELSE '60+'
  END AS age_band,
  p.has_underlying_disease,
  p.is_deleted,
  p.created_at,
  p.zip_code,
  zc.district_code,
  zc.district_name_en,
  zc.province_code,
  zc.province_name_en,
  zc.is_ambiguous
FROM silver.patient p
LEFT JOIN silver.zip_code_primary_district zc ON zc.zip_code = p.zip_code;

-- ---------------------------------------------------------------------------
-- Dim_Question
-- ---------------------------------------------------------------------------
INSERT INTO Dim_Question (question_id, question_text_th, question_text_en, is_active, display_order)
SELECT question_id, question_text_th, question_text_en, is_active, display_order
FROM silver.screening_question;

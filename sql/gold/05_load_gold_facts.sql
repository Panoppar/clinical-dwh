-- ============================================================================
-- Silver -> Gold: populate fact tables.
-- Run AFTER 04_load_gold_dimensions.sql.
--
-- Default policy: soft-deleted source rows (is_deleted = 1 in Silver) are
-- EXCLUDED from Gold facts — executive KPIs should reflect current,
-- non-retracted records. Change the WHERE clauses below if historical/
-- deleted rows are ever needed for audit-style reporting.
-- ============================================================================

USE gold;

-- ---------------------------------------------------------------------------
-- Fact_Patient_Registration — grain: one row per patient
-- ---------------------------------------------------------------------------
INSERT INTO Fact_Patient_Registration (date_key, patient_sk, company_sk, registration_count)
SELECT
  CAST(DATE_FORMAT(p.created_at, '%Y%m%d') AS UNSIGNED) AS date_key,
  dp.patient_sk,
  COALESCE(dc.company_sk, -1) AS company_sk,
  1 AS registration_count
FROM silver.patient p
JOIN Dim_Patient dp ON dp.patient_id = p.patient_id
LEFT JOIN silver.company_employee ce ON ce.patient_id = p.patient_id
LEFT JOIN Dim_Company dc ON dc.company_id = ce.company_id
WHERE p.is_deleted = 0;

-- ---------------------------------------------------------------------------
-- Fact_Screening_Response — grain: one row per screening answer
-- ---------------------------------------------------------------------------
INSERT INTO Fact_Screening_Response (
  date_key, patient_sk, company_sk, question_sk, record_id, is_flagged, response_count
)
SELECT
  CAST(DATE_FORMAT(sr.created_at, '%Y%m%d') AS UNSIGNED) AS date_key,
  dp.patient_sk,
  COALESCE(dc.company_sk, -1) AS company_sk,
  dq.question_sk,
  sa.record_id,
  sa.answer_flag AS is_flagged,
  1 AS response_count
FROM silver.screening_answer sa
JOIN silver.screening_record sr ON sr.record_id = sa.record_id AND sr.is_deleted = 0
JOIN silver.patient p ON p.patient_id = sr.patient_id AND p.is_deleted = 0
JOIN Dim_Patient dp ON dp.patient_id = p.patient_id
JOIN Dim_Question dq ON dq.question_id = sa.question_id
LEFT JOIN silver.company_employee ce ON ce.patient_id = p.patient_id
LEFT JOIN Dim_Company dc ON dc.company_id = ce.company_id;

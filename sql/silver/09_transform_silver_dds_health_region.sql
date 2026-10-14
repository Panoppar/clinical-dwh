USE silver;

INSERT INTO dds_health_region_disease_report
  (health_region_code, report_year_ce, report_period_label, rank_no, disease_name_th,
   patient_count, morbidity_rate_per_100k, ipd_count, death_count, case_fatality_rate_pct,
   is_aggregate_row)
SELECT
  health_region_code, CAST(report_year AS UNSIGNED), report_period_label,
  CAST(NULLIF(raw_no, '') AS UNSIGNED),
  TRIM(raw_disease_name_th),
  CAST(NULLIF(REPLACE(raw_patient_count, ',', ''), '') AS SIGNED),
  CAST(NULLIF(raw_morbidity_rate, '') AS DECIMAL(10,2)),
  CAST(NULLIF(REPLACE(raw_ipd_count, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(raw_death_count, ',', ''), '') AS SIGNED),
  CAST(NULLIF(raw_case_fatality_rate, '') AS DECIMAL(6,2)),
  IF(TRIM(raw_disease_name_th) LIKE '%รวม', 1, 0)
FROM bronze.dds_health_region_disease_report;

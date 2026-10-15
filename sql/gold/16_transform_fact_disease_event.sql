USE gold;

-- 1. DDS health-region disease reports. No geography match -- DDS's
-- health_region_code (e.g. "skr13") is a MOPH health-service zone
-- spanning multiple provinces, not part of dim_geography's hierarchy.
INSERT INTO fact_disease_event (geo_key, date_key, disease_key, health_region_code, case_count, death_count, rate_per_100k, ipd_count, case_fatality_rate_pct, source_system)
SELECT NULL, s.report_year_ce * 10000 + 101, dd.disease_key, s.health_region_code,
    s.patient_count, s.death_count, s.morbidity_rate_per_100k, s.ipd_count, s.case_fatality_rate_pct, 'dds'
FROM silver.dds_health_region_disease_report s
JOIN dim_disease dd ON dd.source_system = 'dds' AND dd.disease_code = s.disease_name_th
WHERE s.is_aggregate_row = 0;

-- 2. Cause of death (with-rate variant only -- cause_of_death_top10_no_rate
-- is confirmed identical data minus the rate column, same province/years/
-- counts verified by direct comparison; loading both would double-count).
-- total_count here IS a death count (these are deaths by cause), not a
-- case count.
INSERT INTO fact_disease_event (geo_key, date_key, disease_key, death_count, rate_per_100k, source_system)
SELECT
    IF(s.province = 'ทั้งประเทศ', (SELECT geo_key FROM dim_geography WHERE admin_level = 'country' LIMIT 1), dg.geo_key),
    s.year_ce * 10000 + 101, dd.disease_key, s.total_count, s.rate_per_100k, 'cause_of_death'
FROM silver.cause_of_death_top10_with_rate s
JOIN dim_disease dd ON dd.source_system = 'cause_of_death' AND dd.disease_code = s.cause_of_death
LEFT JOIN dim_geography dg ON dg.admin_level = 'province' AND TRIM(REPLACE(dg.province_name_th, 'จังหวัด', '')) = TRIM(s.province)
WHERE s.is_aggregate_row = 0;

-- 3. NCD mortality by disease.
INSERT INTO fact_disease_event (geo_key, date_key, disease_key, death_count, rate_per_100k, source_system)
SELECT
    IF(s.province = 'ทั้งประเทศ', (SELECT geo_key FROM dim_geography WHERE admin_level = 'country' LIMIT 1), dg.geo_key),
    s.year_ce * 10000 + 101, dd.disease_key, s.death_count, s.death_rate_per_100k, 'ncd_mortality'
FROM silver.ncd_mortality_by_disease s
JOIN dim_disease dd ON dd.source_system = 'ncd_mortality' AND dd.disease_code = s.disease
LEFT JOIN dim_geography dg ON dg.admin_level = 'province' AND TRIM(REPLACE(dg.province_name_th, 'จังหวัด', '')) = TRIM(s.province)
WHERE s.is_aggregate_row = 0;

-- 4. sick_298group, long format (already one row per sex).
INSERT INTO fact_disease_event (geo_key, date_key, disease_key, age_sex_key, case_count, source_system)
SELECT dg.geo_key, s.year_ce * 10000 + 101, dd.disease_key, das.age_sex_key, s.case_count, 'sick298'
FROM silver.sick_298group_long s
JOIN dim_disease dd ON dd.source_system = 'sick298' AND dd.disease_code = s.disease_group
LEFT JOIN dim_geography dg ON dg.admin_level = 'province' AND TRIM(REPLACE(dg.province_name_th, 'จังหวัด', '')) = TRIM(s.province)
JOIN dim_age_sex das ON das.sex = s.sex AND das.age_exact IS NULL AND das.age_qualifier IS NULL
WHERE s.is_aggregate_row = 0;

-- 5. sick_298group, wide format -- unpivoted male/female/total into 3 rows.
INSERT INTO fact_disease_event (geo_key, date_key, disease_key, age_sex_key, case_count, source_system)
SELECT dg.geo_key, s.year_ce * 10000 + 101, dd.disease_key, das.age_sex_key, v.case_count, 'sick298'
FROM silver.sick_298group_wide s
JOIN dim_disease dd ON dd.source_system = 'sick298' AND dd.disease_code = s.disease_group
LEFT JOIN dim_geography dg ON dg.admin_level = 'province' AND TRIM(REPLACE(dg.province_name_th, 'จังหวัด', '')) = TRIM(s.province)
JOIN (
    SELECT 'male' AS sex, silver_id, male_count AS case_count FROM silver.sick_298group_wide
    UNION ALL SELECT 'female', silver_id, female_count FROM silver.sick_298group_wide
    UNION ALL SELECT 'total', silver_id, total_count FROM silver.sick_298group_wide
) v ON v.silver_id = s.silver_id
JOIN dim_age_sex das ON das.sex = v.sex AND das.age_exact IS NULL AND das.age_qualifier IS NULL
WHERE s.is_aggregate_row = 0;

-- 6. compare_cases_by_disease -- no geography (national), unpivoted
-- count_2024/count_2025 into 2 year rows.
INSERT INTO fact_disease_event (geo_key, date_key, disease_key, case_count, source_system)
SELECT (SELECT geo_key FROM dim_geography WHERE admin_level = 'country' LIMIT 1), v.year_ce * 10000 + 101, dd.disease_key, v.case_count, 'compare_cases'
FROM silver.compare_cases_by_disease s
JOIN dim_disease dd ON dd.source_system = 'compare_cases' AND dd.disease_code = s.disease_name
JOIN (
    SELECT 2024 AS year_ce, silver_id, count_2024 AS case_count FROM silver.compare_cases_by_disease
    UNION ALL SELECT 2025, silver_id, count_2025 FROM silver.compare_cases_by_disease
) v ON v.silver_id = s.silver_id
WHERE s.is_aggregate_row = 0;

-- 7. compare_cases_by_subdistrict -- no disease dimension in the source
-- (confirmed: it's a total-patient-count comparison, not disease-
-- specific), tagged with the catch-all 'all_diseases_combined' disease.
-- geo_key matched on subdistrict_name_th alone within Bangkok
-- (province_code='10') -- confirmed unambiguous by direct inspection;
-- the one placeholder row ("ไม่ระบุ/ไม่มีแขวง" -- not specified) stays
-- NULL rather than guessed.
INSERT INTO fact_disease_event (geo_key, date_key, disease_key, case_count, source_system)
SELECT dg.geo_key, v.year_ce * 10000 + 101, dd.disease_key, v.case_count, 'compare_cases'
FROM silver.compare_cases_by_subdistrict s
JOIN dim_disease dd ON dd.source_system = 'compare_cases' AND dd.disease_code = 'all_diseases_combined'
LEFT JOIN dim_geography dg ON dg.admin_level = 'subdistrict' AND dg.province_code = '10' AND dg.subdistrict_name_th = TRIM(s.subdistrict_name)
JOIN (
    SELECT 2024 AS year_ce, silver_id, count_2024 AS case_count FROM silver.compare_cases_by_subdistrict
    UNION ALL SELECT 2025, silver_id, count_2025 FROM silver.compare_cases_by_subdistrict
) v ON v.silver_id = s.silver_id
WHERE s.is_aggregate_row = 0;

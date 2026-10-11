-- ============================================================================
-- Silver -> Gold: populate Phase 2 dashboard-ready tables.
-- Run AFTER 10_create_gold_phase2_facts.sql.
-- ============================================================================

USE gold;

INSERT INTO Fact_HDC_Pop_Age (disease, province_code, province_name_en, year_ce, age_group, population, cases)
SELECT disease, CAST(s.province_code AS UNSIGNED), prov.province_name_en, year_ce, 'Age Group 1', SUM(pop_group1), SUM(result_group1)
FROM silver.hdc_disease_pop_age s
LEFT JOIN (SELECT DISTINCT province_code, province_name_en FROM silver.thai_geography) prov
  ON prov.province_code = CAST(s.province_code AS UNSIGNED)
GROUP BY disease, s.province_code, prov.province_name_en, year_ce
UNION ALL
SELECT disease, CAST(s.province_code AS UNSIGNED), prov.province_name_en, year_ce, 'Age Group 2', SUM(pop_group2), SUM(result_group2)
FROM silver.hdc_disease_pop_age s
LEFT JOIN (SELECT DISTINCT province_code, province_name_en FROM silver.thai_geography) prov
  ON prov.province_code = CAST(s.province_code AS UNSIGNED)
GROUP BY disease, s.province_code, prov.province_name_en, year_ce
UNION ALL
SELECT disease, CAST(s.province_code AS UNSIGNED), prov.province_name_en, year_ce, 'Age Group 3', SUM(pop_group3), SUM(result_group3)
FROM silver.hdc_disease_pop_age s
LEFT JOIN (SELECT DISTINCT province_code, province_name_en FROM silver.thai_geography) prov
  ON prov.province_code = CAST(s.province_code AS UNSIGNED)
GROUP BY disease, s.province_code, prov.province_name_en, year_ce
UNION ALL
SELECT disease, CAST(s.province_code AS UNSIGNED), prov.province_name_en, year_ce, 'Age Group 4', SUM(pop_group4), SUM(result_group4)
FROM silver.hdc_disease_pop_age s
LEFT JOIN (SELECT DISTINCT province_code, province_name_en FROM silver.thai_geography) prov
  ON prov.province_code = CAST(s.province_code AS UNSIGNED)
GROUP BY disease, s.province_code, prov.province_name_en, year_ce
UNION ALL
SELECT disease, CAST(s.province_code AS UNSIGNED), prov.province_name_en, year_ce, 'Age Group 5', SUM(pop_group5), SUM(result_group5)
FROM silver.hdc_disease_pop_age s
LEFT JOIN (SELECT DISTINCT province_code, province_name_en FROM silver.thai_geography) prov
  ON prov.province_code = CAST(s.province_code AS UNSIGNED)
GROUP BY disease, s.province_code, prov.province_name_en, year_ce;

INSERT INTO Fact_HDC_Incidence (disease, province_code, province_name_en, year_ce, target, result, achievement_rate_pct)
SELECT
  disease, CAST(s.province_code AS UNSIGNED), prov.province_name_en, year_ce,
  SUM(target), SUM(result),
  CASE WHEN SUM(target) > 0 THEN ROUND(SUM(result) * 100.0 / SUM(target), 2) ELSE NULL END
FROM silver.hdc_disease_incidence s
LEFT JOIN (SELECT DISTINCT province_code, province_name_en FROM silver.thai_geography) prov
  ON prov.province_code = CAST(s.province_code AS UNSIGNED)
GROUP BY disease, s.province_code, prov.province_name_en, year_ce;

INSERT INTO Fact_HDC_Death_Age (disease, province_code, province_name_en, year_ce, age_group, person_time, deaths)
SELECT disease, CAST(s.province_code AS UNSIGNED), prov.province_name_en, year_ce, 'Age Group 1', SUM(pt_group1), SUM(death_group1)
FROM silver.hdc_disease_death_age s
LEFT JOIN (SELECT DISTINCT province_code, province_name_en FROM silver.thai_geography) prov
  ON prov.province_code = CAST(s.province_code AS UNSIGNED)
GROUP BY disease, s.province_code, prov.province_name_en, year_ce
UNION ALL
SELECT disease, CAST(s.province_code AS UNSIGNED), prov.province_name_en, year_ce, 'Age Group 2', SUM(pt_group2), SUM(death_group2)
FROM silver.hdc_disease_death_age s
LEFT JOIN (SELECT DISTINCT province_code, province_name_en FROM silver.thai_geography) prov
  ON prov.province_code = CAST(s.province_code AS UNSIGNED)
GROUP BY disease, s.province_code, prov.province_name_en, year_ce
UNION ALL
SELECT disease, CAST(s.province_code AS UNSIGNED), prov.province_name_en, year_ce, 'Age Group 3', SUM(pt_group3), SUM(death_group3)
FROM silver.hdc_disease_death_age s
LEFT JOIN (SELECT DISTINCT province_code, province_name_en FROM silver.thai_geography) prov
  ON prov.province_code = CAST(s.province_code AS UNSIGNED)
GROUP BY disease, s.province_code, prov.province_name_en, year_ce
UNION ALL
SELECT disease, CAST(s.province_code AS UNSIGNED), prov.province_name_en, year_ce, 'Age Group 4', SUM(pt_group4), SUM(death_group4)
FROM silver.hdc_disease_death_age s
LEFT JOIN (SELECT DISTINCT province_code, province_name_en FROM silver.thai_geography) prov
  ON prov.province_code = CAST(s.province_code AS UNSIGNED)
GROUP BY disease, s.province_code, prov.province_name_en, year_ce
UNION ALL
SELECT disease, CAST(s.province_code AS UNSIGNED), prov.province_name_en, year_ce, 'Age Group 5', SUM(pt_group5), SUM(death_group5)
FROM silver.hdc_disease_death_age s
LEFT JOIN (SELECT DISTINCT province_code, province_name_en FROM silver.thai_geography) prov
  ON prov.province_code = CAST(s.province_code AS UNSIGNED)
GROUP BY disease, s.province_code, prov.province_name_en, year_ce;

INSERT INTO Fact_DDS_Disease_Ranking (
  province_code, province_name_en, province_name_th, year_ce, disease_th,
  case_count, case_fatality_pct, death_count, rate_per_100k, rank_by_cases, is_provisional
)
SELECT
  CAST(d.province_code AS UNSIGNED), prov.province_name_en, d.province_name_th, d.year_ce, d.disease_th,
  d.case_count, d.case_fatality_pct, d.death_count, d.rate_per_100k, d.rank_by_cases, d.is_provisional
FROM silver.dds_yearly_disease_ranking d
LEFT JOIN (SELECT DISTINCT province_code, province_name_en FROM silver.thai_geography) prov
  ON prov.province_code = CAST(d.province_code AS UNSIGNED);

INSERT INTO Fact_Lat_Krabang_Population (subdistrict_name_th, sex, population)
SELECT subdistrict_name_th, sex, count FROM silver.lat_krabang_population_by_subdistrict;

INSERT INTO Fact_Lat_Krabang_Deaths (subdistrict_name_th, sex, deaths)
SELECT subdistrict_name_th, sex, count FROM silver.lat_krabang_deaths_by_subdistrict;

INSERT INTO Dim_Lat_Krabang_POI (poi_type, name_th, investment_thb, student_num, risk_type)
SELECT
  poi_type, name_th,
  CAST(JSON_UNQUOTE(JSON_EXTRACT(attributes, '$.investment_thb')) AS DECIMAL(15,2)),
  CAST(JSON_UNQUOTE(JSON_EXTRACT(attributes, '$.student_num')) AS UNSIGNED),
  JSON_UNQUOTE(JSON_EXTRACT(attributes, '$.risk_type'))
FROM silver.lat_krabang_points_of_interest;

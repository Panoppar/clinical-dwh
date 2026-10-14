-- ============================================================================
-- SILVER LAYER — transform HDC_region6_13_by_age_api
-- ============================================================================

USE silver;

-- ---------------------------------------------------------------------
-- hdc_incidence_monthly: UNION of 5 bronze tables, disease literal + BE->CE
-- ---------------------------------------------------------------------
INSERT INTO hdc_incidence_monthly
  (disease, province_code, province_name, hospcode, areacode, b_year_be, b_year_ce,
   target, result, result10, result11, result12, result01, result02, result03,
   result04, result05, result06, result07, result08, result09)
SELECT 'asthma', province_code, province_name, hospcode, areacode,
  CAST(b_year AS UNSIGNED), CAST(b_year AS UNSIGNED) - 543,
  target, result, result10, result11, result12, result01, result02, result03,
  result04, result05, result06, result07, result08, result09
FROM bronze.inc_monthly_asthma
UNION ALL
SELECT 'copd', province_code, province_name, hospcode, areacode,
  CAST(b_year AS UNSIGNED), CAST(b_year AS UNSIGNED) - 543,
  target, result, result10, result11, result12, result01, result02, result03,
  result04, result05, result06, result07, result08, result09
FROM bronze.inc_monthly_copd
UNION ALL
SELECT 'coronary', province_code, province_name, hospcode, areacode,
  CAST(b_year AS UNSIGNED), CAST(b_year AS UNSIGNED) - 543,
  target, result, result10, result11, result12, result01, result02, result03,
  result04, result05, result06, result07, result08, result09
FROM bronze.inc_monthly_coronary
UNION ALL
SELECT 'dm', province_code, province_name, hospcode, areacode,
  CAST(b_year AS UNSIGNED), CAST(b_year AS UNSIGNED) - 543,
  target, result, result10, result11, result12, result01, result02, result03,
  result04, result05, result06, result07, result08, result09
FROM bronze.inc_monthly_dm
UNION ALL
SELECT 'ht', province_code, province_name, hospcode, areacode,
  CAST(b_year AS UNSIGNED), CAST(b_year AS UNSIGNED) - 543,
  target, result, result10, result11, result12, result01, result02, result03,
  result04, result05, result06, result07, result08, result09
FROM bronze.inc_monthly_ht;

-- ---------------------------------------------------------------------
-- hdc_incidence_annual: single bronze table (distinct schema vs monthly)
-- ---------------------------------------------------------------------
INSERT INTO hdc_incidence_annual
  (disease, province_code, province_name, hospcode, areacode, b_year_be, b_year_ce,
   target, result, target1, result1)
SELECT 'ihd', province_code, province_name, hospcode, areacode,
  CAST(b_year AS UNSIGNED), CAST(b_year AS UNSIGNED) - 543,
  target, result, target1, result1
FROM bronze.inc_annual_ihd;

-- ---------------------------------------------------------------------
-- hdc_population_by_age: UNION of 9 bronze tables, unpivoting the 5
-- pop_group/result_group pairs into one row per age_group (1-5).
-- ---------------------------------------------------------------------
INSERT INTO hdc_population_by_age
  (disease, province_code, province_name, hospcode, areacode, b_year_be, b_year_ce,
   age_group, population, result)
SELECT disease, province_code, province_name, hospcode, areacode,
  CAST(b_year AS UNSIGNED), CAST(b_year AS UNSIGNED) - 543, age_group, population, result
FROM (
  SELECT 'ca_breast' AS disease, province_code, province_name, hospcode, areacode, b_year,
    1 AS age_group, pop_group1 AS population, result_group1 AS result FROM bronze.pop_age_ca_breast
  UNION ALL SELECT 'ca_breast', province_code, province_name, hospcode, areacode, b_year, 2, pop_group2, result_group2 FROM bronze.pop_age_ca_breast
  UNION ALL SELECT 'ca_breast', province_code, province_name, hospcode, areacode, b_year, 3, pop_group3, result_group3 FROM bronze.pop_age_ca_breast
  UNION ALL SELECT 'ca_breast', province_code, province_name, hospcode, areacode, b_year, 4, pop_group4, result_group4 FROM bronze.pop_age_ca_breast
  UNION ALL SELECT 'ca_breast', province_code, province_name, hospcode, areacode, b_year, 5, pop_group5, result_group5 FROM bronze.pop_age_ca_breast

  UNION ALL SELECT 'ca_cervix', province_code, province_name, hospcode, areacode, b_year, 1, pop_group1, result_group1 FROM bronze.pop_age_ca_cervix
  UNION ALL SELECT 'ca_cervix', province_code, province_name, hospcode, areacode, b_year, 2, pop_group2, result_group2 FROM bronze.pop_age_ca_cervix
  UNION ALL SELECT 'ca_cervix', province_code, province_name, hospcode, areacode, b_year, 3, pop_group3, result_group3 FROM bronze.pop_age_ca_cervix
  UNION ALL SELECT 'ca_cervix', province_code, province_name, hospcode, areacode, b_year, 4, pop_group4, result_group4 FROM bronze.pop_age_ca_cervix
  UNION ALL SELECT 'ca_cervix', province_code, province_name, hospcode, areacode, b_year, 5, pop_group5, result_group5 FROM bronze.pop_age_ca_cervix

  UNION ALL SELECT 'ca_lung', province_code, province_name, hospcode, areacode, b_year, 1, pop_group1, result_group1 FROM bronze.pop_age_ca_lung
  UNION ALL SELECT 'ca_lung', province_code, province_name, hospcode, areacode, b_year, 2, pop_group2, result_group2 FROM bronze.pop_age_ca_lung
  UNION ALL SELECT 'ca_lung', province_code, province_name, hospcode, areacode, b_year, 3, pop_group3, result_group3 FROM bronze.pop_age_ca_lung
  UNION ALL SELECT 'ca_lung', province_code, province_name, hospcode, areacode, b_year, 4, pop_group4, result_group4 FROM bronze.pop_age_ca_lung
  UNION ALL SELECT 'ca_lung', province_code, province_name, hospcode, areacode, b_year, 5, pop_group5, result_group5 FROM bronze.pop_age_ca_lung

  UNION ALL SELECT 'copd', province_code, province_name, hospcode, areacode, b_year, 1, pop_group1, result_group1 FROM bronze.pop_age_copd
  UNION ALL SELECT 'copd', province_code, province_name, hospcode, areacode, b_year, 2, pop_group2, result_group2 FROM bronze.pop_age_copd
  UNION ALL SELECT 'copd', province_code, province_name, hospcode, areacode, b_year, 3, pop_group3, result_group3 FROM bronze.pop_age_copd
  UNION ALL SELECT 'copd', province_code, province_name, hospcode, areacode, b_year, 4, pop_group4, result_group4 FROM bronze.pop_age_copd
  UNION ALL SELECT 'copd', province_code, province_name, hospcode, areacode, b_year, 5, pop_group5, result_group5 FROM bronze.pop_age_copd

  UNION ALL SELECT 'coronary', province_code, province_name, hospcode, areacode, b_year, 1, pop_group1, result_group1 FROM bronze.pop_age_coronary
  UNION ALL SELECT 'coronary', province_code, province_name, hospcode, areacode, b_year, 2, pop_group2, result_group2 FROM bronze.pop_age_coronary
  UNION ALL SELECT 'coronary', province_code, province_name, hospcode, areacode, b_year, 3, pop_group3, result_group3 FROM bronze.pop_age_coronary
  UNION ALL SELECT 'coronary', province_code, province_name, hospcode, areacode, b_year, 4, pop_group4, result_group4 FROM bronze.pop_age_coronary
  UNION ALL SELECT 'coronary', province_code, province_name, hospcode, areacode, b_year, 5, pop_group5, result_group5 FROM bronze.pop_age_coronary

  UNION ALL SELECT 'dm', province_code, province_name, hospcode, areacode, b_year, 1, pop_group1, result_group1 FROM bronze.pop_age_dm
  UNION ALL SELECT 'dm', province_code, province_name, hospcode, areacode, b_year, 2, pop_group2, result_group2 FROM bronze.pop_age_dm
  UNION ALL SELECT 'dm', province_code, province_name, hospcode, areacode, b_year, 3, pop_group3, result_group3 FROM bronze.pop_age_dm
  UNION ALL SELECT 'dm', province_code, province_name, hospcode, areacode, b_year, 4, pop_group4, result_group4 FROM bronze.pop_age_dm
  UNION ALL SELECT 'dm', province_code, province_name, hospcode, areacode, b_year, 5, pop_group5, result_group5 FROM bronze.pop_age_dm

  UNION ALL SELECT 'emphysema', province_code, province_name, hospcode, areacode, b_year, 1, pop_group1, result_group1 FROM bronze.pop_age_emphysema
  UNION ALL SELECT 'emphysema', province_code, province_name, hospcode, areacode, b_year, 2, pop_group2, result_group2 FROM bronze.pop_age_emphysema
  UNION ALL SELECT 'emphysema', province_code, province_name, hospcode, areacode, b_year, 3, pop_group3, result_group3 FROM bronze.pop_age_emphysema
  UNION ALL SELECT 'emphysema', province_code, province_name, hospcode, areacode, b_year, 4, pop_group4, result_group4 FROM bronze.pop_age_emphysema
  UNION ALL SELECT 'emphysema', province_code, province_name, hospcode, areacode, b_year, 5, pop_group5, result_group5 FROM bronze.pop_age_emphysema

  UNION ALL SELECT 'ht', province_code, province_name, hospcode, areacode, b_year, 1, pop_group1, result_group1 FROM bronze.pop_age_ht
  UNION ALL SELECT 'ht', province_code, province_name, hospcode, areacode, b_year, 2, pop_group2, result_group2 FROM bronze.pop_age_ht
  UNION ALL SELECT 'ht', province_code, province_name, hospcode, areacode, b_year, 3, pop_group3, result_group3 FROM bronze.pop_age_ht
  UNION ALL SELECT 'ht', province_code, province_name, hospcode, areacode, b_year, 4, pop_group4, result_group4 FROM bronze.pop_age_ht
  UNION ALL SELECT 'ht', province_code, province_name, hospcode, areacode, b_year, 5, pop_group5, result_group5 FROM bronze.pop_age_ht

  UNION ALL SELECT 'stroke', province_code, province_name, hospcode, areacode, b_year, 1, pop_group1, result_group1 FROM bronze.pop_age_stroke
  UNION ALL SELECT 'stroke', province_code, province_name, hospcode, areacode, b_year, 2, pop_group2, result_group2 FROM bronze.pop_age_stroke
  UNION ALL SELECT 'stroke', province_code, province_name, hospcode, areacode, b_year, 3, pop_group3, result_group3 FROM bronze.pop_age_stroke
  UNION ALL SELECT 'stroke', province_code, province_name, hospcode, areacode, b_year, 4, pop_group4, result_group4 FROM bronze.pop_age_stroke
  UNION ALL SELECT 'stroke', province_code, province_name, hospcode, areacode, b_year, 5, pop_group5, result_group5 FROM bronze.pop_age_stroke
) u;

-- ---------------------------------------------------------------------
-- hdc_death_by_age: UNION of 4 bronze tables, unpivoting pt_group/death_group
-- ---------------------------------------------------------------------
INSERT INTO hdc_death_by_age
  (disease, province_code, province_name, hospcode, areacode, b_year_be, b_year_ce,
   age_group, person_time, death_count)
SELECT disease, province_code, province_name, hospcode, areacode,
  CAST(b_year AS UNSIGNED), CAST(b_year AS UNSIGNED) - 543, age_group, person_time, death_count
FROM (
  SELECT 'copd' AS disease, province_code, province_name, hospcode, areacode, b_year,
    1 AS age_group, pt_group1 AS person_time, death_group1 AS death_count FROM bronze.death_age_copd
  UNION ALL SELECT 'copd', province_code, province_name, hospcode, areacode, b_year, 2, pt_group2, death_group2 FROM bronze.death_age_copd
  UNION ALL SELECT 'copd', province_code, province_name, hospcode, areacode, b_year, 3, pt_group3, death_group3 FROM bronze.death_age_copd
  UNION ALL SELECT 'copd', province_code, province_name, hospcode, areacode, b_year, 4, pt_group4, death_group4 FROM bronze.death_age_copd
  UNION ALL SELECT 'copd', province_code, province_name, hospcode, areacode, b_year, 5, pt_group5, death_group5 FROM bronze.death_age_copd

  UNION ALL SELECT 'coronary', province_code, province_name, hospcode, areacode, b_year, 1, pt_group1, death_group1 FROM bronze.death_age_coronary
  UNION ALL SELECT 'coronary', province_code, province_name, hospcode, areacode, b_year, 2, pt_group2, death_group2 FROM bronze.death_age_coronary
  UNION ALL SELECT 'coronary', province_code, province_name, hospcode, areacode, b_year, 3, pt_group3, death_group3 FROM bronze.death_age_coronary
  UNION ALL SELECT 'coronary', province_code, province_name, hospcode, areacode, b_year, 4, pt_group4, death_group4 FROM bronze.death_age_coronary
  UNION ALL SELECT 'coronary', province_code, province_name, hospcode, areacode, b_year, 5, pt_group5, death_group5 FROM bronze.death_age_coronary

  UNION ALL SELECT 'dm', province_code, province_name, hospcode, areacode, b_year, 1, pt_group1, death_group1 FROM bronze.death_age_dm
  UNION ALL SELECT 'dm', province_code, province_name, hospcode, areacode, b_year, 2, pt_group2, death_group2 FROM bronze.death_age_dm
  UNION ALL SELECT 'dm', province_code, province_name, hospcode, areacode, b_year, 3, pt_group3, death_group3 FROM bronze.death_age_dm
  UNION ALL SELECT 'dm', province_code, province_name, hospcode, areacode, b_year, 4, pt_group4, death_group4 FROM bronze.death_age_dm
  UNION ALL SELECT 'dm', province_code, province_name, hospcode, areacode, b_year, 5, pt_group5, death_group5 FROM bronze.death_age_dm

  UNION ALL SELECT 'ht', province_code, province_name, hospcode, areacode, b_year, 1, pt_group1, death_group1 FROM bronze.death_age_ht
  UNION ALL SELECT 'ht', province_code, province_name, hospcode, areacode, b_year, 2, pt_group2, death_group2 FROM bronze.death_age_ht
  UNION ALL SELECT 'ht', province_code, province_name, hospcode, areacode, b_year, 3, pt_group3, death_group3 FROM bronze.death_age_ht
  UNION ALL SELECT 'ht', province_code, province_name, hospcode, areacode, b_year, 4, pt_group4, death_group4 FROM bronze.death_age_ht
  UNION ALL SELECT 'ht', province_code, province_name, hospcode, areacode, b_year, 5, pt_group5, death_group5 FROM bronze.death_age_ht
) u;

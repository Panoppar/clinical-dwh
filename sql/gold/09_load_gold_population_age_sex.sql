-- ============================================================================
-- Silver -> Gold: populate Dim_Population_By_Age_Sex.
-- Run AFTER 08_create_gold_population_age_sex.sql.
--
-- silver.population_reference_age_sex only carries a Thai province name
-- (sourced from DOPA, which is Thai-only). English names are enriched here
-- via silver.thai_geography, same pattern as 07_load_gold_population_reference.sql.
-- ============================================================================

USE gold;

INSERT INTO Dim_Population_By_Age_Sex (
  scope, province_code, province_name_th, province_name_en,
  sex, age_label, age_exact, age_qualifier, year_be, year_ce, population_count
)
SELECT
  p.scope,
  p.province_code,
  p.province_name AS province_name_th,
  g.province_name_en,
  p.sex,
  p.age_label,
  p.age_exact,
  p.age_qualifier,
  p.year_be,
  p.year_ce,
  p.population_count
FROM silver.population_reference_age_sex p
LEFT JOIN (
  SELECT DISTINCT province_code, province_name_en FROM silver.thai_geography
) g ON g.province_code = p.province_code;

-- ============================================================================
-- Bronze -> Silver transform: external population reference data.
-- Run AFTER 03_create_silver_reference_tables.sql.
-- ============================================================================

USE silver;

-- ---------------------------------------------------------------------------
-- population_reference_subdistrict
-- Source file (stat_t.txt) carries the FULL administrative rollup in one
-- table: country/province/district/subdistrict/village totals are all
-- present as different rows, distinguished by which code columns are '0'.
-- `grain_level` makes that explicit instead of forcing every query to
-- re-derive it from raw code comparisons.
--
-- IMPORTANT: this is a 28-point year-end time series (yymm = '3612'..'6312',
-- Dec 1993 - Dec 2020 CE), not a single current snapshot. Any aggregate
-- query must GROUP BY yymm (or filter to one) or totals will be summed
-- across all 28 years.
-- ---------------------------------------------------------------------------
INSERT INTO population_reference_subdistrict (
  province_code, province_name, regoffice_code, regoffice_name,
  subdistrict_code, subdistrict_name, village_code, village_name,
  grain_level, male, female, total, house, yymm
)
SELECT
  b.province_code,
  TRIM(b.province_name),
  b.regoffice_code,
  NULLIF(TRIM(b.regoffice_name), ''),
  b.subdistrict_code,
  NULLIF(TRIM(b.subdistrict_name), ''),
  b.village_code,
  NULLIF(TRIM(b.village_name), ''),
  CASE
    WHEN b.province_code = '0' THEN 'country'
    WHEN b.regoffice_code = '0' THEN 'province'
    WHEN b.subdistrict_code = '0' THEN 'district'
    WHEN b.village_code = '0' THEN 'subdistrict'
    ELSE 'village'
  END AS grain_level,
  CAST(REPLACE(b.male_raw, ',', '') AS UNSIGNED) AS male,
  CAST(REPLACE(b.female_raw, ',', '') AS UNSIGNED) AS female,
  CAST(REPLACE(b.total_raw, ',', '') AS UNSIGNED) AS total,
  CAST(REPLACE(b.house_raw, ',', '') AS UNSIGNED) AS house,
  b.yymm
FROM bronze.dopa_population_monthly b;

-- ---------------------------------------------------------------------------
-- population_reference_age_sex
-- Province names are resolved from the DOPA table we just loaded (self-
-- consistent with our own ingested data) rather than a hardcoded lookup.
-- ---------------------------------------------------------------------------
INSERT INTO population_reference_age_sex (
  scope, province_code, province_name, indicator_code, indicator_name_en,
  is_headline_total, sex, age_label, age_exact,
  age_qualifier, year_be, year_ce, population_count
)
SELECT
  IF(b.cwt_code = '_T', 'national', 'province') AS scope,
  IF(b.cwt_code = '_T', NULL, b.cwt_code) AS province_code,
  prov.province_name,
  b.pop_ind AS indicator_code,
  -- Names decoded from the source's own SDMX structure file
  -- (5_NSO/reg_structure.xml), not guessed.
  CASE b.pop_ind
    WHEN 'DEM_IND24'  THEN 'Population from registration (TOTAL)'
    WHEN 'DEM_IND109' THEN 'Registered in a household registration'
    WHEN 'DEM_IND48'  THEN 'Central house registration'
    WHEN 'DEM_IND50'  THEN 'During move (mid-transfer)'
    ELSE b.pop_ind
  END AS indicator_name_en,
  IF(b.pop_ind = 'DEM_IND24', 1, 0) AS is_headline_total,
  CASE b.sex_code WHEN '_T' THEN 'Total' WHEN 'M' THEN 'Male' WHEN 'F' THEN 'Female' ELSE b.sex_code END AS sex,
  b.age_code AS age_label,
  -- Y_GT / Y_LT are handled alongside Y_GE / Y_LE: the source uses
  -- Y_GT100 ("over 100") for its open-ended top bracket, which an
  -- earlier version of this CASE silently dropped into 'other' with a
  -- NULL age_exact -- quietly excluding the oldest cohort from any
  -- age_exact filter.
  CASE
    WHEN b.age_code REGEXP '^Y[0-9]+$' THEN CAST(SUBSTRING(b.age_code, 2) AS UNSIGNED)
    WHEN b.age_code REGEXP '^Y_(LE|GE|GT|LT)[0-9]+$' THEN CAST(SUBSTRING(b.age_code, 5) AS UNSIGNED)
    ELSE NULL
  END AS age_exact,
  CASE
    WHEN b.age_code = '_T' THEN 'total'
    WHEN b.age_code REGEXP '^Y[0-9]+$' THEN 'exact'
    WHEN b.age_code REGEXP '^Y_LE[0-9]+$' THEN 'le'
    WHEN b.age_code REGEXP '^Y_GE[0-9]+$' THEN 'ge'
    WHEN b.age_code REGEXP '^Y_GT[0-9]+$' THEN 'gt'
    WHEN b.age_code REGEXP '^Y_LT[0-9]+$' THEN 'lt'
    ELSE 'other'
  END AS age_qualifier,
  CAST(b.time_period AS UNSIGNED) AS year_be,
  CAST(b.time_period AS UNSIGNED) - 543 AS year_ce,
  CASE WHEN b.obs_value REGEXP '^[0-9]+(\\.[0-9]+)?$'
       THEN ROUND(CAST(b.obs_value AS DECIMAL(15,2)))
       ELSE NULL
  END AS population_count
FROM bronze.nso_population_registration b
LEFT JOIN (
  SELECT DISTINCT province_code, province_name
  FROM population_reference_subdistrict
  WHERE grain_level = 'province'
) prov ON prov.province_code = b.cwt_code
WHERE b.sex_code IS NOT NULL
  AND b.age_code IS NOT NULL
  AND b.cwt_code IS NOT NULL
  AND b.time_period IS NOT NULL;

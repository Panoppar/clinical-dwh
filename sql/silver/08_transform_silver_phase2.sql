-- ============================================================================
-- Bronze -> Silver transform: Phase 2 shared-drive data.
-- Run AFTER 07_create_silver_phase2_tables.sql.
-- Note: `count_2567`/`count_2568` columns are labeled by their source Thai
-- Buddhist-Era year (BE 2567 = CE 2024, BE 2568 = CE 2025) rather than
-- renamed, since that's how the source itself distinguishes them.
-- ============================================================================

USE silver;

-- ---------------------------------------------------------------------------
-- HDC disease surveillance (b_year is Thai BE -> convert to CE)
-- ---------------------------------------------------------------------------
INSERT INTO hdc_disease_pop_age
SELECT
  disease, province_code, hospcode, areacode,
  CAST(NULLIF(TRIM(b_year), '') AS SIGNED) - 543 AS year_ce,
  CAST(NULLIF(TRIM(pop_group1), '') AS SIGNED), CAST(NULLIF(TRIM(result_group1), '') AS SIGNED),
  CAST(NULLIF(TRIM(pop_group2), '') AS SIGNED), CAST(NULLIF(TRIM(result_group2), '') AS SIGNED),
  CAST(NULLIF(TRIM(pop_group3), '') AS SIGNED), CAST(NULLIF(TRIM(result_group3), '') AS SIGNED),
  CAST(NULLIF(TRIM(pop_group4), '') AS SIGNED), CAST(NULLIF(TRIM(result_group4), '') AS SIGNED),
  CAST(NULLIF(TRIM(pop_group5), '') AS SIGNED), CAST(NULLIF(TRIM(result_group5), '') AS SIGNED)
FROM bronze.hdc_disease_pop_age;

INSERT INTO hdc_disease_incidence
SELECT
  disease, province_code, hospcode, areacode,
  CAST(NULLIF(TRIM(b_year), '') AS SIGNED) - 543 AS year_ce,
  CAST(NULLIF(TRIM(target), '') AS SIGNED), CAST(NULLIF(TRIM(result), '') AS SIGNED)
FROM bronze.hdc_disease_incidence;

INSERT INTO hdc_disease_death_age
SELECT
  disease, province_code, hospcode, areacode,
  CAST(NULLIF(TRIM(b_year), '') AS SIGNED) - 543 AS year_ce,
  CAST(NULLIF(TRIM(pt_group1), '') AS SIGNED), CAST(NULLIF(TRIM(death_group1), '') AS SIGNED),
  CAST(NULLIF(TRIM(pt_group2), '') AS SIGNED), CAST(NULLIF(TRIM(death_group2), '') AS SIGNED),
  CAST(NULLIF(TRIM(pt_group3), '') AS SIGNED), CAST(NULLIF(TRIM(death_group3), '') AS SIGNED),
  CAST(NULLIF(TRIM(pt_group4), '') AS SIGNED), CAST(NULLIF(TRIM(death_group4), '') AS SIGNED),
  CAST(NULLIF(TRIM(pt_group5), '') AS SIGNED), CAST(NULLIF(TRIM(death_group5), '') AS SIGNED)
FROM bronze.hdc_disease_death_age;

-- ---------------------------------------------------------------------------
-- DDS yearly disease ranking (year is already CE in this source, unlike HDC)
-- ---------------------------------------------------------------------------
INSERT INTO dds_yearly_disease_ranking
SELECT
  province_code, TRIM(province_name),
  CAST(NULLIF(TRIM(year), '') AS SIGNED),
  TRIM(disease),
  CAST(NULLIF(TRIM(case_count), '') AS DECIMAL(15,2)),
  CAST(NULLIF(TRIM(case_fatality_pct), '') AS DECIMAL(6,2)),
  CAST(NULLIF(TRIM(death_count), '') AS DECIMAL(15,2)),
  CAST(NULLIF(TRIM(rate_per_100k), '') AS DECIMAL(10,2)),
  CAST(NULLIF(TRIM(rank_by_cases), '') AS SIGNED),
  CAST(NULLIF(TRIM(implied_population), '') AS DECIMAL(15,2)),
  IF(LOWER(TRIM(is_provisional)) = 'true', 1, 0),
  note
FROM bronze.dds_yearly_disease_ranking;

-- ---------------------------------------------------------------------------
-- Lat Krabang population by subdistrict — pivot wide (male/female/total)
-- to long (sex, count); `total` is dropped since it's male+female and would
-- double-count if summed alongside the sex-level rows.
-- ---------------------------------------------------------------------------
INSERT INTO lat_krabang_population_by_subdistrict (subdistrict_name_th, sex, count)
SELECT TRIM(subdistrict_name_th), 'male', CAST(REPLACE(male, ',', '') AS SIGNED)
FROM bronze.lat_krabang_population_by_subdistrict WHERE subdistrict_name_th IS NOT NULL AND TRIM(subdistrict_name_th) <> 'รวม'
UNION ALL
SELECT TRIM(subdistrict_name_th), 'female', CAST(REPLACE(female, ',', '') AS SIGNED)
FROM bronze.lat_krabang_population_by_subdistrict WHERE subdistrict_name_th IS NOT NULL AND TRIM(subdistrict_name_th) <> 'รวม';

INSERT INTO lat_krabang_deaths_by_subdistrict (subdistrict_name_th, sex, count)
SELECT TRIM(subdistrict_name_th), 'male', CAST(REPLACE(male, ',', '') AS SIGNED)
FROM bronze.lat_krabang_deaths_by_subdistrict WHERE subdistrict_name_th IS NOT NULL AND TRIM(subdistrict_name_th) <> 'รวม'
UNION ALL
SELECT TRIM(subdistrict_name_th), 'female', CAST(REPLACE(female, ',', '') AS SIGNED)
FROM bronze.lat_krabang_deaths_by_subdistrict WHERE subdistrict_name_th IS NOT NULL AND TRIM(subdistrict_name_th) <> 'รวม';

-- ---------------------------------------------------------------------------
-- Lat Krabang points of interest — consolidated from 7 bronze tables
-- ---------------------------------------------------------------------------
INSERT INTO lat_krabang_points_of_interest (poi_type, name_th, address_th, attributes, source_added_date)
SELECT 'university', TRIM(name_th), TRIM(address_th), NULL, STR_TO_DATE(adddate, '%Y-%m-%d')
FROM bronze.lat_krabang_universities
UNION ALL
SELECT 'vocational_college', TRIM(name_th), TRIM(address_th), NULL, STR_TO_DATE(adddate, '%Y-%m-%d')
FROM bronze.lat_krabang_vocational_colleges
UNION ALL
SELECT 'school', TRIM(name_th), NULL,
  JSON_OBJECT(
    'student_num', CAST(NULLIF(TRIM(student_num), '') AS UNSIGNED),
    'classroom_num', CAST(NULLIF(TRIM(classroom_num), '') AS UNSIGNED),
    'teacher_num', CAST(NULLIF(TRIM(teacher_num), '') AS UNSIGNED)
  ),
  STR_TO_DATE(adddate, '%Y-%m-%d')
FROM bronze.lat_krabang_schools
UNION ALL
SELECT 'hospital', TRIM(name_th), TRIM(address_th), NULL, STR_TO_DATE(adddate, '%Y-%m-%d')
FROM bronze.lat_krabang_hospitals
UNION ALL
SELECT 'religious_site', TRIM(name_th), TRIM(address_th), NULL, STR_TO_DATE(adddate, '%Y-%m-%d')
FROM bronze.lat_krabang_religious_sites
UNION ALL
SELECT 'risk_point', TRIM(risk_name_th), NULL,
  JSON_OBJECT('risk_type', risk_type, 'flags', JSON_ARRAY(r1, r2, r3, r4, r5, r6)),
  STR_TO_DATE(adddate, '%Y-%m-%d')
FROM bronze.lat_krabang_risk_points
UNION ALL
SELECT 'business', TRIM(business_name_th), TRIM(address_th),
  JSON_OBJECT('investment_thb', CAST(NULLIF(TRIM(investment_thb), '') AS DECIMAL(15,2)), 'type_code', business_type_code),
  STR_TO_DATE(adddate, '%Y-%m-%d')
FROM bronze.lat_krabang_businesses;

-- ---------------------------------------------------------------------------
-- KMCH catchment places
-- ---------------------------------------------------------------------------
INSERT INTO kmch_catchment_places
SELECT
  TRIM(category), TRIM(place_name_th), TRIM(place_name_en), TRIM(address_th),
  TRIM(subdistrict_th), TRIM(district_th), TRIM(province_th),
  CAST(NULLIF(TRIM(avg_distance_km), '') AS DECIMAL(6,2)),
  CAST(NULLIF(TRIM(avg_travel_time_mins), '') AS SIGNED),
  TRIM(market_potential)
FROM bronze.kmch_catchment_places;

-- ---------------------------------------------------------------------------
-- Other health & population tables
-- ---------------------------------------------------------------------------
INSERT INTO other_health_disease_cases
SELECT TRIM(disease_th), CAST(REPLACE(count_2567,',','') AS SIGNED), CAST(REPLACE(count_2568,',','') AS SIGNED), CAST(REPLACE(diff,',','') AS SIGNED)
FROM bronze.other_health_disease_cases WHERE disease_th IS NOT NULL;

INSERT INTO other_health_subdistrict_cases
SELECT TRIM(district_th), TRIM(subdistrict_th), CAST(REPLACE(count_2567,',','') AS SIGNED), CAST(REPLACE(count_2568,',','') AS SIGNED), CAST(REPLACE(diff,',','') AS SIGNED)
FROM bronze.other_health_subdistrict_cases WHERE district_th IS NOT NULL;

INSERT INTO other_health_sick_by_group
SELECT
  CAST(NULLIF(TRIM(year_be), '') AS SIGNED) - 543, TRIM(province_th), TRIM(disease_group_th),
  CASE TRIM(sex_th) WHEN 'ชาย' THEN 'male' WHEN 'หญิง' THEN 'female' ELSE TRIM(sex_th) END,
  CAST(REPLACE(count, ',', '') AS SIGNED)
FROM bronze.other_health_sick_by_group WHERE year_be IS NOT NULL;

INSERT INTO other_health_disease_by_year
SELECT CAST(NULLIF(TRIM(year_be), '') AS SIGNED) - 543, TRIM(disease_th), CAST(REPLACE(count, ',', '') AS SIGNED)
FROM bronze.other_health_disease_by_year WHERE year_be IS NOT NULL;

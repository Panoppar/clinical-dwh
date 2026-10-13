-- ============================================================================
-- Silver -> Gold: populate local-area health & catchment tables.
-- Run AFTER 12_create_gold_local_health_facts.sql.
--
-- BE->CE mapping for the wide source columns: count_2567 = BE2567 = CE2024,
-- count_2568 = BE2568 = CE2025.
-- ============================================================================

USE gold;

-- Wide -> long pivot (one row per disease per year)
INSERT INTO Fact_Disease_Case_Trend (disease_th, year_ce, case_count, is_aggregate_row)
SELECT disease_th, 2024, count_2567, is_aggregate_row FROM silver.other_health_disease_cases
UNION ALL
SELECT disease_th, 2025, count_2568, is_aggregate_row FROM silver.other_health_disease_cases;

-- Wide -> long pivot (one row per district/subdistrict per year)
INSERT INTO Fact_Subdistrict_Case_Trend (district_th, subdistrict_th, year_ce, case_count, is_aggregate_row)
SELECT district_th, NULLIF(subdistrict_th, ''), 2024, count_2567, is_aggregate_row
FROM silver.other_health_subdistrict_cases
UNION ALL
SELECT district_th, NULLIF(subdistrict_th, ''), 2025, count_2568, is_aggregate_row
FROM silver.other_health_subdistrict_cases;

INSERT INTO Fact_Morbidity_By_Group (year_ce, province_th, disease_group_th, sex, case_count, is_aggregate_row)
SELECT year_ce, province_th, disease_group_th, sex, count, is_aggregate_row
FROM silver.other_health_sick_by_group;

INSERT INTO Fact_Disease_Annual_Count (year_ce, disease_th, case_count)
SELECT year_ce, disease_th, count
FROM silver.other_health_disease_by_year;

-- district_name_en enriched via thai_geography where the district name
-- matches; left NULL rather than guessed when it doesn't (the basic-shape
-- KMCH source files carry no address columns at all, so ~30% of rows have
-- no district to resolve in the first place).
INSERT INTO Dim_Catchment_Place (
  category, place_name_th, place_name_en, subdistrict_th, district_th,
  district_name_en, province_th, avg_distance_km, avg_travel_time_mins, market_potential
)
SELECT
  k.category, k.place_name_th, k.place_name_en, k.subdistrict_th, k.district_th,
  tg.district_name_en, k.province_th,
  k.avg_distance_km, k.avg_travel_time_mins, k.market_potential
FROM silver.kmch_catchment_places k
LEFT JOIN (
  SELECT DISTINCT district_name_th, district_name_en FROM silver.thai_geography
) tg ON tg.district_name_th = k.district_th;

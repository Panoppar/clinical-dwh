USE gold;

-- DOPA, province level
INSERT INTO fact_population_by_area (geo_key, date_key, admin_level, male_count, female_count, total_count, house_count, source_system)
SELECT dg.geo_key, s.year_ce*10000 + s.month*100 + 1, 'province', s.male, s.female, s.total, s.house, 'dopa'
FROM silver.population_by_area_month s
JOIN dim_geography dg ON dg.admin_level = 'province' AND dg.province_code = s.cc_code
WHERE s.admin_level = 'province' AND s.is_rollup_row = 0;

-- DOPA, district level
INSERT INTO fact_population_by_area (geo_key, date_key, admin_level, male_count, female_count, total_count, house_count, source_system)
SELECT dg.geo_key, s.year_ce*10000 + s.month*100 + 1, 'district', s.male, s.female, s.total, s.house, 'dopa'
FROM silver.population_by_area_month s
JOIN dim_geography dg ON dg.admin_level = 'district' AND dg.province_code = s.cc_code AND dg.district_code = s.rcode_code
WHERE s.admin_level = 'district' AND s.is_rollup_row = 0;

-- DOPA, subdistrict level
INSERT INTO fact_population_by_area (geo_key, date_key, admin_level, male_count, female_count, total_count, house_count, source_system)
SELECT dg.geo_key, s.year_ce*10000 + s.month*100 + 1, 'subdistrict', s.male, s.female, s.total, s.house, 'dopa'
FROM silver.population_by_area_month s
JOIN dim_geography dg ON dg.admin_level = 'subdistrict'
    AND dg.province_code = s.cc_code AND dg.district_code = s.rcode_code AND dg.subdistrict_code = s.ccaatt_code
WHERE s.admin_level = 'subdistrict' AND s.is_rollup_row = 0;

-- other_health's population_by_tambon_national: same DOPA code scheme,
-- native grain is always subdistrict-level (confirmed at Silver build
-- time -- same source data as DOPA's own triplicated snapshot, just a
-- different delivery format for Dec 2025).
INSERT INTO fact_population_by_area (geo_key, date_key, admin_level, male_count, female_count, total_count, house_count, source_system)
SELECT dg.geo_key, s.year_ce*10000 + s.month*100 + 1, 'subdistrict', s.male, s.female, s.total, s.house, 'other_health'
FROM silver.population_by_tambon_national s
JOIN dim_geography dg ON dg.admin_level = 'subdistrict'
    AND dg.province_code = s.cc_code AND dg.district_code = s.rcode_code AND dg.subdistrict_code = s.ccaatt_code
WHERE s.is_rollup_row = 0;

USE gold;

-- Step 1: base grain + lag features, reusing the same exact-prior-period
-- self-join pattern as the OBT (see 09_transform_obt_population_by_geography.sql).
INSERT INTO feat_geography_month
    (geo_key, date_key, admin_level, province_code, district_code, subdistrict_code,
     year_ce, month, total_count, pop_density_proxy, sex_ratio, total_count_lag1, total_count_lag12)
SELECT
    f.geo_key, f.date_key, f.admin_level, dg.province_code, dg.district_code, dg.subdistrict_code,
    dd.year_ce, dd.month, f.total_count, f.total_count,
    CASE WHEN f.female_count IS NULL OR f.female_count = 0 THEN NULL
         ELSE ROUND(f.male_count / f.female_count * 100, 4) END,
    fm.total_count, fy.total_count
FROM fact_population_by_area f
JOIN dim_geography dg ON f.geo_key = dg.geo_key
JOIN dim_date dd ON f.date_key = dd.date_key
LEFT JOIN fact_population_by_area fm ON fm.geo_key = f.geo_key
    AND fm.date_key = CAST(DATE_FORMAT(dd.full_date - INTERVAL 1 MONTH, '%Y%m01') AS UNSIGNED)
LEFT JOIN fact_population_by_area fy ON fy.geo_key = f.geo_key
    AND fy.date_key = CAST(DATE_FORMAT(dd.full_date - INTERVAL 1 YEAR, '%Y%m01') AS UNSIGNED);

-- Step 1b: country + province rows for months DOPA doesn't cover, same
-- reasoning as agg_population_summary_yearly's Step 1b -- fact_population_by_area
-- never has a 'country' row, and DOPA's province series stops Dec-2020.
INSERT INTO feat_geography_month
    (geo_key, date_key, admin_level, province_code, district_code, subdistrict_code,
     year_ce, month, total_count, pop_density_proxy, total_count_lag1, total_count_lag12)
SELECT f.geo_key, f.date_key, dg.admin_level, dg.province_code, dg.district_code, dg.subdistrict_code,
    dd.year_ce, dd.month, f.population_count, f.population_count, fm.population_count, fy.population_count
FROM fact_population_age_sex f
JOIN dim_date dd ON f.date_key = dd.date_key
JOIN dim_age_sex das ON f.age_sex_key = das.age_sex_key
JOIN dim_population_component dc ON f.component_key = dc.component_key
JOIN dim_geography dg ON f.geo_key = dg.geo_key
LEFT JOIN fact_population_age_sex fm ON fm.geo_key = f.geo_key
    AND fm.date_key = CAST(DATE_FORMAT(dd.full_date - INTERVAL 1 MONTH, '%Y%m01') AS UNSIGNED)
    AND fm.age_sex_key = f.age_sex_key AND fm.component_key = f.component_key
LEFT JOIN fact_population_age_sex fy ON fy.geo_key = f.geo_key
    AND fy.date_key = CAST(DATE_FORMAT(dd.full_date - INTERVAL 1 YEAR, '%Y%m01') AS UNSIGNED)
    AND fy.age_sex_key = f.age_sex_key AND fy.component_key = f.component_key
WHERE f.source_system = 'nso' AND dc.component_code = 'DEM_IND24' AND das.sex = 'total' AND das.age_qualifier = 'total'
    AND NOT EXISTS (
        SELECT 1 FROM feat_geography_month ft
        WHERE ft.geo_key = f.geo_key AND ft.date_key = f.date_key
    );

-- Step 2: age-band percentages, same per-source normalization as
-- agg_population_summary_yearly's Step 2 but matched on exact date_key
-- (month grain) instead of year_ce.
CREATE TEMPORARY TABLE tmp_feat_age_band_pop AS
SELECT geo_key, date_key,
    CASE WHEN age_qualifier IN ('exact','le') AND age_exact < 15 THEN 'young'
         WHEN age_qualifier = 'exact' AND age_exact BETWEEN 15 AND 64 THEN 'working'
         WHEN age_qualifier IN ('exact','gt') AND age_exact >= 65 THEN 'elderly'
         ELSE NULL END AS age_band,
    population_count
FROM (
    SELECT f.geo_key, f.date_key, das.age_qualifier, das.age_exact, f.population_count
    FROM fact_population_age_sex f
    JOIN dim_age_sex das ON f.age_sex_key = das.age_sex_key
    WHERE f.source_system = 'nso' AND f.is_headline_total = 1 AND das.sex = 'total'

    UNION ALL

    SELECT f.geo_key, f.date_key, das.age_qualifier, das.age_exact, f.population_count
    FROM fact_population_age_sex f
    JOIN dim_age_sex das ON f.age_sex_key = das.age_sex_key
    JOIN dim_population_component dc ON f.component_key = dc.component_key
    WHERE f.source_system = 'other_health' AND dc.component_code = 'age_bracket'
        AND das.sex IN ('male', 'female')
) src;

CREATE TEMPORARY TABLE tmp_feat_age_band_summary AS
SELECT geo_key, date_key,
    SUM(CASE WHEN age_band = 'young' THEN population_count ELSE 0 END) AS young_pop,
    SUM(CASE WHEN age_band = 'working' THEN population_count ELSE 0 END) AS working_pop,
    SUM(CASE WHEN age_band = 'elderly' THEN population_count ELSE 0 END) AS elderly_pop
FROM tmp_feat_age_band_pop
WHERE age_band IS NOT NULL
GROUP BY geo_key, date_key;

UPDATE feat_geography_month ft
JOIN tmp_feat_age_band_summary t ON ft.geo_key = t.geo_key AND ft.date_key = t.date_key
SET
    ft.pct_age_0_14 = IF(ft.total_count IS NULL OR ft.total_count = 0, NULL, ROUND(t.young_pop / ft.total_count * 100, 4)),
    ft.pct_age_15_64 = IF(ft.total_count IS NULL OR ft.total_count = 0, NULL, ROUND(t.working_pop / ft.total_count * 100, 4)),
    ft.pct_age_65_plus = IF(ft.total_count IS NULL OR ft.total_count = 0, NULL, ROUND(t.elderly_pop / ft.total_count * 100, 4));

DROP TEMPORARY TABLE tmp_feat_age_band_pop;
DROP TEMPORARY TABLE tmp_feat_age_band_summary;

USE gold;

INSERT INTO obt_population_by_geography
    (geo_key, date_key, admin_level, province_name_th, district_name_th, subdistrict_name_th,
     year_ce, month, month_name, total_count, male_count, female_count, household_count,
     pop_growth_mom_pct, pop_growth_yoy_pct, persons_per_household, sex_ratio)
SELECT
    f.geo_key, f.date_key, f.admin_level,
    dg.province_name_th, dg.district_name_th, dg.subdistrict_name_th,
    dd.year_ce, dd.month, dd.month_name,
    f.total_count, f.male_count, f.female_count, f.house_count,
    CASE WHEN fm.total_count IS NULL OR fm.total_count = 0 THEN NULL
         ELSE ROUND((f.total_count - fm.total_count) / fm.total_count * 100, 4) END,
    CASE WHEN fy.total_count IS NULL OR fy.total_count = 0 THEN NULL
         ELSE ROUND((f.total_count - fy.total_count) / fy.total_count * 100, 4) END,
    CASE WHEN f.house_count IS NULL OR f.house_count = 0 THEN NULL
         ELSE ROUND(f.total_count / f.house_count, 4) END,
    CASE WHEN f.female_count IS NULL OR f.female_count = 0 THEN NULL
         ELSE ROUND(f.male_count / f.female_count * 100, 4) END
FROM fact_population_by_area f
JOIN dim_geography dg ON f.geo_key = dg.geo_key
JOIN dim_date dd ON f.date_key = dd.date_key
-- prior month: exact calendar month before, same geo (NULL if that exact
-- snapshot doesn't exist -- honest, not a guessed "previous available")
LEFT JOIN fact_population_by_area fm ON fm.geo_key = f.geo_key
    AND fm.date_key = CAST(DATE_FORMAT(dd.full_date - INTERVAL 1 MONTH, '%Y%m01') AS UNSIGNED)
-- prior year, same month
LEFT JOIN fact_population_by_area fy ON fy.geo_key = f.geo_key
    AND fy.date_key = CAST(DATE_FORMAT(dd.full_date - INTERVAL 1 YEAR, '%Y%m01') AS UNSIGNED);

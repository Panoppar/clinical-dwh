USE gold;

-- Step 1: base total_count (December snapshot) + YoY growth.
-- Dec-2025 specifically carries the same subdistrict from both 'dopa'
-- (its own triplicated html snapshot) and 'other_health'
-- (population_by_tambon_national) -- same underlying government data,
-- confirmed by inspection, just two delivery paths kept as separate Silver/
-- fact rows per this project's no-cross-source-merge rule. One row per
-- (geo_key, year) is required here though, so 'dopa' wins ties
-- (preferred as the primary source throughout this dimension build).
INSERT INTO agg_population_summary_yearly (geo_key, year_ce, admin_level, total_count, yoy_growth_pct)
SELECT geo_key, year_ce, admin_level, total_count, yoy_growth_pct
FROM (
    SELECT
        f.geo_key, dd.year_ce, f.admin_level, f.total_count,
        CASE WHEN fy.total_count IS NULL OR fy.total_count = 0 THEN NULL
             ELSE ROUND((f.total_count - fy.total_count) / fy.total_count * 100, 4) END AS yoy_growth_pct,
        ROW_NUMBER() OVER (
            PARTITION BY f.geo_key, dd.year_ce
            ORDER BY (f.source_system = 'dopa') DESC
        ) AS rn
    FROM fact_population_by_area f
    JOIN dim_date dd ON f.date_key = dd.date_key AND dd.month = 12
    LEFT JOIN fact_population_by_area fy ON fy.geo_key = f.geo_key
        AND fy.date_key = (dd.year_ce - 1) * 10000 + 1201
) ranked
WHERE rn = 1;

-- Step 1b: country + province rows for years DOPA doesn't cover.
-- fact_population_by_area never has a 'country' row at all (DOPA/
-- other_health only ever publish province/district/subdistrict), and
-- DOPA's own province-level series stops at Dec-2020 while NSO's
-- province age-breakdown is 2024-only -- confirmed by direct inspection,
-- not assumed. Without this step, country+province age_dependency_ratio/
-- aging_index/non_thai_national_pct would be structurally unreachable:
-- no base row would ever exist for the years NSO actually has data.
-- NSO's DEM_IND24 (sex='total', age_qualifier='total') is itself the
-- age-independent grand total for that geo+year, confirmed against the
-- already-verified real national figures (e.g. 65,951,210 for 2024).
INSERT INTO agg_population_summary_yearly (geo_key, year_ce, admin_level, total_count, yoy_growth_pct)
SELECT f.geo_key, dd.year_ce, dg.admin_level, f.population_count,
    CASE WHEN fy.population_count IS NULL OR fy.population_count = 0 THEN NULL
         ELSE ROUND((f.population_count - fy.population_count) / fy.population_count * 100, 4) END
FROM fact_population_age_sex f
JOIN dim_date dd ON f.date_key = dd.date_key
JOIN dim_age_sex das ON f.age_sex_key = das.age_sex_key
JOIN dim_population_component dc ON f.component_key = dc.component_key
JOIN dim_geography dg ON f.geo_key = dg.geo_key
LEFT JOIN fact_population_age_sex fy ON fy.geo_key = f.geo_key
    AND fy.date_key = (dd.year_ce - 1) * 10000 + 101
    AND fy.age_sex_key = f.age_sex_key AND fy.component_key = f.component_key
WHERE f.source_system = 'nso' AND dc.component_code = 'DEM_IND24' AND das.sex = 'total' AND das.age_qualifier = 'total'
    AND NOT EXISTS (
        SELECT 1 FROM agg_population_summary_yearly a
        WHERE a.geo_key = f.geo_key AND a.year_ce = dd.year_ce
    );

-- Step 2: age-band populations, normalized across the 2 source systems
-- into one consistent (geo_key, year_ce, age_band, population) shape --
-- NSO's headline indicator (DEM_IND24, sex='total') already has a
-- pre-summed total per age; other_health's age_bracket rows don't (only
-- male/female), so those are summed explicitly. Age-band boundaries:
-- young = exact age <15 (plus the Y_LE1-style "le" bucket); working =
-- exact age 15-64; elderly = exact age >=65 (plus the ">100" style "gt"
-- bucket).
CREATE TEMPORARY TABLE tmp_age_band_pop AS
SELECT geo_key, year_ce,
    CASE WHEN age_qualifier IN ('exact','le') AND age_exact < 15 THEN 'young'
         WHEN age_qualifier = 'exact' AND age_exact BETWEEN 15 AND 64 THEN 'working'
         WHEN age_qualifier IN ('exact','gt') AND age_exact >= 65 THEN 'elderly'
         ELSE NULL END AS age_band,
    population_count
FROM (
    -- NSO: country + province, sex='total', headline indicator only.
    SELECT f.geo_key, dd.year_ce, das.age_qualifier, das.age_exact, f.population_count
    FROM fact_population_age_sex f
    JOIN dim_date dd ON f.date_key = dd.date_key
    JOIN dim_age_sex das ON f.age_sex_key = das.age_sex_key
    WHERE f.source_system = 'nso' AND f.is_headline_total = 1 AND das.sex = 'total'

    UNION ALL

    -- other_health: Bangkok subdistricts, age_bracket component, male+female summed.
    SELECT f.geo_key, dd.year_ce, das.age_qualifier, das.age_exact, f.population_count
    FROM fact_population_age_sex f
    JOIN dim_date dd ON f.date_key = dd.date_key
    JOIN dim_age_sex das ON f.age_sex_key = das.age_sex_key
    JOIN dim_population_component dc ON f.component_key = dc.component_key
    WHERE f.source_system = 'other_health' AND dc.component_code = 'age_bracket'
        AND das.sex IN ('male', 'female')
) src;

CREATE TEMPORARY TABLE tmp_age_band_summary AS
SELECT geo_key, year_ce,
    SUM(CASE WHEN age_band = 'young' THEN population_count ELSE 0 END) AS young_pop,
    SUM(CASE WHEN age_band = 'working' THEN population_count ELSE 0 END) AS working_pop,
    SUM(CASE WHEN age_band = 'elderly' THEN population_count ELSE 0 END) AS elderly_pop
FROM tmp_age_band_pop
WHERE age_band IS NOT NULL
GROUP BY geo_key, year_ce;

UPDATE agg_population_summary_yearly a
JOIN tmp_age_band_summary t ON a.geo_key = t.geo_key AND a.year_ce = t.year_ce
SET
    a.age_dependency_ratio = IF(t.working_pop = 0, NULL, ROUND((t.young_pop + t.elderly_pop) / t.working_pop * 100, 4)),
    a.aging_index = IF(t.young_pop = 0, NULL, ROUND(t.elderly_pop / t.young_pop * 100, 4));

-- Step 3: non-Thai nationality % (NSO only -- DEM_IND49 / DEM_IND24, sex='total').
CREATE TEMPORARY TABLE tmp_non_thai AS
SELECT f24.geo_key, dd.year_ce,
    IF(f24.population_count = 0, NULL, ROUND(f49.population_count / f24.population_count * 100, 4)) AS non_thai_pct
FROM fact_population_age_sex f24
JOIN dim_date dd ON f24.date_key = dd.date_key
JOIN dim_age_sex das24 ON f24.age_sex_key = das24.age_sex_key
JOIN dim_population_component dc24 ON f24.component_key = dc24.component_key
JOIN fact_population_age_sex f49 ON f49.geo_key = f24.geo_key AND f49.date_key = f24.date_key
JOIN dim_age_sex das49 ON f49.age_sex_key = das49.age_sex_key
JOIN dim_population_component dc49 ON f49.component_key = dc49.component_key
WHERE dc24.source_system = 'nso' AND dc24.component_code = 'DEM_IND24' AND das24.sex = 'total' AND das24.age_qualifier = 'total'
    AND dc49.source_system = 'nso' AND dc49.component_code = 'DEM_IND49' AND das49.sex = 'total' AND das49.age_qualifier = 'total';

UPDATE agg_population_summary_yearly a
JOIN tmp_non_thai t ON a.geo_key = t.geo_key AND a.year_ce = t.year_ce
SET a.non_thai_national_pct = t.non_thai_pct;

DROP TEMPORARY TABLE tmp_age_band_pop;
DROP TEMPORARY TABLE tmp_age_band_summary;
DROP TEMPORARY TABLE tmp_non_thai;

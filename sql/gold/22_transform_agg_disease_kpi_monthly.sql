USE gold;

-- Case-fatality rate (DDS only -- the only source with both a case count
-- and a death count in the same row). YoY matched on
-- (health_region_code, disease_key, year-1) since DDS has no geo_key to
-- match on.
INSERT INTO agg_disease_kpi_monthly (geo_key, date_key, disease_key, year_ce, month, case_fatality_rate_pct, yoy_change_pct, kpi_type, source_system)
SELECT NULL, f.date_key, f.disease_key, dt.year_ce, NULL, f.case_fatality_rate_pct,
    CASE WHEN fy.case_fatality_rate_pct IS NULL OR fy.case_fatality_rate_pct = 0 THEN NULL
         ELSE ROUND((f.case_fatality_rate_pct - fy.case_fatality_rate_pct) / fy.case_fatality_rate_pct * 100, 4) END,
    'case_fatality', 'dds'
FROM fact_disease_event f
JOIN dim_date dt ON f.date_key = dt.date_key
LEFT JOIN fact_disease_event fy ON fy.health_region_code = f.health_region_code AND fy.disease_key = f.disease_key
    AND fy.date_key = (dt.year_ce - 1) * 10000 + 101
WHERE f.source_system = 'dds' AND f.case_fatality_rate_pct IS NOT NULL;

-- Target-attainment % (HDC's target/result KPI, both monthly and annual
-- grain). YoY matched on exact prior period, same disease_key +
-- (hospcode, areacode) -- the real unique-per-facility key here
-- (confirmed by direct check: areacode alone has a few duplicates, e.g.
-- the same catchment area covered by two different hospcodes, but
-- hospcode+areacode together is unique). geo_key alone would match
-- every other facility in the same district and fan out into a
-- many-to-many explosion (confirmed: an earlier geo_key-only join
-- produced 42.5M rows from 507K facts).
INSERT INTO agg_disease_kpi_monthly (geo_key, date_key, disease_key, year_ce, month, target_attainment_pct, yoy_change_pct, kpi_type, source_system)
SELECT f.geo_key, f.date_key, f.disease_key, dt.year_ce, dt.month,
    CASE WHEN f.target IS NULL OR f.target = 0 THEN NULL ELSE ROUND(f.result / f.target * 100, 4) END,
    CASE WHEN fy.target IS NULL OR fy.target = 0 OR f.target IS NULL OR f.target = 0 THEN NULL
         ELSE ROUND((f.result / f.target * 100) - (fy.result / fy.target * 100), 4) END,
    'target_attainment', 'hdc'
FROM fact_disease_incidence_hdc f
JOIN dim_date dt ON f.date_key = dt.date_key
LEFT JOIN fact_disease_incidence_hdc fy ON fy.hospcode = f.hospcode AND fy.areacode = f.areacode
    AND fy.disease_key = f.disease_key AND fy.grain = f.grain
    AND fy.date_key = CASE WHEN f.grain = 'monthly'
        THEN CAST(DATE_FORMAT(dt.full_date - INTERVAL 1 YEAR, '%Y%m01') AS UNSIGNED)
        ELSE (dt.year_ce - 1) * 10000 + 101 END;

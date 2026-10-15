USE gold;

-- Monthly grain: unpivot result10/11/12 (Oct-Dec of b_year_ce-1) and
-- result01..09 (Jan-Sep of b_year_ce) into one row per calendar month,
-- per the Thai government fiscal year convention (Oct-Sep).
INSERT INTO fact_disease_incidence_hdc (geo_key, date_key, disease_key, grain, hospcode, areacode, target, result, source_system)
SELECT dg.geo_key, v.date_key, dd.disease_key, 'monthly', s.hospcode, s.areacode, s.target, v.result_value, 'hdc'
FROM silver.hdc_incidence_monthly s
JOIN dim_disease dd ON dd.source_system = 'hdc' AND dd.disease_code = s.disease
LEFT JOIN dim_geography dg ON dg.admin_level = 'district' AND dg.province_code = s.province_code
    AND dg.district_code = SUBSTRING(s.areacode, 1, 4)
JOIN (
    SELECT silver_id, (b_year_ce - 1) * 10000 + 1001 AS date_key, result10 AS result_value FROM silver.hdc_incidence_monthly
    UNION ALL SELECT silver_id, (b_year_ce - 1) * 10000 + 1101, result11 FROM silver.hdc_incidence_monthly
    UNION ALL SELECT silver_id, (b_year_ce - 1) * 10000 + 1201, result12 FROM silver.hdc_incidence_monthly
    UNION ALL SELECT silver_id, b_year_ce * 10000 + 101, result01 FROM silver.hdc_incidence_monthly
    UNION ALL SELECT silver_id, b_year_ce * 10000 + 201, result02 FROM silver.hdc_incidence_monthly
    UNION ALL SELECT silver_id, b_year_ce * 10000 + 301, result03 FROM silver.hdc_incidence_monthly
    UNION ALL SELECT silver_id, b_year_ce * 10000 + 401, result04 FROM silver.hdc_incidence_monthly
    UNION ALL SELECT silver_id, b_year_ce * 10000 + 501, result05 FROM silver.hdc_incidence_monthly
    UNION ALL SELECT silver_id, b_year_ce * 10000 + 601, result06 FROM silver.hdc_incidence_monthly
    UNION ALL SELECT silver_id, b_year_ce * 10000 + 701, result07 FROM silver.hdc_incidence_monthly
    UNION ALL SELECT silver_id, b_year_ce * 10000 + 801, result08 FROM silver.hdc_incidence_monthly
    UNION ALL SELECT silver_id, b_year_ce * 10000 + 901, result09 FROM silver.hdc_incidence_monthly
) v ON v.silver_id = s.silver_id;

-- Annual grain: disease='ihd' only (confirmed by inspection), year grain
-- represented as Jan 1 of b_year_ce, same convention as fact_population_age_sex.
INSERT INTO fact_disease_incidence_hdc (geo_key, date_key, disease_key, grain, hospcode, areacode, target, result, target_alt, result_alt, source_system)
SELECT dg.geo_key, s.b_year_ce * 10000 + 101, dd.disease_key, 'annual', s.hospcode, s.areacode, s.target, s.result, s.target1, s.result1, 'hdc'
FROM silver.hdc_incidence_annual s
JOIN dim_disease dd ON dd.source_system = 'hdc' AND dd.disease_code = s.disease
LEFT JOIN dim_geography dg ON dg.admin_level = 'district' AND dg.province_code = s.province_code
    AND dg.district_code = SUBSTRING(s.areacode, 1, 4);

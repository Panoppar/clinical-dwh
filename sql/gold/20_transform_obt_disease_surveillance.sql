USE gold;

INSERT INTO obt_disease_surveillance
    (geo_key, date_key, disease_key, province_name_th, district_name_th, subdistrict_name_th,
     disease_name, year_ce, month, sex, health_region_code, case_count, death_count, rate_per_100k,
     case_fatality_rate_pct, grain, source_system)
SELECT
    f.geo_key, f.date_key, f.disease_key, dg.province_name_th, dg.district_name_th, dg.subdistrict_name_th,
    dd.disease_name, dt.year_ce, dt.month, das.sex, f.health_region_code, f.case_count, f.death_count,
    f.rate_per_100k, f.case_fatality_rate_pct, 'event_year', f.source_system
FROM fact_disease_event f
JOIN dim_date dt ON f.date_key = dt.date_key
JOIN dim_disease dd ON f.disease_key = dd.disease_key
LEFT JOIN dim_geography dg ON f.geo_key = dg.geo_key
LEFT JOIN dim_age_sex das ON f.age_sex_key = das.age_sex_key;

INSERT INTO obt_disease_surveillance
    (geo_key, date_key, disease_key, district_name_th, disease_name, year_ce, month,
     target, result, target_attainment_pct, grain, source_system)
SELECT
    f.geo_key, f.date_key, f.disease_key, dg.district_name_th, dd.disease_name, dt.year_ce, dt.month,
    f.target, f.result,
    CASE WHEN f.target IS NULL OR f.target = 0 THEN NULL ELSE ROUND(f.result / f.target * 100, 4) END,
    IF(f.grain = 'monthly', 'incidence_monthly', 'incidence_annual'), f.source_system
FROM fact_disease_incidence_hdc f
JOIN dim_date dt ON f.date_key = dt.date_key
JOIN dim_disease dd ON f.disease_key = dd.disease_key
LEFT JOIN dim_geography dg ON f.geo_key = dg.geo_key;

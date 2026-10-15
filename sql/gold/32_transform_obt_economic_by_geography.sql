USE gold;

INSERT INTO obt_economic_by_geography
    (geo_key, date_key, province_name_th, district_name_th, subdistrict_name_th, entity_name, entity_type,
     total_investment, total_workers, male_workers, female_workers, total_horsepower, source_system)
SELECT f.geo_key, f.date_key, dg.province_name_th, dg.district_name_th, dg.subdistrict_name_th,
    df.factory_name, 'factory', f.total_investment, f.total_workers, f.male_workers, f.female_workers, f.total_horsepower, 'factory_list'
FROM fact_factory_registration f
JOIN dim_factory df ON f.factory_key = df.factory_key
LEFT JOIN dim_geography dg ON f.geo_key = dg.geo_key;

INSERT INTO obt_economic_by_geography
    (geo_key, province_name_th, district_name_th, subdistrict_name_th, entity_name, entity_type,
     total_investment, avg_distance_km, market_potential, student_count, source_system)
SELECT f.geo_key, dg.province_name_th, dg.district_name_th, dg.subdistrict_name_th,
    dp.place_name, dp.source_system, f.investment_thb, f.avg_distance_km, f.market_potential, f.student_count, dp.source_system
FROM fact_catchment_place f
JOIN dim_place dp ON f.place_key = dp.place_key
LEFT JOIN dim_geography dg ON f.geo_key = dg.geo_key;

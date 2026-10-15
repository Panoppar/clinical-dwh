USE gold;

-- kmch_catchment_places: compound (district, sub_district) match, same
-- approach as fact_factory_registration -- resolved to at most one
-- geo_key per distinct text pair BEFORE joining to the main query, since
-- joining straight to dim_geography can fan out when a subdistrict name
-- is ambiguous within province_code='10' (the exact bug that produced
-- 815 duplicate rows in fact_factory_registration before being caught).
CREATE TEMPORARY TABLE kmch_geo_lookup AS
SELECT s.district, s.sub_district, MIN(dg.geo_key) AS geo_key
FROM (SELECT DISTINCT district, sub_district FROM silver.kmch_catchment_places) s
LEFT JOIN dim_geography dg ON dg.admin_level = 'subdistrict' AND dg.province_code = '10'
    AND dg.subdistrict_name_th = TRIM(s.sub_district)
LEFT JOIN dim_geography ddist ON ddist.admin_level = 'district' AND ddist.province_code = '10'
    AND ddist.district_code = dg.district_code AND ddist.district_name_th LIKE CONCAT('%', TRIM(s.district), '%')
WHERE ddist.geo_key IS NOT NULL
GROUP BY s.district, s.sub_district;

INSERT INTO fact_catchment_place (place_key, geo_key, avg_distance_km, avg_travel_time_mins, market_potential)
SELECT dp.place_key, gl.geo_key, s.avg_distance_km, s.avg_travel_time_mins, s.market_potential
FROM silver.kmch_catchment_places s
JOIN dim_place dp ON dp.source_system = 'kmch' AND dp.silver_id = s.silver_id
LEFT JOIN kmch_geo_lookup gl ON gl.district = s.district AND gl.sub_district = s.sub_district;

DROP TEMPORARY TABLE kmch_geo_lookup;

-- business_establishment: no structured geography.
INSERT INTO fact_catchment_place (place_key, investment_thb)
SELECT dp.place_key, s.investment_thb
FROM silver.business_establishment s
JOIN dim_place dp ON dp.source_system = 'business' AND dp.silver_id = s.silver_id;

-- religious_site: no structured geography, no numeric measures.
INSERT INTO fact_catchment_place (place_key)
SELECT dp.place_key FROM silver.religious_site s
JOIN dim_place dp ON dp.source_system = 'religious' AND dp.silver_id = s.silver_id;

-- safety_risk_point: no geography column survived the Bronze->Silver
-- transform (confirmed: silver.safety_risk_point has no district/
-- address column at all, unlike the raw bronze table) -- geo_key stays
-- NULL, same as the other address-text-only sources.
INSERT INTO fact_catchment_place (place_key, risk_flag_1, risk_flag_2, risk_flag_3, risk_flag_4, risk_flag_5, risk_flag_6)
SELECT dp.place_key, s.r1, s.r2, s.r3, s.r4, s.r5, s.r6
FROM silver.safety_risk_point s
JOIN dim_place dp ON dp.source_system = 'safety_risk' AND dp.silver_id = s.silver_id;

-- edu_school: no structured geography, has the full student/teacher measure set.
INSERT INTO fact_catchment_place (place_key, student_count, classroom_count, teacher_count, student_m6_count, student_p3_count)
SELECT dp.place_key, s.student_count, s.classroom_count, s.teacher_count, s.student_m6_count, s.student_p3_count
FROM silver.edu_school s
JOIN dim_place dp ON dp.source_system = 'edu_school' AND dp.silver_id = s.silver_id;

-- edu_university, edu_vocational, hospital: no structured geography, no numeric measures.
INSERT INTO fact_catchment_place (place_key)
SELECT dp.place_key FROM silver.edu_university s
JOIN dim_place dp ON dp.source_system = 'edu_university' AND dp.silver_id = s.silver_id;

INSERT INTO fact_catchment_place (place_key)
SELECT dp.place_key FROM silver.edu_vocational_college s
JOIN dim_place dp ON dp.source_system = 'edu_vocational' AND dp.silver_id = s.silver_id;

INSERT INTO fact_catchment_place (place_key)
SELECT dp.place_key FROM silver.health_hospital s
JOIN dim_place dp ON dp.source_system = 'hospital' AND dp.silver_id = s.silver_id;

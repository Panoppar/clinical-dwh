USE gold;

-- geo_lookup resolves each distinct (district, sub_district) text pair
-- to AT MOST ONE geo_key up front, via a GROUP BY -- joining the main
-- query straight to dim_geography (even with the district-name
-- cross-check) can still return multiple candidate rows per source row
-- when a subdistrict name is ambiguous within province_code='10'
-- (confirmed: "อนุสาวรีย์" alone matches more than one subdistrict
-- candidate before district disambiguation narrows it, and the
-- disambiguation step was applied too late, after the fan-out already
-- happened -- this produced 815 duplicate fact rows before being
-- caught). MIN() picks a single winner if, after disambiguation, more
-- than one candidate somehow still remains.
CREATE TEMPORARY TABLE geo_lookup AS
SELECT s.district, s.sub_district, MIN(dg.geo_key) AS geo_key
FROM (SELECT DISTINCT district, sub_district FROM silver.factory_list) s
LEFT JOIN dim_geography dg ON dg.admin_level = 'subdistrict' AND dg.province_code = '10'
    AND dg.subdistrict_name_th = TRIM(s.sub_district)
LEFT JOIN dim_geography ddist ON ddist.admin_level = 'district' AND ddist.province_code = '10'
    AND ddist.district_code = dg.district_code AND ddist.district_name_th LIKE CONCAT('%', TRIM(s.district), '%')
WHERE ddist.geo_key IS NOT NULL
GROUP BY s.district, s.sub_district;

INSERT INTO fact_factory_registration
    (factory_key, geo_key, date_key, building_value, land_value, machinery_value, working_capital,
     total_investment, male_workers, female_workers, total_workers, total_horsepower, factory_area_sqm, building_area_sqm)
SELECT
    df.factory_key, gl.geo_key, s.permit_year_ce * 10000 + 101,
    s.building_value, s.land_value, s.machinery_value, s.working_capital, s.total_investment,
    s.male_workers, s.female_workers, s.total_workers, s.total_horsepower, s.factory_area_sqm, s.building_area_sqm
FROM silver.factory_list s
JOIN dim_factory df ON df.factory_reg_no = s.factory_reg_no
LEFT JOIN geo_lookup gl ON gl.district = s.district AND gl.sub_district = s.sub_district;

DROP TEMPORARY TABLE geo_lookup;

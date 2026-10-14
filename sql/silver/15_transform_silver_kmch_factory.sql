USE silver;

INSERT INTO kmch_catchment_places
  (category, place_name_th, place_name_en, address, sub_district, district, province,
   avg_distance_km, avg_travel_time_mins, market_potential)
SELECT raw_category, raw_place_name_th, raw_place_name_en, raw_address, raw_sub_district,
  raw_district, raw_province,
  CAST(NULLIF(raw_avg_distance_km, '') AS DECIMAL(10,2)),
  CAST(NULLIF(raw_avg_travel_time_mins, '') AS SIGNED),
  raw_market_potential
FROM bronze.kmch_catchment_places;

INSERT INTO factory_list
  (factory_reg_no, factory_fid, tsic_code, factory_type_code, factory_type_desc, category, class,
   permit_year_be, permit_year_ce, factory_name, owner_name, business_activity, address_no, moo,
   soi, road, sub_district, district, province_code, province, postal_code, phone,
   building_value, land_value, machinery_value, working_capital, total_investment,
   male_workers, female_workers, total_workers, total_horsepower, factory_area_sqm, building_area_sqm)
SELECT
  raw_factory_reg_no, raw_factory_fid, raw_tsic_code, raw_factory_type_code, raw_factory_type_desc,
  raw_category, CAST(NULLIF(raw_class, '') AS UNSIGNED),
  CAST(NULLIF(source_permit_year_be, '') AS UNSIGNED),
  CAST(NULLIF(source_permit_year_be, '') AS UNSIGNED) - 543,
  raw_factory_name, raw_owner_name, raw_business_activity, raw_address_no, raw_moo, raw_soi, raw_road,
  raw_sub_district, raw_district, raw_province_code, raw_province, raw_postal_code, raw_phone,
  raw_building_value, raw_land_value, raw_machinery_value, raw_working_capital, raw_total_investment,
  raw_male_workers, raw_female_workers, raw_total_workers, raw_total_horsepower,
  raw_factory_area_sqm, raw_building_area_sqm
FROM bronze.factory_list;

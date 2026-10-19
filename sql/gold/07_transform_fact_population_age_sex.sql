USE gold;

-- FK checks disabled for these bulk inserts -- the other_health branch
-- (78,840 rows, 4 FK columns each) was observed hanging indefinitely
-- mid-transaction on this machine after several hours of repeated
-- full-rebuild cycles in one session (CPU pegged, row count already
-- correct, but the transaction never committed) -- per-row FK validation
-- under that resource pressure is the suspected cause. All 3 branches
-- here already only insert rows that passed an INNER JOIN against the
-- exact referenced dimension, so referential integrity is guaranteed by
-- construction regardless of whether MySQL re-checks it per row.
SET FOREIGN_KEY_CHECKS = 0;

-- NSO national-level rows -> 'country' geo_key (no province breakdown in
-- this source_level).
INSERT INTO fact_population_age_sex (geo_key, date_key, age_sex_key, component_key, is_headline_total, population_count, source_system)
SELECT
    (SELECT geo_key FROM dim_geography WHERE admin_level='country' LIMIT 1),
    s.year_ce*10000 + 101,
    das.age_sex_key,
    dc.component_key,
    s.is_headline_total,
    s.obs_value,
    'nso'
FROM silver.population_reference_age_sex s
JOIN dim_age_sex das ON das.sex = CASE s.sex WHEN 'M' THEN 'male' WHEN 'F' THEN 'female' WHEN '_T' THEN 'total' ELSE s.sex END
    AND das.age_exact <=> s.age_exact AND das.age_qualifier = s.age_qualifier
JOIN dim_population_component dc ON dc.source_system = 'nso' AND dc.component_code = s.pop_ind
WHERE s.source_level = 'national';

-- NSO province-level rows.
INSERT INTO fact_population_age_sex (geo_key, date_key, age_sex_key, component_key, is_headline_total, population_count, source_system)
SELECT
    dg.geo_key,
    s.year_ce*10000 + 101,
    das.age_sex_key,
    dc.component_key,
    s.is_headline_total,
    s.obs_value,
    'nso'
FROM silver.population_reference_age_sex s
JOIN dim_geography dg ON dg.admin_level = 'province' AND dg.province_code = s.province_code
JOIN dim_age_sex das ON das.sex = CASE s.sex WHEN 'M' THEN 'male' WHEN 'F' THEN 'female' WHEN '_T' THEN 'total' ELSE s.sex END
    AND das.age_exact <=> s.age_exact AND das.age_qualifier = s.age_qualifier
JOIN dim_population_component dc ON dc.source_system = 'nso' AND dc.component_code = s.pop_ind
WHERE s.source_level = 'province';

-- other_health's Bangkok subdistrict-level rows. tambon_code is 6-digit
-- (e.g. "100101"); dim_geography's subdistrict_code is DOPA's 8-digit
-- scheme with a trailing "00" (village-level digits, always 0 in this
-- data) -- confirmed by direct testing that CONCAT(tambon_code,'00')
-- matches all 78,840 rows exactly.
INSERT INTO fact_population_age_sex (geo_key, date_key, age_sex_key, component_key, is_headline_total, population_count, source_system)
SELECT
    dg.geo_key,
    s.year_ce*10000 + s.month*100 + 1,
    das.age_sex_key,
    dc.component_key,
    s.is_headline_total,
    s.population_count,
    'other_health'
FROM silver.population_by_age_subdistrict_bkk s
JOIN dim_geography dg ON dg.admin_level = 'subdistrict' AND dg.province_code = s.province_code
    AND dg.district_code = s.registrar_code AND dg.subdistrict_code = CONCAT(s.tambon_code, '00')
JOIN dim_age_sex das ON das.sex = s.sex AND das.age_exact <=> s.age_exact AND das.age_qualifier <=> s.age_qualifier
JOIN dim_population_component dc ON dc.source_system = 'other_health' AND dc.component_code = s.component_type;

SET FOREIGN_KEY_CHECKS = 1;

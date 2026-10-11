-- ============================================================================
-- Bronze -> Silver transform: Thai geography + zip-code admin crosswalk.
-- Run AFTER 05_create_silver_crosswalk_tables.sql.
--
-- Note on codes: province_code is derived as FLOOR(district_code / 100),
-- NOT from thai_geo_province.id. The source dataset's own province.id is an
-- unrelated internal sequential key (1, 2, 3...), while district_id already
-- embeds the real official 2-digit province code as its first two digits
-- (e.g. district 1011 "Lat Krabang" -> province 10 "Bangkok") — the same
-- scheme DOPA's data uses. province.id is still used (via district's own
-- province_id FK) purely to look up the province's name text.
-- ============================================================================

USE silver;

-- ---------------------------------------------------------------------------
-- thai_geography
-- ---------------------------------------------------------------------------
INSERT INTO thai_geography (
  subdistrict_code, subdistrict_name_th, subdistrict_name_en, zip_code,
  district_code, district_name_th, district_name_en,
  province_code, province_name_th, province_name_en
)
SELECT
  CAST(sd.id AS UNSIGNED) AS subdistrict_code,
  NULLIF(TRIM(sd.name_th), ''),
  NULLIF(TRIM(sd.name_en), ''),
  NULLIF(TRIM(sd.zip_code), ''),
  CAST(sd.district_id AS UNSIGNED) AS district_code,
  NULLIF(TRIM(d.name_th), ''),
  NULLIF(TRIM(d.name_en), ''),
  FLOOR(CAST(sd.district_id AS UNSIGNED) / 100) AS province_code,
  NULLIF(TRIM(p.name_th), ''),
  NULLIF(TRIM(p.name_en), '')
FROM bronze.thai_geo_subdistrict sd
JOIN bronze.thai_geo_district d ON d.id = sd.district_id
JOIN bronze.thai_geo_province p ON p.id = d.province_id
WHERE sd.id IS NOT NULL AND sd.id REGEXP '^[0-9]+$';

-- ---------------------------------------------------------------------------
-- zip_code_admin_crosswalk — full fidelity, one row per (zip, subdistrict)
-- ---------------------------------------------------------------------------
INSERT INTO zip_code_admin_crosswalk (
  zip_code, subdistrict_code, subdistrict_name_en,
  district_code, district_name_en, province_code, province_name_en
)
SELECT
  zip_code, subdistrict_code, subdistrict_name_en,
  district_code, district_name_en, province_code, province_name_en
FROM thai_geography
WHERE zip_code IS NOT NULL;

-- ---------------------------------------------------------------------------
-- zip_code_primary_district — one row per zip_code, resolved to the
-- district with the most matching subdistricts (tie-break: lowest
-- district_code), flagged when the zip genuinely spans multiple districts.
-- ---------------------------------------------------------------------------
INSERT INTO zip_code_primary_district (
  zip_code, district_code, district_name_th, district_name_en,
  province_code, province_name_th, province_name_en, district_count, is_ambiguous
)
WITH zip_district_counts AS (
  SELECT zip_code, district_code, COUNT(*) AS n_subdistricts
  FROM thai_geography
  WHERE zip_code IS NOT NULL
  GROUP BY zip_code, district_code
),
ranked AS (
  SELECT
    zip_code, district_code, n_subdistricts,
    COUNT(*) OVER (PARTITION BY zip_code) AS district_count,
    ROW_NUMBER() OVER (PARTITION BY zip_code ORDER BY n_subdistricts DESC, district_code ASC) AS rn
  FROM zip_district_counts
)
SELECT
  r.zip_code,
  r.district_code,
  g.district_name_th,
  g.district_name_en,
  g.province_code,
  g.province_name_th,
  g.province_name_en,
  r.district_count,
  IF(r.district_count > 1, 1, 0) AS is_ambiguous
FROM ranked r
JOIN (SELECT DISTINCT district_code, district_name_th, district_name_en, province_code, province_name_th, province_name_en FROM thai_geography) g
  ON g.district_code = r.district_code
WHERE r.rn = 1;

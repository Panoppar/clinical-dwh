-- ============================================================================
-- Silver -> Gold: populate Dim_District_Population.
-- Run AFTER 06_create_gold_population_reference.sql.
--
-- DOPA's own data only carries Thai names; English names are enriched via
-- silver.thai_geography (matching district_code = regoffice_code), falling
-- back to the DOPA Thai name if a district code doesn't match (e.g. a
-- historical registration-office code that was since merged/renamed).
-- ============================================================================

USE gold;

INSERT INTO Dim_District_Population (
  district_code, year_ce, district_name_th, district_name_en,
  province_code, province_name_th, province_name_en, male, female, total, house
)
SELECT
  CAST(p.regoffice_code AS UNSIGNED) AS district_code,
  (2500 + CAST(LEFT(p.yymm, 2) AS UNSIGNED)) - 543 AS year_ce,
  p.regoffice_name AS district_name_th,
  g.district_name_en,
  CAST(p.province_code AS UNSIGNED) AS province_code,
  p.province_name AS province_name_th,
  g.province_name_en,
  SUM(p.male) AS male,
  SUM(p.female) AS female,
  SUM(p.total) AS total,
  SUM(p.house) AS house
FROM silver.population_reference_subdistrict p
LEFT JOIN (
  -- thai_geography is at subdistrict grain (many rows per district); collapse
  -- to one row per district_code first, or the join below fans out p's
  -- population figures by however many subdistricts that district has.
  SELECT DISTINCT district_code, district_name_en, province_name_en
  FROM silver.thai_geography
) g ON g.district_code = CAST(p.regoffice_code AS UNSIGNED)
WHERE p.grain_level = 'district'
GROUP BY
  p.regoffice_code, p.yymm, p.regoffice_name, g.district_name_en,
  p.province_code, p.province_name, g.province_name_en;

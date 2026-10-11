-- ============================================================================
-- Silver -> Gold: populate Dim_District_Population.
-- Run AFTER 06_create_gold_population_reference.sql.
--
-- DOPA's own data only carries Thai names; English district names are
-- enriched via silver.thai_geography (matching district_code = regoffice_code).
--
-- IMPORTANT: DOPA's "regoffice_code" (RCODE) is NOT purely district/amphoe
-- codes. A province also has separate higher-numbered RCODE entries for
-- each municipality (เทศบาล) registration office within it — a different,
-- orthogonal administrative layer that silver.thai_geography (built from a
-- standard amphoe/tambon dataset) has no entries for. Those rows'
-- district_name_en/district_name_th-via-join legitimately have no English
-- name and that's fine to leave NULL; their population figures are real
-- and are NOT double-counted against the district-level rows (district and
-- municipality registration offices partition the province, they don't
-- overlap), so summing ALL rows for a province is correct.
--
-- What's NOT fine: resolving province_name_en through that same per-
-- district join, since ~60% of rows (every municipality-level one) would
-- then get a NULL province name despite belonging to a perfectly real,
-- named province. province_name_en is instead resolved once per
-- province_code (taking any row in that province that does resolve), so
-- grouping/labeling a province never depends on which specific
-- district/municipality rows happened to match.
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
  d.district_name_en,
  CAST(p.province_code AS UNSIGNED) AS province_code,
  p.province_name AS province_name_th,
  prov.province_name_en,
  SUM(p.male) AS male,
  SUM(p.female) AS female,
  SUM(p.total) AS total,
  SUM(p.house) AS house
FROM silver.population_reference_subdistrict p
LEFT JOIN (
  -- thai_geography is at subdistrict grain (many rows per district); collapse
  -- to one row per district_code first, or the join below fans out p's
  -- population figures by however many subdistricts that district has.
  SELECT DISTINCT district_code, district_name_en
  FROM silver.thai_geography
) d ON d.district_code = CAST(p.regoffice_code AS UNSIGNED)
LEFT JOIN (
  -- Resolved once per province_code so municipality-level RCODE rows (which
  -- never match the district-level join above) still get a province name.
  SELECT DISTINCT province_code, province_name_en
  FROM silver.thai_geography
) prov ON prov.province_code = CAST(p.province_code AS UNSIGNED)
WHERE p.grain_level = 'district'
GROUP BY
  p.regoffice_code, p.yymm, p.regoffice_name, d.district_name_en,
  p.province_code, p.province_name, prov.province_name_en;

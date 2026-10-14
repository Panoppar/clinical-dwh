-- ============================================================================
-- SILVER LAYER — transform DOPA population by area/month
-- yymm format: 2-digit BE year + 2-digit month (e.g. "6312" = BE2563-12 =
-- Dec 2020 CE), confirmed against the bronze DDL's own documented example.
-- ============================================================================

USE silver;

INSERT INTO population_by_area_month
  (admin_level, yymm, year_be, year_ce, month,
   cc_code, cc_desc, rcode_code, rcode_desc, ccaatt_code, ccaatt_desc,
   ccaattmm_code, ccaattmm_desc, male, female, total, house, is_rollup_row, source_schema_variant)
SELECT
  admin_level, yymm,
  2500 + CAST(LEFT(yymm, 2) AS UNSIGNED) AS year_be,
  2500 + CAST(LEFT(yymm, 2) AS UNSIGNED) - 543 AS year_ce,
  CAST(RIGHT(yymm, 2) AS UNSIGNED) AS month,
  cc_code, cc_desc, rcode_code, rcode_desc, ccaatt_code, ccaatt_desc,
  ccaattmm_code, ccaattmm_desc,
  CAST(NULLIF(REPLACE(male, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(female, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(total, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(house, ',', ''), '') AS SIGNED),
  CASE admin_level
    WHEN 'province'    THEN IF(cc_code = '0', 1, 0)
    WHEN 'district'    THEN IF(rcode_code = '0', 1, 0)
    WHEN 'subdistrict' THEN IF(ccaatt_code = '0', 1, 0)
  END AS is_rollup_row,
  schema_variant
FROM bronze.dopa_population_by_area_month
WHERE is_duplicate_row = 0
  AND (
    admin_level = 'province'
    OR (admin_level = 'district' AND schema_variant IN ('long_format_pipe_delimited', 'html_yearly_snapshot'))
    OR (admin_level = 'subdistrict' AND (
          schema_variant = 'long_format_pipe_delimited'
          OR (schema_variant IN ('html_yearly_snapshot', 'html_yearly_snapshot_triplicated')
              AND CAST(yymm AS UNSIGNED) > 6312)
        ))
  );

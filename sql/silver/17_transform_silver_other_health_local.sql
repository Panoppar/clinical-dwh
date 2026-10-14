USE silver;

INSERT INTO health_kpi_export
  (geo_level, set_number, area_name, target, result, f3_ratio,
   result1, result2, result3, result4, result5, result6,
   result7, result8, result9, result10, result11, result12)
SELECT file_geo_level, file_set_number, a_name,
  CAST(NULLIF(target, '') AS SIGNED), CAST(NULLIF(result, '') AS SIGNED),
  CAST(NULLIF(F3, '') AS DECIMAL(10,4)),
  CAST(NULLIF(result1, '') AS SIGNED), CAST(NULLIF(result2, '') AS SIGNED),
  CAST(NULLIF(result3, '') AS SIGNED), CAST(NULLIF(result4, '') AS SIGNED),
  CAST(NULLIF(result5, '') AS SIGNED), CAST(NULLIF(result6, '') AS SIGNED),
  CAST(NULLIF(result7, '') AS SIGNED), CAST(NULLIF(result8, '') AS SIGNED),
  CAST(NULLIF(result9, '') AS SIGNED), CAST(NULLIF(result10, '') AS SIGNED),
  CAST(NULLIF(result11, '') AS SIGNED), CAST(NULLIF(result12, '') AS SIGNED)
FROM bronze.health_kpi_export;

INSERT INTO community_count_by_district_bkk
  (district_name, crowded_count, suburban_count, highrise_count, urban_count, special_format_count)
SELECT `สำนักงานเขต`,
  CAST(NULLIF(`ชุมชนแออัด`, '') AS SIGNED), CAST(NULLIF(`ชุมชนชานเมือง`, '') AS SIGNED),
  CAST(NULLIF(`ชุมชนอาคารสูง`, '') AS SIGNED), CAST(NULLIF(`ชุมชนเมือง`, '') AS SIGNED),
  CAST(NULLIF(`ชุมชนรูปแบบพิเศษ`, '') AS SIGNED)
FROM bronze.community_count_by_district_bkk;

INSERT INTO foreign_labor_permit_by_area_bkk
  (area_name, district_group, general_total, general_male, general_female,
   mou_total, mou_male, mou_female, investment_promo_total, investment_promo_male, investment_promo_female,
   minority_total, minority_male, minority_female, renewal_total, renewal_male, renewal_female,
   undocumented_registered_total, undocumented_registered_male, undocumented_registered_female,
   is_aggregate_row)
SELECT `พื้นที่`, `เขตที่ครอบคลุม`,
  CAST(NULLIF(NULLIF(REPLACE(`ทั่วไป_รวม`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`ทั่วไป_ชาย`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`ทั่วไป_หญิง`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`นำเข้าตามMOU_รวม`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`นำเข้าตามMOU_ชาย`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`นำเข้าตามMOU_หญิง`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`ส่งเสริมการลงทุน_รวม`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`ส่งเสริมการลงทุน_ชาย`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`ส่งเสริมการลงทุน_หญิง`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`ชนกลุ่มน้อย_รวม`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`ชนกลุ่มน้อย_ชาย`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`ชนกลุ่มน้อย_หญิง`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`ต่ออายุ_รวม`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`ต่ออายุ_ชาย`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`ต่ออายุ_หญิง`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`จดทะเบียนสถานะไม่ถูกกฎหมาย_รวม`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`จดทะเบียนสถานะไม่ถูกกฎหมาย_ชาย`, ',', ''), ''), '-') AS SIGNED),
  CAST(NULLIF(NULLIF(REPLACE(`จดทะเบียนสถานะไม่ถูกกฎหมาย_หญิง`, ',', ''), ''), '-') AS SIGNED),
  IF(TRIM(`เขตที่ครอบคลุม`) = 'รวมทั้งสิ้น', 1, 0)
FROM bronze.foreign_labor_permit_by_area_bkk
-- Rows 1-11 only -- see the bronze-level-defect comment in the DDL file.
-- Rows 12+ reuse these same columns for 3 different, differently-labeled
-- reports and would silently misrepresent that data under the wrong names.
WHERE source_row_number <= 11;

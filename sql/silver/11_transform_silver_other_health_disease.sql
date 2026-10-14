USE silver;

-- ---------------------------------------------------------------------
INSERT INTO sick_298group_long (year_be, year_ce, province, disease_group, sex, case_count, is_aggregate_row)
SELECT CAST(`ปี` AS UNSIGNED), CAST(`ปี` AS UNSIGNED) - 543, `จังหวัด`, `ชื่อกลุ่ม`,
  CASE `เพศ` WHEN 'ชาย' THEN 'male' WHEN 'หญิง' THEN 'female' ELSE `เพศ` END,
  CAST(NULLIF(REPLACE(`จำนวน`, ',', ''), '') AS SIGNED),
  IF(TRIM(`ชื่อกลุ่ม`) = 'รวม', 1, 0)
FROM bronze.sick_298group_long;

INSERT INTO sick_298group_wide (year_be, year_ce, province, disease_group, male_count, female_count, total_count, is_aggregate_row)
SELECT CAST(file_year AS UNSIGNED), CAST(file_year AS UNSIGNED) - 543, file_province, `ชื่อกลุ่ม(298โรค)`,
  CAST(NULLIF(REPLACE(`ชาย`, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(`หญิง`, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(`รวม`, ',', ''), '') AS SIGNED),
  IF(TRIM(`ชื่อกลุ่ม(298โรค)`) = 'รวม', 1, 0)
FROM bronze.sick_298group_wide;

-- ---------------------------------------------------------------------
INSERT INTO surveillance_top_diseases (year_be, year_ce, disease_name, case_count, unit)
SELECT CAST(`ปี` AS UNSIGNED), CAST(`ปี` AS UNSIGNED) - 543, `โรค`,
  CAST(NULLIF(REPLACE(`จำนวน`, ',', ''), '') AS SIGNED), `หน่วย`
FROM bronze.surveillance_top_diseases_2566
UNION ALL
SELECT CAST(`ปี` AS UNSIGNED), CAST(`ปี` AS UNSIGNED) - 543, `ชื่อโรค`,
  CAST(NULLIF(REPLACE(`จำนวน`, ',', ''), '') AS SIGNED), NULL
FROM bronze.surveillance_top_diseases_2567;

-- ---------------------------------------------------------------------
INSERT INTO compare_cases_by_disease (disease_name, count_2024, count_2025, diff, is_aggregate_row)
SELECT `โรค`,
  CAST(NULLIF(REPLACE(`ปี2567`, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(`ปี2568`, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(`ผลต่าง`, ',', ''), '') AS SIGNED),
  IF(TRIM(`โรค`) LIKE 'รวมทั้งหมด%', 1, 0)
FROM bronze.compare_cases_by_disease;

INSERT INTO compare_cases_by_subdistrict (district_name, subdistrict_name, count_2024, count_2025, diff, is_aggregate_row)
SELECT `เขต`, `แขวง`,
  CAST(NULLIF(REPLACE(`ปี2567`, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(`ปี2568`, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(`ผลต่าง`, ',', ''), '') AS SIGNED),
  IF(TRIM(`เขต`) LIKE 'รวมทั้งหมด%', 1, 0)
FROM bronze.compare_cases_by_subdistrict;

-- ---------------------------------------------------------------------
INSERT INTO ncd_mortality_by_disease
  (disease, health_region, province, year_ce, death_count, death_rate_per_100k, mid_year_population, is_aggregate_row)
SELECT source_sheet_name, `เขตสุขภาพ`, `จังหวัด`, 2019,
  CAST(NULLIF(`ปี2562_จำนวน`, '') AS DECIMAL(15,2)),
  CAST(NULLIF(`ปี2562_อัตรา`, '') AS DECIMAL(15,6)),
  CAST(NULLIF(`ปี2562_ประชากรกลางปี`, '') AS DECIMAL(15,2)),
  IF(TRIM(`จังหวัด`) = 'รวม', 1, 0)
FROM bronze.ncd_mortality_multisheet
UNION ALL
SELECT source_sheet_name, `เขตสุขภาพ`, `จังหวัด`, 2020,
  CAST(NULLIF(`ปี2563_จำนวน`, '') AS DECIMAL(15,2)),
  CAST(NULLIF(`ปี2563_อัตรา`, '') AS DECIMAL(15,6)),
  CAST(NULLIF(`ปี2563_ประชากรกลางปี`, '') AS DECIMAL(15,2)),
  IF(TRIM(`จังหวัด`) = 'รวม', 1, 0)
FROM bronze.ncd_mortality_multisheet
UNION ALL
SELECT source_sheet_name, `เขตสุขภาพ`, `จังหวัด`, 2021,
  CAST(NULLIF(`ปี2564_จำนวน`, '') AS DECIMAL(15,2)),
  CAST(NULLIF(`ปี2564_อัตรา`, '') AS DECIMAL(15,6)),
  CAST(NULLIF(`ปี2564_ประชากรกลางปี`, '') AS DECIMAL(15,2)),
  IF(TRIM(`จังหวัด`) = 'รวม', 1, 0)
FROM bronze.ncd_mortality_multisheet
UNION ALL
SELECT source_sheet_name, `เขตสุขภาพ`, `จังหวัด`, 2022,
  CAST(NULLIF(`ปี2565_จำนวน`, '') AS DECIMAL(15,2)),
  CAST(NULLIF(`ปี2565_อัตรา`, '') AS DECIMAL(15,6)),
  CAST(NULLIF(`ปี2565_ประชากรกลางปี`, '') AS DECIMAL(15,2)),
  IF(TRIM(`จังหวัด`) = 'รวม', 1, 0)
FROM bronze.ncd_mortality_multisheet
UNION ALL
SELECT source_sheet_name, `เขตสุขภาพ`, `จังหวัด`, 2023,
  CAST(NULLIF(`ปี2566_จำนวน`, '') AS DECIMAL(15,2)),
  CAST(NULLIF(`ปี2566_อัตรา`, '') AS DECIMAL(15,6)),
  CAST(NULLIF(`ปี2566_ประชากรกลางปี`, '') AS DECIMAL(15,2)),
  IF(TRIM(`จังหวัด`) = 'รวม', 1, 0)
FROM bronze.ncd_mortality_multisheet;

-- ---------------------------------------------------------------------
-- cause_of_death_top10_with_rate: dedupe the csv/mojibake-xlsx pair
-- (confirmed exact duplicates at bronze time) -- canonical = the .csv.
INSERT INTO cause_of_death_top10_with_rate
  (year_be, year_ce, province, cause_of_death, male_count, female_count, total_count,
   rate_per_100k, unit, source_attribution, is_aggregate_row)
SELECT CAST(`ปี` AS UNSIGNED), CAST(`ปี` AS UNSIGNED) - 543, `จังหวัด`, `สาเหตุการตาย`,
  CAST(NULLIF(REPLACE(`เพศชาย`, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(`เพศหญิง`, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(`รวม`, ',', ''), '') AS SIGNED),
  CAST(NULLIF(`อัตราการตายต่อประชากร`, '') AS DECIMAL(10,2)),
  `หน่วย`, `ที่มา`,
  IF(TRIM(`สาเหตุการตาย`) = 'รวม', 1, 0)
FROM bronze.cause_of_death_top10_with_rate
WHERE source_file_name LIKE '%.csv';

INSERT INTO cause_of_death_top10_no_rate
  (year_be, year_ce, province, cause_of_death, male_count, female_count, total_count,
   unit, source_attribution, is_aggregate_row)
SELECT CAST(`ปี` AS UNSIGNED), CAST(`ปี` AS UNSIGNED) - 543, `จังหวัด`, `สาเหตุการตาย`,
  CAST(NULLIF(REPLACE(`ชาย`, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(`หญิง`, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(`รวม`, ',', ''), '') AS SIGNED),
  `หน่วย`, `ที่มา`,
  IF(TRIM(`สาเหตุการตาย`) = 'รวม', 1, 0)
FROM bronze.cause_of_death_top10_no_rate;

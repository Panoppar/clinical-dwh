USE silver;

INSERT INTO edu_vocational_college (college_name, address, remark)
SELECT ed_name, ad_name, remark FROM bronze.edu_vocational_college;

INSERT INTO edu_university (university_name, address, remark)
SELECT n_u_name, a_name, remark FROM bronze.edu_university;

INSERT INTO edu_school (school_name, student_count, classroom_count, teacher_count,
  student_m6_count, student_p3_count, remark)
SELECT s_name,
  CAST(NULLIF(student_num, '') AS UNSIGNED), CAST(NULLIF(classroom_num, '') AS UNSIGNED),
  CAST(NULLIF(teacher_num, '') AS UNSIGNED), CAST(NULLIF(studentm6_num, '') AS UNSIGNED),
  CAST(NULLIF(studentp3_num, '') AS UNSIGNED), remark
FROM bronze.edu_school;

INSERT INTO health_hospital (hospital_name, address, remark)
SELECT h_name, address_name, remark FROM bronze.health_hospital;

INSERT INTO religious_site (site_name, address, remark)
SELECT n_rel, a_rel, remark FROM bronze.religious_site;

INSERT INTO business_establishment (business_name, business_type, investment_thb, address, remark)
SELECT name_b, type_b, CAST(NULLIF(REPLACE(investment, ',', ''), '') AS DECIMAL(20,2)), address, remark
FROM bronze.business_establishment;

INSERT INTO safety_risk_point (risk_name, risk_type, r1, r2, r3, r4, r5, r6, remark)
SELECT risk_name, risk_type, r1, r2, r3, r4, r5, r6, remark FROM bronze.safety_risk_point;

INSERT INTO lat_krabang_population_by_subdistrict (subdistrict_name, male_count, female_count, total_count)
SELECT l_district,
  CAST(NULLIF(REPLACE(l_male, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(l_female, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(l_total, ',', ''), '') AS SIGNED)
FROM bronze.population_total
WHERE TRIM(l_district) <> 'รวม';

INSERT INTO lat_krabang_deaths_by_subdistrict (subdistrict_name, male_count, female_count, total_count)
SELECT l_district,
  CAST(NULLIF(REPLACE(l_male, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(l_female, ',', ''), '') AS SIGNED),
  CAST(NULLIF(REPLACE(l_total, ',', ''), '') AS SIGNED)
FROM bronze.population_death
WHERE TRIM(l_district) <> 'รวม';

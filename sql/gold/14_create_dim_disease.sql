-- ============================================================================
-- GOLD LAYER — dim_disease
-- Scoped PER source_system, not a unified taxonomy -- confirmed during
-- planning that these 7 sources' disease vocabularies are disjoint and
-- don't line up 1:1 (DDS has 85 Thai disease names, sick_298group uses
-- numbered ICD-ish group labels like "104 เบาหวาน", HDC uses short
-- English codes like "dm", cause_of_death uses its own Thai phrasing --
-- no reliable automated crosswalk exists between them). Cross-source
-- disease rollups are future work requiring a real crosswalk, not
-- something to fabricate here.
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `dim_disease`;

CREATE TABLE `dim_disease` (
    `disease_key`    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `source_system`    VARCHAR(20)  NOT NULL COMMENT 'dds | hdc | cause_of_death | ncd_mortality | sick298 | compare_cases | surveillance',
    `disease_code`       VARCHAR(300) NOT NULL COMMENT 'raw identifier as that source reports it',
    `disease_name`         VARCHAR(300) NOT NULL,
    UNIQUE KEY `ux_dd_combo` (`source_system`, `disease_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `dim_disease` (source_system, disease_code, disease_name)
SELECT DISTINCT 'dds', disease_name_th, disease_name_th FROM silver.dds_health_region_disease_report
UNION
SELECT DISTINCT 'cause_of_death', cause_of_death, cause_of_death FROM silver.cause_of_death_top10_with_rate WHERE is_aggregate_row = 0
UNION
SELECT DISTINCT 'ncd_mortality', disease, disease FROM silver.ncd_mortality_by_disease WHERE is_aggregate_row = 0
UNION
SELECT DISTINCT 'sick298', disease_group, disease_group FROM silver.sick_298group_long WHERE is_aggregate_row = 0
UNION
SELECT DISTINCT 'sick298', disease_group, disease_group FROM silver.sick_298group_wide WHERE is_aggregate_row = 0
UNION
SELECT DISTINCT 'compare_cases', disease_name, disease_name FROM silver.compare_cases_by_disease WHERE is_aggregate_row = 0
UNION
SELECT DISTINCT 'surveillance', disease_name, disease_name FROM silver.surveillance_top_diseases;

-- HDC's short English codes decoded to readable names -- only 11 values
-- across all 4 hdc_* tables, confirmed by direct inspection, so a plain
-- VALUES list is simpler and more reliable than a generic lookup query.
INSERT INTO `dim_disease` (source_system, disease_code, disease_name)
VALUES
    ('hdc', 'ihd', 'Ischemic heart disease'),
    ('hdc', 'asthma', 'Asthma'),
    ('hdc', 'copd', 'Chronic obstructive pulmonary disease'),
    ('hdc', 'coronary', 'Coronary artery disease'),
    ('hdc', 'dm', 'Diabetes mellitus'),
    ('hdc', 'ht', 'Hypertension'),
    ('hdc', 'ca_breast', 'Breast cancer'),
    ('hdc', 'ca_cervix', 'Cervical cancer'),
    ('hdc', 'ca_lung', 'Lung cancer'),
    ('hdc', 'emphysema', 'Emphysema'),
    ('hdc', 'stroke', 'Stroke');

-- compare_cases_by_subdistrict's source file ("จำนวนผู้ป่วยรายเขต-แขวง_
-- เปรียบเทียบปี2567-2568.csv" -- "patient count by district-subdistrict,
-- 2024-2025 comparison") has no disease column at all -- confirmed by
-- checking the raw bronze file: it's a total-patient-count comparison
-- across all diseases, not disease-specific. A dedicated catch-all code
-- keeps that geographic data point in the warehouse instead of silently
-- dropping it or mis-assigning it to some other source's disease catalog.
INSERT INTO `dim_disease` (source_system, disease_code, disease_name)
VALUES ('compare_cases', 'all_diseases_combined', 'All diseases combined (total patient count)');

SET FOREIGN_KEY_CHECKS = 1;

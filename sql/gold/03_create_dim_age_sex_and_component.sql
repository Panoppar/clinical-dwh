-- ============================================================================
-- GOLD LAYER — dim_age_sex, dim_population_component
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `dim_age_sex`;
DROP TABLE IF EXISTS `dim_population_component`;

CREATE TABLE `dim_age_sex` (
    `age_sex_key`    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `sex`              VARCHAR(10) NOT NULL COMMENT 'male | female | total',
    `age_exact`          SMALLINT    NULL COMMENT 'NULL for bucket/total/other qualifiers, or when age doesn''t apply',
    `age_qualifier`        VARCHAR(10) NULL COMMENT 'exact | le | ge | gt | lt | total | other; NULL when the row has no age dimension at all (other_health''s 5 non-age-bracket components: sex applies, age doesn''t)',
    UNIQUE KEY `ux_das_combo` (`sex`, `age_exact`, `age_qualifier`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- NSO's sex codes (M/F/_T) are normalized to the same male/female/total
-- vocabulary other_health's Silver tables already use, so one dimension
-- serves both fact sources without a second sex vocabulary.
INSERT INTO `dim_age_sex` (sex, age_exact, age_qualifier)
SELECT DISTINCT
    CASE sex WHEN 'M' THEN 'male' WHEN 'F' THEN 'female' WHEN '_T' THEN 'total' ELSE sex END,
    age_exact, age_qualifier
FROM silver.population_reference_age_sex
UNION
SELECT DISTINCT sex, age_exact, age_qualifier
FROM silver.population_by_age_subdistrict_bkk
WHERE component_type = 'age_bracket';

-- other_health's 5 non-age-bracket components (lunar_birth,
-- central_house_reg, non_thai_national, mid_move, grand_total) carry a
-- sex dimension but no age dimension at all -- one row per sex with
-- age_exact/age_qualifier both NULL, so fact_population_age_sex can join
-- to them instead of silently losing those rows to an inner join miss.
INSERT INTO `dim_age_sex` (sex, age_exact, age_qualifier)
VALUES ('male', NULL, NULL), ('female', NULL, NULL), ('total', NULL, NULL);

-- is_headline_total depends on a (component, sex) COMBINATION, not purely
-- the component -- confirmed by inspection (other_health's component_type
-- 'grand_total' pairs with sex='male'/'female' AND sex='total'; only the
-- sex='total' pairing is the real headline figure). That flag therefore
-- stays on the FACT table (computed the same way Silver already computed
-- it), not baked into this dimension -- this dimension just decodes what
-- each component actually means, across both source vocabularies
-- (NSO's DEM_IND* codes, other_health's component_type strings).
CREATE TABLE `dim_population_component` (
    `component_key`    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `source_system`       VARCHAR(20) NOT NULL COMMENT 'nso | other_health',
    `component_code`       VARCHAR(30) NOT NULL COMMENT 'e.g. DEM_IND24, grand_total',
    `component_name_en`      VARCHAR(200),
    UNIQUE KEY `ux_dpc_combo` (`source_system`, `component_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `dim_population_component` (source_system, component_code, component_name_en)
VALUES
    ('nso', 'DEM_IND24', 'Population from registration (TOTAL)'),
    ('nso', 'DEM_IND48', 'Central house'),
    ('nso', 'DEM_IND50', 'During move'),
    ('nso', 'DEM_IND109', 'Registered in a household registration'),
    ('nso', 'DEM_IND49', 'Not Thai nationality'),
    ('nso', 'DEM_IND95', 'Number of Thai nationals from registration'),
    ('other_health', 'age_bracket', 'Age bracket (regular age/sex breakdown)'),
    ('other_health', 'lunar_birth', 'Lunar-calendar birth year (unexplained/other)'),
    ('other_health', 'central_house_reg', 'Central house registration'),
    ('other_health', 'non_thai_national', 'Non-Thai nationals'),
    ('other_health', 'mid_move', 'Mid-move (during relocation)'),
    ('other_health', 'grand_total', 'Grand total');

SET FOREIGN_KEY_CHECKS = 1;

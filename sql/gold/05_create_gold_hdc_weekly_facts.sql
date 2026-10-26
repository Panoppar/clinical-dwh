-- ============================================================================
-- GOLD LAYER — fact_hdc_weekly_observation (kmch-ml input-parity gap 2)
-- New file, does not touch fact_hdc_observation or any other table in
-- sql/gold/01-04 -- those stay exactly as-is.
--
-- Source: silver.api_hdc_observations, filtered to the 4 PM2.5-linked
-- weekly disease reports (report codes below) -- confirmed these are
-- NOT a separate report family: they're already discovered by the
-- existing 4-subcatalog HDC crawl (ingest_api_hdc.py), under
-- "การป่วยด้วยโรคจากมลพิษทางอากาศ" (air pollution disease), already
-- landed in Bronze/Silver with zero code change needed there. This file
-- + the new _build_fact_hdc_weekly() Gold transform are the only change
-- for this gap.
--
-- Report codes: NL9idjvwQKjv6R6Maiw9 (patients seen), cxG0gstCJkfG1X1c71y4o
-- (patients resident in catchment), 58t8PvddP1nCaDdSTuakd (visit count +
-- % of total), 5968980caf87d4518aa9f0263a9299c9 (rate per 100k).
--
-- Field shape is richer than a flat w_01..w_53: each week has 4 metric
-- variants (w_NN_m / w_NN_y / w_NN_z / w_NN_zy), parsed into
-- week_number + metric_variant rather than literal columns (a full wide
-- pivot would need 200+ columns). variant meaning is NOT documented by
-- HDC -- carried as-is, not guessed.
--
-- KNOWN DATA-QUALITY CAVEAT (confirmed from kmch-ml's own findings, not
-- fixed here): week-to-calendar mapping is undocumented, reporting is
-- incomplete for some province/year combinations, and year-over-year
-- totals can swing unexpectedly. This table lands what HDC actually
-- returns; it does not attempt to validate or smooth it.
-- ============================================================================

USE gold;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `fact_hdc_weekly_observation`;

CREATE TABLE `fact_hdc_weekly_observation` (
    `fact_id`               BIGINT AUTO_INCREMENT PRIMARY KEY,
    `report_key`            INT UNSIGNED NOT NULL,
    `date_key`              INT UNSIGNED NOT NULL,
    `zone`                  VARCHAR(10)  NOT NULL,
    `record_index`          INT          NOT NULL COMMENT 'which disease-group row within the report response',
    `disease_group_name`    VARCHAR(500) COMMENT 'from the report''s own group_name field, e.g. "Chronic obstructive pulmonary disease (J44)"',
    `ordering`               SMALLINT     COMMENT 'the report''s own rank/position for this disease group',
    `week_number`            TINYINT      COMMENT '1-53; NULL for the all_* annual-total rows',
    `metric_variant`         VARCHAR(10)  NOT NULL COMMENT 'm | y | z | zy -- exact meaning not documented by HDC, carried as-is',
    `metric_value`           DECIMAL(18,2),
    KEY `ix_fhwo_report_date_zone` (`report_key`, `date_key`, `zone`),
    KEY `ix_fhwo_week` (`week_number`),
    CONSTRAINT `fk_fhwo_report` FOREIGN KEY (`report_key`) REFERENCES `dim_hdc_report` (`report_key`),
    CONSTRAINT `fk_fhwo_date` FOREIGN KEY (`date_key`) REFERENCES `dim_date` (`date_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

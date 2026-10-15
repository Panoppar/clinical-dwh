-- ============================================================================
-- GOLD LAYER — feat_geography_month, Stage 2 extension
-- Adds disease incidence columns for the 5 diseases actually present in
-- fact_disease_incidence_hdc (confirmed by inspection: dm, ht, copd,
-- coronary at monthly grain; ihd at annual grain only -- the other HDC
-- diseases tracked elsewhere in Silver, asthma/stroke/the 3 cancers/
-- emphysema, either aren't in hdc_incidence_monthly/annual at all or
-- only appear in hdc_death_by_age/hdc_population_by_age, which feed a
-- different fact table, not this one).
--
-- incidence_rate_ihd only populates on January rows (annual grain's
-- date_key is Jan 1 of the year) -- a real grain mismatch between an
-- annual-only disease and this monthly feature table, not a bug.
--
-- This script ALTERs the table built by 12_create_feat_geography_month.sql
-- rather than redefining it, since the base feature table and this
-- disease extension are separate vertical slices built in separate
-- stages (Stage 1 population, Stage 2 disease) per the project's staged
-- build plan.
-- ============================================================================

USE gold;

ALTER TABLE `feat_geography_month`
    ADD COLUMN `incidence_rate_dm` DECIMAL(20,2) NULL COMMENT 'diabetes mellitus, HDC result value',
    ADD COLUMN `incidence_rate_ht` DECIMAL(20,2) NULL COMMENT 'hypertension',
    ADD COLUMN `incidence_rate_copd` DECIMAL(20,2) NULL,
    ADD COLUMN `incidence_rate_coronary` DECIMAL(20,2) NULL COMMENT 'coronary artery disease',
    ADD COLUMN `incidence_rate_ihd` DECIMAL(20,2) NULL COMMENT 'ischemic heart disease, annual grain only -- see note above';

-- ============================================================================
-- INCREMENTAL PIPELINE - ALL SOURCES SCHEMA SETUP
-- Run once to extend incremental architecture to NSO, BMA, DIW, DDS
-- ============================================================================

-- Add incremental columns to Silver tables
USE silver;

-- NSO income
ALTER TABLE `api_nso_income`
ADD COLUMN `row_hash` VARCHAR(16) AFTER `source_agency`,
ADD COLUMN `ingestion_batch_id` VARCHAR(100) AFTER `row_hash`,
ADD KEY `ix_row_hash` (`row_hash`),
ADD KEY `ix_ingestion_batch_id` (`ingestion_batch_id`);

-- BMA community
ALTER TABLE `api_bma_community`
ADD COLUMN `row_hash` VARCHAR(16) AFTER `female`,
ADD COLUMN `ingestion_batch_id` VARCHAR(100) AFTER `row_hash`,
ADD KEY `ix_row_hash` (`row_hash`),
ADD KEY `ix_ingestion_batch_id` (`ingestion_batch_id`);

-- DIW factory
ALTER TABLE `api_diw_factory`
ADD COLUMN `row_hash` VARCHAR(16) AFTER `old_reg_no`,
ADD COLUMN `ingestion_batch_id` VARCHAR(100) AFTER `row_hash`,
ADD KEY `ix_row_hash` (`row_hash`),
ADD KEY `ix_ingestion_batch_id` (`ingestion_batch_id`);

-- DDS disease ranking
ALTER TABLE `api_dds_disease_ranking`
ADD COLUMN `row_hash` VARCHAR(16) AFTER `case_fatality_pct`,
ADD COLUMN `ingestion_batch_id` VARCHAR(100) AFTER `row_hash`,
ADD KEY `ix_row_hash` (`row_hash`),
ADD KEY `ix_ingestion_batch_id` (`ingestion_batch_id`);

-- Update Gold fact tables for MERGE support
USE gold;

-- fact_income: Add ingestion_batch_id + unique key
ALTER TABLE `fact_income`
ADD COLUMN `ingestion_batch_id` VARCHAR(100) AFTER `fact_id`,
ADD UNIQUE KEY `ux_income_business_key` (
    `geo_key`, `date_key`, `source_income1`, `soc_eco_class1`
);

-- fact_factory: Add ingestion_batch_id + unique key
ALTER TABLE `fact_factory`
ADD COLUMN `ingestion_batch_id` VARCHAR(100) AFTER `fact_id`,
ADD UNIQUE KEY `ux_factory_business_key` (`reg_no`);

-- fact_community_population: Add ingestion_batch_id + unique key
ALTER TABLE `fact_community_population`
ADD COLUMN `ingestion_batch_id` VARCHAR(100) AFTER `fact_id`,
ADD UNIQUE KEY `ux_community_business_key` (
    `geo_key`, `date_key`, `name_of_community`
);

-- fact_disease_ranking: Add ingestion_batch_id + unique key
ALTER TABLE `fact_disease_ranking`
ADD COLUMN `ingestion_batch_id` VARCHAR(100) AFTER `fact_id`,
ADD UNIQUE KEY `ux_disease_business_key` (
    `geo_key`, `date_key`, `disease_key`
);

-- fact_hdc_observation: Add ingestion_batch_id (already has unique key from HDC setup)
ALTER TABLE `fact_hdc_observation`
ADD COLUMN `ingestion_batch_id` VARCHAR(100) AFTER `fact_id`;

-- Create/update metadata table (may already exist from HDC setup)
CREATE TABLE IF NOT EXISTS `pipeline_metadata` (
    `metadata_id`           BIGINT AUTO_INCREMENT PRIMARY KEY,
    `target_table`          VARCHAR(100) NOT NULL,
    `last_batch_id`         VARCHAR(100),
    `last_processed_at`     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `created_at`            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `ux_target_table` (`target_table`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- INCREMENTAL PIPELINE METADATA TABLES
-- Run once to set up incremental architecture
-- ============================================================================

USE gold;

-- Pipeline metadata: tracks high-water marks per target table
-- Persists the last successfully processed ingestion_batch_id
CREATE TABLE IF NOT EXISTS `pipeline_metadata` (
    `metadata_id`           BIGINT AUTO_INCREMENT PRIMARY KEY,
    `target_table`          VARCHAR(100) NOT NULL COMMENT 'fact_hdc_observation, fact_income, etc.',
    `last_batch_id`         VARCHAR(100) COMMENT 'Last successfully processed ingestion_batch_id',
    `last_processed_at`     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `created_at`            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `ux_target_table` (`target_table`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add row_hash column to Silver HDC observations for delta detection
-- Hash is deterministic hash of (report_code, year_ce, zone, record_index, field_name, field_value)
USE silver;

ALTER TABLE `api_hdc_observations`
ADD COLUMN `row_hash` VARCHAR(16) AFTER `field_value`,
ADD KEY `ix_row_hash` (`row_hash`);

-- Add ingestion_batch_id to Silver for high-water mark filtering
-- Tracks which batch inserted each row (comes from Bronze lineage)
ALTER TABLE `api_hdc_observations`
ADD COLUMN `ingestion_batch_id` VARCHAR(100) AFTER `row_hash`,
ADD KEY `ix_ingestion_batch_id` (`ingestion_batch_id`);

-- Update Gold fact_hdc_observation to support MERGE/upsert
-- Add ingestion_batch_id for tracking which batch updated the row
-- Add unique constraint on business key for INSERT ... ON DUPLICATE KEY UPDATE
USE gold;

ALTER TABLE `fact_hdc_observation`
ADD COLUMN `ingestion_batch_id` VARCHAR(100) AFTER `fact_id`,
ADD UNIQUE KEY `ux_hdc_business_key` (
    `report_code`, `year_ce`, `zone`, `record_index`
);

-- Optional: Index for high-water mark filtering in Silver
USE silver;
CREATE INDEX `ix_hdc_batch_id_date` ON `api_hdc_observations` (`ingestion_batch_id`, `year_ce`);

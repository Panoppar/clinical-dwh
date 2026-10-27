-- ============================================================================
-- BRONZE LAYER — tambon_xwalk (kmch-ml input-parity gap 4/6)
-- Source: xwalk_tambon_unit.csv, file-based (not a live API, a deliberate
-- scoped exception -- see docs/06_kmch_ml_gap_closure_plan.md, Gap 4).
-- Landed via pipeline/ingest_file_tambon_xwalk.py.
--
-- This is kmch-ml's own authoritative mapping of every original TIS-1099
-- tambon code to the merged gold.dim_area unit_code it belongs to --
-- including the 7 Bangkok post-2019 khwaeng-split groups that
-- gold.dim_area's own fallback logic previously approximated incorrectly
-- (see sql/gold/04's _build_dim_area() fix). 1:1 fidelity, no
-- transformation, same convention as every other Bronze table.
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `tambon_xwalk`;

CREATE TABLE `tambon_xwalk` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'TAMBON_XWALK',

  `raw_tambon_code`      VARCHAR(20),
  `raw_tambon_th`         VARCHAR(255),
  `raw_tambon_en`          VARCHAR(255),
  `raw_amphoe_code`         VARCHAR(20),
  `raw_postal_code`          VARCHAR(20),
  `raw_unit_code`             VARCHAR(20) COMMENT 'kmch-ml''s merged-unit identity -- equals raw_tambon_code except for the 7 Bangkok split groups',
  `raw_is_split`               VARCHAR(10) COMMENT '"True"/"False" as text, same as every other Bronze column -- cast in Silver/Gold',
  `raw_amphoe_th`               VARCHAR(255),
  `raw_province_code`            VARCHAR(20),

  KEY `ix_txw_tambon` (`raw_tambon_code`),
  KEY `ix_txw_unit` (`raw_unit_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

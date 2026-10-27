-- ============================================================================
-- BRONZE LAYER — BMA migrant worker permits (kmch-ml input-parity gap 2)
-- Source: ข้อมูลแรงงานต่างด้าว.xlsx (BMA/Dept. of Employment publication,
-- 2568 BE snapshot). File-based, not a live API -- a deliberate, scoped
-- exception, same pattern as bronze.tambon_xwalk/dopa_population_*.
-- Landed via pipeline/ingest_file_bma_migrant_worker.py.
--
-- The source is a wide, multi-section pivot: 4 stacked tables in one
-- sheet, each with its own header shape -- shredded as 4 separate Bronze
-- tables (1:1 with each section), not normalized here (that happens in
-- Silver). Every section has the same row shape: 1 grand-total row
-- ("รวมทั้งสิ้น") + 10 zone rows ("พื้นที่ 1".."พื้นที่ 10"), each with a
-- district-name list in the second column.
--
-- Verified before building: every column's grand-total value exactly
-- equals the sum of its 10 zone rows, in all 4 sections (confirmed
-- "-" means literal zero, not missing/suppressed -- it coexists
-- row-by-row with real nonzero numbers for other nationalities in the
-- same row). Also verified cross-section: bma_migrant_general's own
-- "นำเข้าตาม MOU"/"ต่ออายุ"/"จดทะเบียนสถานะไม่ถูกกฎหมาย" category totals
-- exactly equal bma_migrant_mou_import/renewal/illegal's own grand
-- totals -- those 3 sections are a nationality-level breakdown of 3 of
-- bma_migrant_general's 6 categories, not an independent measure.
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `bma_migrant_general`;
DROP TABLE IF EXISTS `bma_migrant_mou_import`;
DROP TABLE IF EXISTS `bma_migrant_renewal`;
DROP TABLE IF EXISTS `bma_migrant_illegal`;

-- Section A: 6 permit categories (ทั่วไป/นำเข้าตาม MOU/ส่งเสริมการลงทุน/
-- ชนกลุ่มน้อย/ต่ออายุ/จดทะเบียนสถานะไม่ถูกกฎหมาย), no nationality breakdown.
CREATE TABLE `bma_migrant_general` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL,
  `source_folder`       VARCHAR(255)  NOT NULL,
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'BMA_MIGRANT_WORKER',

  `raw_zone_label`           VARCHAR(50) COMMENT '"พื้นที่ N", or empty for the grand-total row',
  `raw_zone_districts_or_label` VARCHAR(500) COMMENT 'district-name list for zone rows, or "รวมทั้งสิ้น" for the grand-total row',
  `raw_general_total`       VARCHAR(20), `raw_general_male`       VARCHAR(20), `raw_general_female`       VARCHAR(20),
  `raw_mou_import_total`     VARCHAR(20), `raw_mou_import_male`     VARCHAR(20), `raw_mou_import_female`     VARCHAR(20),
  `raw_investment_total`      VARCHAR(20), `raw_investment_male`      VARCHAR(20), `raw_investment_female`      VARCHAR(20),
  `raw_minority_total`         VARCHAR(20), `raw_minority_male`         VARCHAR(20), `raw_minority_female`         VARCHAR(20),
  `raw_renewal_total`           VARCHAR(20), `raw_renewal_male`           VARCHAR(20), `raw_renewal_female`           VARCHAR(20),
  `raw_illegal_total`            VARCHAR(20), `raw_illegal_male`            VARCHAR(20), `raw_illegal_female`            VARCHAR(20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sections B/C/D share one shape: 4 nationalities (เมียนมา/ลาว/กัมพูชา/
-- เวียดนาม), each a nationality-level breakdown of one bma_migrant_general
-- category (MOU import / renewal / illegal registration respectively).
CREATE TABLE `bma_migrant_mou_import` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL,
  `source_folder`       VARCHAR(255)  NOT NULL,
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'BMA_MIGRANT_WORKER',

  `raw_zone_label`           VARCHAR(50),
  `raw_zone_districts_or_label` VARCHAR(500),
  `raw_myanmar_total`       VARCHAR(20), `raw_myanmar_male`       VARCHAR(20), `raw_myanmar_female`       VARCHAR(20),
  `raw_laos_total`           VARCHAR(20), `raw_laos_male`           VARCHAR(20), `raw_laos_female`           VARCHAR(20),
  `raw_cambodia_total`        VARCHAR(20), `raw_cambodia_male`        VARCHAR(20), `raw_cambodia_female`        VARCHAR(20),
  `raw_vietnam_total`          VARCHAR(20), `raw_vietnam_male`          VARCHAR(20), `raw_vietnam_female`          VARCHAR(20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `bma_migrant_renewal` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL,
  `source_folder`       VARCHAR(255)  NOT NULL,
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'BMA_MIGRANT_WORKER',

  `raw_zone_label`           VARCHAR(50),
  `raw_zone_districts_or_label` VARCHAR(500),
  `raw_myanmar_total`       VARCHAR(20), `raw_myanmar_male`       VARCHAR(20), `raw_myanmar_female`       VARCHAR(20),
  `raw_laos_total`           VARCHAR(20), `raw_laos_male`           VARCHAR(20), `raw_laos_female`           VARCHAR(20),
  `raw_cambodia_total`        VARCHAR(20), `raw_cambodia_male`        VARCHAR(20), `raw_cambodia_female`        VARCHAR(20),
  `raw_vietnam_total`          VARCHAR(20), `raw_vietnam_male`          VARCHAR(20), `raw_vietnam_female`          VARCHAR(20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `bma_migrant_illegal` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL,
  `source_folder`       VARCHAR(255)  NOT NULL,
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'BMA_MIGRANT_WORKER',

  `raw_zone_label`           VARCHAR(50),
  `raw_zone_districts_or_label` VARCHAR(500),
  `raw_myanmar_total`       VARCHAR(20), `raw_myanmar_male`       VARCHAR(20), `raw_myanmar_female`       VARCHAR(20),
  `raw_laos_total`           VARCHAR(20), `raw_laos_male`           VARCHAR(20), `raw_laos_female`           VARCHAR(20),
  `raw_cambodia_total`        VARCHAR(20), `raw_cambodia_male`        VARCHAR(20), `raw_cambodia_female`        VARCHAR(20),
  `raw_vietnam_total`          VARCHAR(20), `raw_vietnam_male`          VARCHAR(20), `raw_vietnam_female`          VARCHAR(20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

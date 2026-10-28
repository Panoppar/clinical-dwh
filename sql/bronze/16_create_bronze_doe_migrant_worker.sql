-- ============================================================================
-- BRONZE LAYER — doe_migrant_worker_monthly (live replacement for the
-- file-based bma_migrant_general/mou_import/renewal/illegal tables,
-- kmch-ml input-parity gap 2). Source: DOE's (doe.go.th) monthly PDF
-- publication "สถิติการทำงานของคนต่างด้าวประจำเดือน..." -- confirmed live
-- and monthly-updated (see docs/06_kmch_ml_gap_closure_plan.md).
--
-- EAV grain (one row per table x zone x column-group x sex), not fixed
-- columns -- confirmed live that this report's category columns are tied
-- to specific, dated cabinet resolutions and change every time one is
-- superseded (e.g. "ต่ออายุมติ ครม. 2 ธ.ค. 68"), so a rigid per-category
-- column schema would break on a future month's report. Every table in
-- the PDF's "คงเหลือ" (remaining-permits) section is walked generically;
-- which ones carry a nationality breakdown vs. a permit-category
-- breakdown is a Silver/Gold concern, not decided here.
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `doe_migrant_worker_monthly`;

CREATE TABLE `doe_migrant_worker_monthly` (
  `bronze_id`           BIGINT        AUTO_INCREMENT PRIMARY KEY,
  `source_file_name`    VARCHAR(500)  NOT NULL COMMENT 'Landing-zone object key',
  `source_folder`       VARCHAR(255)  NOT NULL COMMENT 'Landing-zone bucket/prefix',
  `source_row_number`   INT           NOT NULL,
  `file_hash`           VARCHAR(64)   NOT NULL,
  `ingestion_batch_id`  VARCHAR(100)  NOT NULL,
  `ingested_at`         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_system`       VARCHAR(50)   NOT NULL DEFAULT 'DOE_MIGRANT_WORKER',

  `raw_report_title`     VARCHAR(500) COMMENT 'e.g. "สถิติการทำงานของคนต่างด้าวประจำเดือน กันยายน พ.ศ.2569" -- carries the report month/year',
  `raw_table_number`      VARCHAR(10)  COMMENT 'this month''s "ตารางที่ N" -- not stable across months, for traceability only',
  `raw_table_title`        VARCHAR(500) COMMENT 'full table caption, e.g. "...(มาตรา 59 MOU)" -- encodes which legal category/nationality-breakdown this table is',
  `raw_zone_label`          VARCHAR(100) COMMENT '"กรุงเทพมหานคร" (BKK total) or "สำนักงานจัดหางานกรุงเทพมหานครพื้นที่ N"',
  `raw_group_label`          VARCHAR(100) COMMENT 'column group header -- a nationality (เมียนมา/ลาว/กัมพูชา/เวียดนาม/ทั้งหมด) for nationality-breakdown tables, or a permit sub-category (MOU/ทั่วไป/...) for table 1',
  `raw_sex_label`             VARCHAR(20)  COMMENT 'รวม | ชาย | หญิง',
  `raw_value`                  VARCHAR(30),

  KEY `ix_dmwm_table` (`raw_table_number`),
  KEY `ix_dmwm_zone` (`raw_zone_label`(50))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

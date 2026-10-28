-- ============================================================================
-- SILVER LAYER — doe_migrant_worker_permit_monthly (live replacement for
-- the retired file-based bma_migrant_worker_permit, kmch-ml input-parity
-- gap 2). Pivots bronze.doe_migrant_worker_monthly's EAV rows (one row per
-- table x zone x group x sex) back into one row per (zone, category,
-- nationality), same grain and nationality-NULL convention as the retired
-- table -- see this project's docs/06_kmch_ml_gap_closure_plan.md.
--
-- permit_category and nationality text is carried through largely as the
-- source PDF's text layer renders it, which includes occasional font-level
-- Thai-glyph artifacts (see pipeline/transform_silver_doe_migrant_worker.py
-- and extract_load_api_doe_migrant_worker.py for why) -- this affects
-- display cosmetics only; grouping and joins only need the values to be
-- stable and distinct, which they are (verified against the report's own
-- published subtotals).
--
-- The Bangkok-wide grand-total row ("กรุงเทพมหานคร", no zone number) is
-- excluded, same convention as the retired table -- it is exactly the sum
-- of the 10 zone rows, so keeping it would just be a derivable,
-- double-counting risk.
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `doe_migrant_worker_permit_monthly`;

CREATE TABLE `doe_migrant_worker_permit_monthly` (
  `silver_id`         BIGINT      AUTO_INCREMENT PRIMARY KEY,
  `zone_id`            TINYINT    NOT NULL COMMENT '1-10, same BMA zone numbering as the retired bma_migrant_worker_permit',
  `report_year_ce`      SMALLINT  NOT NULL,
  `report_month_num`     TINYINT  NOT NULL COMMENT '1-12, parsed from the PDF''s own "ข้อมูล ณ เดือน ..." stamp',
  `permit_category`       VARCHAR(300) NOT NULL,
  `nationality`             VARCHAR(50)  COMMENT 'NULL = category-level total, no nationality breakdown available',
  `total`                    INT NOT NULL,
  `male`                      INT NOT NULL,
  `female`                     INT NOT NULL,
  KEY `ix_dmwpm_zone` (`zone_id`),
  KEY `ix_dmwpm_category` (`permit_category`(100)),
  KEY `ix_dmwpm_month` (`report_year_ce`, `report_month_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

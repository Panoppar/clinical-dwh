-- ============================================================================
-- SILVER LAYER — bma_migrant_worker_permit (kmch-ml input-parity gap 2)
-- Melts the 4 bronze.bma_migrant_* wide tables into one long table,
-- grain (zone_id, permit_category, nationality). nationality is NULL for
-- bma_migrant_general's 3 categories that have no nationality breakdown
-- available (ทั่วไป/ส่งเสริมการลงทุน/ชนกลุ่มน้อย); for the 3 categories
-- that DO have a breakdown (MOU import/renewal/illegal registration),
-- BOTH a nationality=NULL row (the category-level total, from
-- bma_migrant_general) AND 4 nationality-specific rows exist -- a
-- deliberate two-grain design, not a duplication bug: callers choose
-- grain via the nationality column.
--
-- Grand-total ("รวมทั้งสิ้น") rows are NOT loaded here -- confirmed before
-- building that every section's total exactly equals the sum of its 10
-- zone rows, so keeping both would just be a derivable, double-counting
-- risk (same convention as is_rollup_row elsewhere in this project).
-- ============================================================================

USE silver;

DROP TABLE IF EXISTS `bma_migrant_worker_permit`;

CREATE TABLE `bma_migrant_worker_permit` (
  `silver_id`        BIGINT      AUTO_INCREMENT PRIMARY KEY,
  `zone_id`           TINYINT    NOT NULL COMMENT '1-10, BMA''s own zone numbering',
  `permit_category`    VARCHAR(100) NOT NULL COMMENT 'one of the 6 bma_migrant_general categories',
  `nationality`         VARCHAR(50)  COMMENT 'NULL = category-level total, no nationality breakdown available',
  `total`                INT NOT NULL,
  `male`                  INT NOT NULL,
  `female`                 INT NOT NULL,
  KEY `ix_bmwp_zone` (`zone_id`),
  KEY `ix_bmwp_category` (`permit_category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

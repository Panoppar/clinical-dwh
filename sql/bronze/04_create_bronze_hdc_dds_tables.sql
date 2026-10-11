-- ============================================================================
-- Bronze layer DDL — Phase 2 restricted-use health surveillance data
-- (HDC region 6/13 by-age disease stats, DDS yearly rankings, HDC
-- occupational health, DDS PDF report inventory).
--
-- GOVERNANCE NOTE: the source folder's own README states usage/
-- redistribution terms for this data are NOT confirmed with the data
-- owner ("ห้ามเผยแพร่ต่อ" — do not redistribute further). Loaded into this
-- local warehouse on the explicit instruction of the project owner, who
-- accepted that risk — see docs/03_external_reference_sources.md. The raw
-- source files are gitignored (not pushed to any shared remote) regardless
-- of this instruction, as a floor below which redistribution doesn't happen
-- even locally-to-git.
-- ============================================================================

USE bronze;

DROP TABLE IF EXISTS `hdc_disease_pop_age`;
CREATE TABLE `hdc_disease_pop_age` (
  `disease` VARCHAR(30),
  `province_code` VARCHAR(10), `province_name` VARCHAR(100),
  `record_id` VARCHAR(64), `hospcode` VARCHAR(20), `areacode` VARCHAR(20),
  `flag_sent` VARCHAR(5), `date_com` VARCHAR(20), `b_year` VARCHAR(10),
  `pop_group1` VARCHAR(20), `result_group1` VARCHAR(20),
  `pop_group2` VARCHAR(20), `result_group2` VARCHAR(20),
  `pop_group3` VARCHAR(20), `result_group3` VARCHAR(20),
  `pop_group4` VARCHAR(20), `result_group4` VARCHAR(20),
  `pop_group5` VARCHAR(20), `result_group5` VARCHAR(20),
  `ip` VARCHAR(50),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50), `_source_file` VARCHAR(100),
  KEY `ix_hdpa_disease` (`disease`), KEY `ix_hdpa_areacode` (`areacode`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `hdc_disease_incidence`;
CREATE TABLE `hdc_disease_incidence` (
  `disease` VARCHAR(30),
  `province_code` VARCHAR(10), `province_name` VARCHAR(100),
  `record_id` VARCHAR(64), `hospcode` VARCHAR(20), `areacode` VARCHAR(20),
  `flag_sent` VARCHAR(5), `date_com` VARCHAR(20), `b_year` VARCHAR(10),
  `target` VARCHAR(20), `result` VARCHAR(20),
  `result10` VARCHAR(20), `result11` VARCHAR(20), `result12` VARCHAR(20),
  `result01` VARCHAR(20), `result02` VARCHAR(20), `result03` VARCHAR(20),
  `result04` VARCHAR(20), `result05` VARCHAR(20), `result06` VARCHAR(20),
  `result07` VARCHAR(20), `result08` VARCHAR(20), `result09` VARCHAR(20),
  `ip` VARCHAR(50),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50), `_source_file` VARCHAR(100),
  KEY `ix_hdi_disease` (`disease`), KEY `ix_hdi_areacode` (`areacode`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `hdc_disease_death_age`;
CREATE TABLE `hdc_disease_death_age` (
  `disease` VARCHAR(30),
  `province_code` VARCHAR(10), `province_name` VARCHAR(100),
  `record_id` VARCHAR(64), `hospcode` VARCHAR(20), `areacode` VARCHAR(20),
  `flag_sent` VARCHAR(5), `date_com` VARCHAR(20), `b_year` VARCHAR(10),
  `pt_group1` VARCHAR(20), `death_group1` VARCHAR(20),
  `pt_group2` VARCHAR(20), `death_group2` VARCHAR(20),
  `pt_group3` VARCHAR(20), `death_group3` VARCHAR(20),
  `pt_group4` VARCHAR(20), `death_group4` VARCHAR(20),
  `pt_group5` VARCHAR(20), `death_group5` VARCHAR(20),
  `ip` VARCHAR(50),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50), `_source_file` VARCHAR(100),
  KEY `ix_hda_disease` (`disease`), KEY `ix_hda_areacode` (`areacode`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Column order mirrors the raw CSV exactly (province_name is the LAST
-- field in this source file, unlike the HDC files above where it's 2nd —
-- verified against the actual header row, not assumed).
DROP TABLE IF EXISTS `dds_yearly_disease_ranking`;
CREATE TABLE `dds_yearly_disease_ranking` (
  `province_code` VARCHAR(10), `year` VARCHAR(10),
  `disease` VARCHAR(100), `case_count` VARCHAR(20), `case_fatality_pct` VARCHAR(20),
  `death_count` VARCHAR(20), `ipd_count` VARCHAR(20), `rate_per_100k` VARCHAR(20),
  `rank_by_cases` VARCHAR(10), `implied_population` VARCHAR(30), `coverage` VARCHAR(20),
  `rate_lo_per_100k` VARCHAR(20), `rate_hi_per_100k` VARCHAR(20), `grain` VARCHAR(30),
  `area_code` VARCHAR(10), `period` VARCHAR(10), `evidence_type` VARCHAR(30),
  `data_status` VARCHAR(30), `is_provisional` VARCHAR(10), `denominator_type` VARCHAR(50),
  `note` TEXT, `source` VARCHAR(100), `province_name` VARCHAR(100),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50), `_source_file` VARCHAR(100),
  KEY `ix_dyr_province` (`province_code`), KEY `ix_dyr_disease` (`disease`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `dds_unit_indicator_snapshot`;
CREATE TABLE `dds_unit_indicator_snapshot` (
  `unit_code` VARCHAR(20), `indicator_name` VARCHAR(100), `value` VARCHAR(30),
  `year` VARCHAR(10), `source` VARCHAR(30), `grain` VARCHAR(100),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50), `_source_file` VARCHAR(100),
  KEY `ix_dus_unit_code` (`unit_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `hdc_occupational_health`;
CREATE TABLE `hdc_occupational_health` (
  `source_hash` VARCHAR(64), `period` VARCHAR(30), `fetched_at` VARCHAR(30),
  `occupation` TEXT, `target` VARCHAR(20), `result` VARCHAR(20),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50), `_source_file` VARCHAR(100),
  KEY `ix_hoh_source_hash` (`source_hash`), KEY `ix_hoh_period` (`period`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Unextracted DDS PDF weekly surveillance reports (region 6, 13, and
-- province-level 10/11/24 snapshots). No OCR/table extraction performed —
-- this is a document inventory for lineage/audit, not structured content.
DROP TABLE IF EXISTS `dds_pdf_report_inventory`;
CREATE TABLE `dds_pdf_report_inventory` (
  `filename` VARCHAR(100), `size_bytes` VARCHAR(20), `sha256` VARCHAR(64),
  `source_group` VARCHAR(100),
  `_bronze_loaded_at` TIMESTAMP NULL, `_source_system` VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

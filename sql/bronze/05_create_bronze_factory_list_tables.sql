-- =============================================================================
-- BRONZE LAYER TABLE DESIGN
-- Source folder : Factory_list_checked
-- Source files  : รายชื่อโรงงานปี 2567 - สำนักงานโรคติดต่อ กทม.xlsx
--                 รายชื่อโรงงานปี 2568 - สำนักงานโรคติดต่อ กทม.xlsx
--                 (sheet: "ทั่วประเทศรวมนิคมฯ" - nationwide factory registry,
--                  Buddhist Era years 2567 / 2568 = CE 2024 / 2025)
--
-- Translated from the provided DDL at
-- share_unprocessed_20261010/Factory_list_checked/bronze_factory_list.sql
-- into MySQL 8.0 syntax. NUMERIC(p,s) -> DECIMAL(p,s) (MySQL alias),
-- INTEGER -> INT; the provided DDL's choice to type the financial/headcount
-- columns as numeric (not VARCHAR) is kept, since Excel delivers true
-- numbers for them in both source files (confirmed by inspection).
--
-- The two source files have minor header-name differences between permit
-- years (confirmed by inspection: "รหัสทะเบียนโรงงาน FID" vs "ทะเบียนโรงงาน
-- รูปแบบใหม่ (14 หลัก) FID"; "ชื่อเจ้าของ" vs "ผู้ประกอบการ") but identical
-- column positions/meaning -- both map to the same bronze columns, with
-- source_permit_year_be / source_file_name preserving which file a row
-- came from.
-- =============================================================================

USE bronze;

DROP TABLE IF EXISTS `factory_list`;

CREATE TABLE `factory_list` (
    `bronze_id`                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    `source_file_name`            VARCHAR(255)  NOT NULL,
    `source_sheet_name`            VARCHAR(100)  NOT NULL,
    `source_permit_year_be`        VARCHAR(10)   NOT NULL COMMENT 'Buddhist-era year parsed from file name, e.g. 2567, 2568',
    `source_row_number`            INT           NOT NULL,
    `ingested_at`                   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `load_batch_id`                 VARCHAR(100),
    `file_hash`                     VARCHAR(64),

    `raw_factory_reg_no`             VARCHAR(50)   COMMENT 'เลขทะเบียนโรงงาน',
    `raw_factory_fid`                 VARCHAR(50)   COMMENT 'รหัสทะเบียนโรงงาน FID / ทะเบียนโรงงานรูปแบบใหม่ (14 หลัก) FID',
    `raw_tsic_code`                    VARCHAR(20)   COMMENT 'TSIC',
    `raw_factory_type_code`            VARCHAR(20)   COMMENT 'รหัสประเภท',
    `raw_factory_type_desc`            TEXT          COMMENT 'ประเภทโรงงาน -- widened from the provided VARCHAR(500): real data has a value 828 chars long, confirmed by inspection',
    `raw_category`                     VARCHAR(50)   COMMENT 'ประเภท',
    `raw_class`                        VARCHAR(10)   COMMENT 'จำพวก',
    `raw_permit_year_be`                VARCHAR(10)   COMMENT 'ปีที่ได้รับอนุญาต',
    `raw_factory_name`                  VARCHAR(500)  COMMENT 'ชื่อโรงงาน',
    `raw_owner_name`                    VARCHAR(500)  COMMENT 'ชื่อเจ้าของ (2567) / ผู้ประกอบการ (2568)',
    `raw_business_activity`             TEXT          COMMENT 'ประกอบกิจการ -- widened from the provided VARCHAR(1000): real data has a value 1298 chars long, confirmed by inspection',
    `raw_address_no`                     VARCHAR(100)  COMMENT 'เลขที่',
    `raw_moo`                            VARCHAR(50)   COMMENT 'หมู่',
    `raw_soi`                            VARCHAR(255)  COMMENT 'ซอย',
    `raw_road`                           VARCHAR(255)  COMMENT 'ถนน',
    `raw_sub_district`                   VARCHAR(255)  COMMENT 'ตำบล',
    `raw_district`                       VARCHAR(255)  COMMENT 'อำเภอ',
    `raw_province_code`                   VARCHAR(20)   COMMENT 'รหัสจังหวัด',
    `raw_province`                        VARCHAR(255)  COMMENT 'จังหวัด',
    `raw_postal_code`                      VARCHAR(20)   COMMENT 'รหัสไปรษณีย์',
    `raw_phone`                            VARCHAR(100)  COMMENT 'โทรศัพท์',
    `raw_building_value`                   DECIMAL(20,2) COMMENT 'ค่าอาคาร',
    `raw_land_value`                       DECIMAL(20,2) COMMENT 'ค่าที่ดิน',
    `raw_machinery_value`                   DECIMAL(20,2) COMMENT 'ค่าเครื่องจักร',
    `raw_working_capital`                   DECIMAL(20,2) COMMENT 'เงินทุนหมุนเวียน',
    `raw_total_investment`                   DECIMAL(20,2) COMMENT 'เงินลงทุนรวม',
    `raw_male_workers`                        INT           COMMENT 'ชาย',
    `raw_female_workers`                       INT           COMMENT 'หญิง',
    `raw_total_workers`                         INT           COMMENT 'คนงานรวม',
    `raw_total_horsepower`                       DECIMAL(20,2) COMMENT 'แรงม้ารวม',
    `raw_factory_area_sqm`                       DECIMAL(20,2) COMMENT 'พื้นที่โรงงาน(ตร.ม.)',
    `raw_building_area_sqm`                       DECIMAL(20,2) COMMENT 'พื้นที่อาคาร(ตร.ม.)',

    KEY `idx_factory_bronze_year`     (`source_permit_year_be`),
    KEY `idx_factory_bronze_province` (`raw_province`),
    KEY `idx_factory_bronze_tsic`     (`raw_tsic_code`),
    KEY `idx_factory_bronze_reg_no`   (`raw_factory_reg_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Bronze landing table for nationwide factory registry lists (BE 2567 / 2568 permit-year workbooks). Near-raw, 1:1 with source sheet rows; numeric cells typed as delivered by Excel, text/codes kept as VARCHAR.';

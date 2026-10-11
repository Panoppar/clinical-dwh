-- ============================================================================
-- 00_init_schemas_and_grants.sql
-- Runs ONCE automatically when the warehouse-db container first boots
-- (mounted into /docker-entrypoint-initdb.d). Creates the three Medallion
-- schemas and locks down access so Metabase can PHYSICALLY only read gold.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS bronze CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS silver CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS gold   CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- ELT service account: full DML/DDL rights across all three layers.
-- Used only by the elt-runner container, never by Metabase.
-- ----------------------------------------------------------------------------
CREATE USER IF NOT EXISTS 'dwh_elt'@'%' IDENTIFIED BY 'ChangeMe_DWH_2026!';
GRANT ALL PRIVILEGES ON bronze.* TO 'dwh_elt'@'%';
GRANT ALL PRIVILEGES ON silver.* TO 'dwh_elt'@'%';
GRANT ALL PRIVILEGES ON gold.*   TO 'dwh_elt'@'%';

-- ----------------------------------------------------------------------------
-- Metabase service account: SELECT-only, GOLD-only. This is the enforcement
-- point for "BI tool connects strictly to the Gold tier" — Metabase's
-- credentials cannot see bronze/silver even if someone adds a second
-- connection by mistake.
-- ----------------------------------------------------------------------------
CREATE USER IF NOT EXISTS 'metabase_ro'@'%' IDENTIFIED BY 'ChangeMe_Metabase_Ro_2026!';
GRANT SELECT ON gold.* TO 'metabase_ro'@'%';

FLUSH PRIVILEGES;

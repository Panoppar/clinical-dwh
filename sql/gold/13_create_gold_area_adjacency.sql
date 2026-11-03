-- ============================================================================
-- GOLD LAYER — bridge_area_adjacency
--
-- Precomputed polygon-contiguity graph over dim_area's 312 catchment units,
-- built for the kmch-ml community-labels project's CL-G1 (DEGURBA
-- urban/cluster/rural) rule, which needs to know which units touch which
-- (rook = shares a real edge, queen = corner-touch counts too).
--
-- Computed once here from already-landed bronze.geo_boundary_polygon data
-- (same "compute once in Gold, re-derive on every refresh" philosophy as
-- agg_industrial_concentration_by_unit_division, sql/gold/10) rather than
-- recomputed client-side on every scheduled ML run -- keeps the ML
-- container free of GIS dependencies and this unchanging geometry computed
-- exactly once per pipeline run, not once per day for no reason.
--
-- Full rebuild every run (DROP+CREATE, not incremental) -- same convention
-- as sql/gold/10's aggregate tables: this is a derived snapshot, not
-- something with meaningful incremental delta semantics.
-- ============================================================================

USE gold;

DROP TABLE IF EXISTS `bridge_area_adjacency`;

CREATE TABLE `bridge_area_adjacency` (
    `adjacency_id`       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `area_key_a`         INT UNSIGNED NOT NULL COMMENT 'always < area_key_b -- each pair stored once',
    `area_key_b`         INT UNSIGNED NOT NULL,
    `shared_boundary_m`  DECIMAL(12,2) NOT NULL COMMENT 'approximate length of shared polygon boundary in meters -- 0 for a corner-only (queen-only) touch',
    `is_rook`            TINYINT(1) NOT NULL COMMENT '1 if shared_boundary_m > 10m (DEGURBA rook/centre-tier contiguity), 0 if corner-touch only (queen-only/cluster-tier)',
    UNIQUE KEY `ux_baa_pair` (`area_key_a`, `area_key_b`),
    KEY `ix_baa_b` (`area_key_b`),
    CONSTRAINT `fk_baa_a` FOREIGN KEY (`area_key_a`) REFERENCES `dim_area` (`area_key`),
    CONSTRAINT `fk_baa_b` FOREIGN KEY (`area_key_b`) REFERENCES `dim_area` (`area_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

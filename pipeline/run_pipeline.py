"""
Orchestrates the Bronze -> Silver -> Gold pipeline for this warehouse's
live-API sources: NSO income, BMA community, DIW factory registry, DDS
disease ranking, HDC health-status (incl. 4 PM2.5-linked weekly reports),
Thailand admin-boundary reference data (dim_area input), and OSM/OSRM
hospital-access data. Plus one deliberate file-based exception: kmch-ml's
own tambon-to-unit crosswalk (see docs/06_kmch_ml_gap_closure_plan.md,
Gap 4), needed to group dim_area's 7 Bangkok post-2019 khwaeng-split
groups correctly -- not derivable from any live source.

Usage (normally invoked via docker compose, not directly):
    docker compose run --rm elt-runner

Each layer is a full refresh: every *.sql script in sql/<layer>/ drops and
recreates its own tables, so reruns are idempotent — there is no manual
cleanup step between runs. One exception to the usual Bronze-all ->
Silver-all -> Gold-all ordering: OSRM's ingest reads gold.dim_area's unit
centroids as its source points, so it runs between Gold dimensions and
Gold facts, not alongside the other live sources -- see the inline
comment at that call site.

Pruned on 2026-10-25/26 to cover only the live-API sources -- the
file-based Bronze/Silver sources and the old Gold layer (DOPA, HDC manual
exports, Lat Krabang, KMCH, factory_list, DDS health region, the old
file-based NSO, HDC region6_13, other_health, and every Gold dimension/
fact table, all of which depended on those sources) were removed on
explicit instruction. A new Gold layer was then built from scratch,
designed bottom-up from the KPI tree + dashboard design in
Excel\\KPI_Tree_and_Dashboard_Design.xlsx, then extended toward kmch-ml
input parity (dim_area, weekly HDC, hospital-access) on 2026-10-26. See
docs/03_external_reference_sources.md for verification status.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pymysql

SQL_ROOT = Path(__file__).parent / "sql"

DWH_HOST = os.environ["DWH_DB_HOST"]
DWH_PORT = int(os.environ["DWH_DB_PORT"])
DWH_USER = os.environ["DWH_DB_USER"]
DWH_PASSWORD = os.environ["DWH_DB_PASSWORD"]

BRONZE_SCRIPTS: list[str] = [
    "bronze/10_create_bronze_api_sources.sql",
    "bronze/11_create_bronze_geo_boundary.sql",
    "bronze/12_create_bronze_geo_access.sql",
    "bronze/13_create_bronze_tambon_xwalk.sql",
    "bronze/14_create_bronze_dopa_population.sql",
    "bronze/16_create_bronze_doe_migrant_worker.sql",
    "bronze/17_create_bronze_bma_zone_districts.sql",
]
SILVER_SCRIPTS: list[str] = [
    "silver/18_create_silver_api_sources.sql",
    "silver/19_create_silver_geo_boundary.sql",
    "silver/20_create_silver_geo_access.sql",
    "silver/21_create_silver_dopa_population.sql",
    "silver/23_create_silver_doe_migrant_worker.sql",
]
GOLD_SCRIPTS: list[str] = [
    "gold/01_create_gold_dimensions.sql",
    "gold/02_create_gold_facts.sql",
    "gold/03_create_gold_agg_obt.sql",
    "gold/04_create_gold_area_dimension.sql",
    "gold/05_create_gold_hdc_weekly_facts.sql",
    "gold/06_create_gold_facility_access.sql",
    "gold/07_create_gold_tambon_xwalk.sql",
    "gold/08_create_gold_population_facts.sql",
    "gold/09_create_gold_industry_division.sql",
    "gold/10_create_gold_industrial_concentration.sql",
    "gold/11_create_gold_bma_zone.sql",
]


def wait_for_mysql(host: str, port: int, user: str, password: str, label: str, timeout_s: int = 60) -> None:
    deadline = time.time() + timeout_s
    last_error = None
    while time.time() < deadline:
        try:
            conn = pymysql.connect(host=host, port=port, user=user, password=password, connect_timeout=5)
            conn.close()
            print(f"[wait] {label} is ready")
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(2)
    raise RuntimeError(f"{label} did not become ready within {timeout_s}s: {last_error}")


def run_live_source(label: str, ingest_fn, load_fn) -> None:
    """Live government APIs (NSO/BMA/DIW/DDS/HDC) can go down transiently and
    independently of this pipeline (confirmed live: DDS's own backend was
    returning a server-side DB-driver error on 2026-10-25, unrelated to any
    request this pipeline sends). One external outage must not abort the
    whole run for every other source, so a failure here is logged and the
    run moves on. Despite the name, also used for file-based sources (see
    the tambon-unit crosswalk call below) -- the same resilience applies:
    a missing/unreadable local file shouldn't abort every other source
    either. Each call site's own label says "live API" or "file-based"."""
    print(f"\n=== BRONZE: ingest + load {label} ===")
    try:
        ingest_fn()
        load_fn()
    except Exception as exc:  # noqa: BLE001
        print(f"[pipeline] WARNING: {label} failed, skipping ({type(exc).__name__}: {exc})", file=sys.stderr)


def run_sql_file(relative_path: str) -> None:
    sql_path = SQL_ROOT / relative_path
    print(f"[sql] executing {relative_path}")
    env = os.environ.copy()
    env["MYSQL_PWD"] = DWH_PASSWORD  # avoids exposing the password in argv/process list
    with open(sql_path, "rb") as f:
        subprocess.run(
            # --default-character-set=utf8mb4 is explicit, not relied on as a
            # client default -- confirmed by direct testing that MySQL's own
            # server-image mysql client defaults to latin1, which silently
            # corrupts Thai string-literal comparisons in WHERE/JOIN clauses
            # (observed: a working 17-candidate match dropped to 7 under the
            # wrong charset, with no error raised). This image's
            # default-mysql-client (Debian mariadb-client) happened to
            # default correctly, but that was never guaranteed by anything
            # in this file.
            ["mysql", "--default-character-set=utf8mb4", "-h", DWH_HOST, "-P", str(DWH_PORT), "-u", DWH_USER],
            stdin=f,
            env=env,
            check=True,
        )


def print_row_counts(schema: str, tables: list[str]) -> None:
    conn = pymysql.connect(host=DWH_HOST, port=DWH_PORT, user=DWH_USER, password=DWH_PASSWORD, database=schema)
    print(f"\n[summary] {schema} layer row counts")
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM `{table}`")
            (count,) = cur.fetchone()
            print(f"  {schema}.{table:<28} {count}")
    conn.close()


def print_bronze_summary() -> None:
    print_row_counts("bronze", [
        "api_nso_income", "api_bma_community", "api_diw_factory",
        "api_dds_disease_ranking", "api_hdc_report_catalog", "api_hdc_observations",
    ])
    print_row_counts("bronze", ["geo_boundary_subdistrict", "geo_boundary_district", "geo_boundary_polygon"])
    print_row_counts("bronze", ["geo_hospital_facility", "geo_travel_matrix"])
    print_row_counts("bronze", ["tambon_xwalk"])
    print_row_counts("bronze", ["dopa_population_year", "dopa_population_supplement"])
    print_row_counts("bronze", ["doe_migrant_worker_monthly"])
    print_row_counts("bronze", ["bma_zone_districts"])


def print_silver_summary() -> None:
    print_row_counts("silver", [
        "api_nso_income", "api_bma_community", "api_diw_factory",
        "api_dds_disease_ranking", "api_hdc_observations",
    ])
    print_row_counts("silver", ["geo_boundary_subdistrict", "geo_boundary_district"])
    print_row_counts("silver", ["geo_hospital_facility", "geo_travel_matrix"])
    print_row_counts("silver", ["dopa_population_by_unit_year"])
    print_row_counts("silver", ["doe_migrant_worker_permit_monthly"])


def print_gold_summary() -> None:
    print_row_counts("gold", [
        "dim_date", "dim_geography", "dim_industry", "dim_hdc_report", "dim_disease", "dim_area",
        "dim_tambon_unit_xwalk", "dim_facility", "dim_industry_division", "dim_bma_zone",
    ])
    print_row_counts("gold", [
        "fact_income", "fact_factory", "fact_community_population",
        "fact_disease_ranking", "fact_hdc_observation", "fact_hdc_weekly_observation", "fact_hospital_access",
        "fact_population_by_area", "fact_migrant_worker_permit", "bridge_bma_zone_district",
    ])
    print_row_counts("gold", [
        "agg_economic_by_province_year", "agg_population_by_district_year",
        "agg_health_kpi_by_province_year", "obt_regional_composite_index",
        "agg_industrial_concentration_by_unit_division", "agg_industrial_concentration_by_unit",
    ])


def main() -> None:
    wait_for_mysql(DWH_HOST, DWH_PORT, DWH_USER, DWH_PASSWORD, "warehouse-db")

    print("\n=== BRONZE: create tables ===")
    for script in BRONZE_SCRIPTS:
        run_sql_file(script)

    import ingest_api_nso, extract_load_api_nso
    run_live_source("live NSO income API", ingest_api_nso.run, extract_load_api_nso.run)

    import ingest_api_bma, extract_load_api_bma
    run_live_source("live BMA community API", ingest_api_bma.run, extract_load_api_bma.run)

    import ingest_api_diw, extract_load_api_diw
    run_live_source("live DIW factory registry API", ingest_api_diw.run, extract_load_api_diw.run)

    import ingest_api_dds, extract_load_api_dds
    run_live_source("live DDS disease ranking API", ingest_api_dds.run, extract_load_api_dds.run)

    import ingest_api_hdc, extract_load_api_hdc
    run_live_source("live HDC health-status API", ingest_api_hdc.run, extract_load_api_hdc.run)

    import ingest_api_geo_boundary, extract_load_api_geo_boundary
    run_live_source("live Thailand admin-boundary reference (dim_area input)",
                     ingest_api_geo_boundary.run, extract_load_api_geo_boundary.run)

    import ingest_api_osm, extract_load_api_osm
    run_live_source("live OSM hospital facilities (Overpass API)", ingest_api_osm.run, extract_load_api_osm.run)

    import ingest_file_tambon_xwalk, extract_load_file_tambon_xwalk
    run_live_source("file-based tambon-unit crosswalk (dim_area grouping fix, kmch-ml input-parity gap 4/6)",
                     ingest_file_tambon_xwalk.run, extract_load_file_tambon_xwalk.run)

    # Must run after tambon-unit crosswalk above -- resolves unit_codes from
    # bronze.tambon_xwalk directly (see extract_load_api_dopa_population.py's
    # docstring for why this reads Bronze instead of Gold).
    import ingest_api_dopa_population, extract_load_api_dopa_population
    run_live_source("live DOPA population (kmch-ml input-parity gap 1)",
                     ingest_api_dopa_population.run, extract_load_api_dopa_population.run)

    import ingest_file_dopa_population, extract_load_file_dopa_population
    run_live_source("file-based DOPA population supplement (2560-2564 backfill, kmch-ml input-parity gap 1)",
                     ingest_file_dopa_population.run, extract_load_file_dopa_population.run)

    import ingest_api_doe_migrant_worker, extract_load_api_doe_migrant_worker
    run_live_source("live DOE migrant worker permit monthly PDF (kmch-ml input-parity gap 2)",
                     ingest_api_doe_migrant_worker.run, extract_load_api_doe_migrant_worker.run)

    import ingest_file_bma_zone_districts, extract_load_file_bma_zone_districts
    run_live_source("file-based BMA zone-district mapping (static geography, dim_bma_zone input)",
                     ingest_file_bma_zone_districts.run, extract_load_file_bma_zone_districts.run)

    print("\n=== SILVER: create tables + transform ===")
    for script in SILVER_SCRIPTS:
        run_sql_file(script)

    print("\n=== SILVER: cleanse + conform live-API sources ===")
    import transform_silver_api_nso
    transform_silver_api_nso.run()
    import transform_silver_api_bma
    transform_silver_api_bma.run()
    import transform_silver_api_diw
    transform_silver_api_diw.run()
    import transform_silver_api_dds
    transform_silver_api_dds.run()
    import transform_silver_api_hdc
    transform_silver_api_hdc.run()
    import transform_silver_geo_boundary
    transform_silver_geo_boundary.run()
    import transform_silver_geo_access
    transform_silver_geo_access.run_facility()  # travel_matrix comes later -- see mid-Gold OSRM stage below
    import transform_silver_dopa_population
    transform_silver_dopa_population.run()  # must run before transform_gold_dimensions.run() -- _build_dim_date reads its year_ce range
    import transform_silver_doe_migrant_worker
    transform_silver_doe_migrant_worker.run()

    print("\n=== GOLD: create tables ===")
    for script in GOLD_SCRIPTS:
        run_sql_file(script)

    print("\n=== GOLD: build dimensions ===")
    import transform_gold_dimensions
    transform_gold_dimensions.run()

    # OSRM needs gold.dim_area's unit centroids as its source points (a real
    # dependency, not an ordering convenience) -- ingest + Bronze shred +
    # Silver transform for the travel matrix specifically happen here,
    # between Gold dimensions and Gold facts, not in the earlier Bronze/
    # Silver phases alongside every other source.
    import ingest_api_osrm, extract_load_api_osrm
    run_live_source("live OSRM hospital travel matrix", ingest_api_osrm.run, extract_load_api_osrm.run)
    transform_silver_geo_access.run_travel_matrix()

    print("\n=== GOLD: build facts ===")
    import transform_gold_facts
    transform_gold_facts.run()

    print("\n=== GOLD: build aggregates + composite index ===")
    import transform_gold_agg
    transform_gold_agg.run()

    print_bronze_summary()
    print_silver_summary()
    print_gold_summary()
    print("\n[pipeline] completed successfully")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"[pipeline] FAILED running SQL script (exit {exc.returncode})", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"[pipeline] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

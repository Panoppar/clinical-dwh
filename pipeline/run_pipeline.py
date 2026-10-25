"""
Orchestrates the Bronze -> Silver pipeline for the 5 live-API sources
(NSO income, BMA community, DIW factory registry, DDS disease ranking,
HDC health-status).

Usage (normally invoked via docker compose, not directly):
    docker compose run --rm elt-runner

Each layer is a full refresh: every *.sql script in sql/<layer>/ drops and
recreates its own tables, so reruns are idempotent — there is no manual
cleanup step between runs.

Pruned on 2026-10-26 to cover only the live-API sources -- the file-based
Bronze/Silver sources and the old Gold layer (DOPA, HDC manual exports,
Lat Krabang, KMCH, factory_list, DDS health region, the old file-based
NSO, HDC region6_13, other_health, and every Gold dimension/fact table,
all of which depended on those sources) were removed on explicit
instruction. A new Gold layer was then built from scratch for the 5
live-API sources, designed bottom-up from the KPI tree + dashboard design
in Excel\\KPI_Tree_and_Dashboard_Design.xlsx. See
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
]
SILVER_SCRIPTS: list[str] = [
    "silver/18_create_silver_api_sources.sql",
]
GOLD_SCRIPTS: list[str] = [
    "gold/01_create_gold_dimensions.sql",
    "gold/02_create_gold_facts.sql",
    "gold/03_create_gold_agg_obt.sql",
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
    run moves on."""
    print(f"\n=== BRONZE: ingest + load live {label} ===")
    try:
        ingest_fn()
        load_fn()
    except Exception as exc:  # noqa: BLE001
        print(f"[pipeline] WARNING: live {label} failed, skipping ({type(exc).__name__}: {exc})", file=sys.stderr)


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


def print_silver_summary() -> None:
    print_row_counts("silver", [
        "api_nso_income", "api_bma_community", "api_diw_factory",
        "api_dds_disease_ranking", "api_hdc_observations",
    ])


def print_gold_summary() -> None:
    print_row_counts("gold", ["dim_date", "dim_geography", "dim_industry", "dim_hdc_report", "dim_disease"])
    print_row_counts("gold", [
        "fact_income", "fact_factory", "fact_community_population",
        "fact_disease_ranking", "fact_hdc_observation",
    ])
    print_row_counts("gold", [
        "agg_economic_by_province_year", "agg_population_by_district_year",
        "agg_health_kpi_by_province_year", "obt_regional_composite_index",
    ])


def main() -> None:
    wait_for_mysql(DWH_HOST, DWH_PORT, DWH_USER, DWH_PASSWORD, "warehouse-db")

    print("\n=== BRONZE: create tables ===")
    for script in BRONZE_SCRIPTS:
        run_sql_file(script)

    import ingest_api_nso, extract_load_api_nso
    run_live_source("NSO income API", ingest_api_nso.run, extract_load_api_nso.run)

    import ingest_api_bma, extract_load_api_bma
    run_live_source("BMA community API", ingest_api_bma.run, extract_load_api_bma.run)

    import ingest_api_diw, extract_load_api_diw
    run_live_source("DIW factory registry API", ingest_api_diw.run, extract_load_api_diw.run)

    import ingest_api_dds, extract_load_api_dds
    run_live_source("DDS disease ranking API", ingest_api_dds.run, extract_load_api_dds.run)

    import ingest_api_hdc, extract_load_api_hdc
    run_live_source("HDC health-status API", ingest_api_hdc.run, extract_load_api_hdc.run)

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

    print("\n=== GOLD: create tables ===")
    for script in GOLD_SCRIPTS:
        run_sql_file(script)

    print("\n=== GOLD: build dimensions ===")
    import transform_gold_dimensions
    transform_gold_dimensions.run()

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

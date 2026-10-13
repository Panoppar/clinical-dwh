"""
Orchestrates the full Bronze -> Silver -> Gold run.

Usage (normally invoked via docker compose, not directly):
    docker compose run --rm elt-runner

Each layer is a full refresh: every *.sql script in sql/<layer>/ drops and
recreates its own tables, so reruns are idempotent — there is no manual
cleanup step between runs.

Rebuilt from scratch on 2026-10-13 against the reorganized
share_unprocessed_20261010 folder. Sources are added one at a time; see
docs/03_external_reference_sources.md for progress.
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

# Execution order matters: each layer's DDL must run before its DML, and
# Gold DDL/DML order matters because facts carry FKs into dimensions.
# Filled in source-by-source as each one is built.
BRONZE_SCRIPTS: list[str] = [
    "bronze/01_create_bronze_dopa_tables.sql",
    "bronze/02_create_bronze_hdc_manual_tables.sql",
]
SILVER_SCRIPTS: list[str] = []
GOLD_SCRIPTS: list[str] = []


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


def run_sql_file(relative_path: str) -> None:
    sql_path = SQL_ROOT / relative_path
    print(f"[sql] executing {relative_path}")
    env = os.environ.copy()
    env["MYSQL_PWD"] = DWH_PASSWORD  # avoids exposing the password in argv/process list
    with open(sql_path, "rb") as f:
        subprocess.run(
            ["mysql", "-h", DWH_HOST, "-P", str(DWH_PORT), "-u", DWH_USER],
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
        "dopa_population_by_area_month", "dopa_source_file_registry", "dopa_metadata_file_registry",
    ])
    print_row_counts("bronze", [
        "schema_registry", "report_catalog",
        "ncd_reports", "morbidity_mortality_causes",
        "occupational_environmental_diseases", "air_pollution_diseases",
    ])


def main() -> None:
    wait_for_mysql(DWH_HOST, DWH_PORT, DWH_USER, DWH_PASSWORD, "warehouse-db")

    print("\n=== BRONZE: create tables ===")
    for script in BRONZE_SCRIPTS:
        run_sql_file(script)

    print("\n=== BRONZE: load DOPA population-by-area files ===")
    import extract_load_dopa
    extract_load_dopa.run()

    print("\n=== BRONZE: load HDC manual exports ===")
    import extract_load_hdc_manual
    extract_load_hdc_manual.run()

    if SILVER_SCRIPTS:
        print("\n=== SILVER: create tables + transform ===")
        for script in SILVER_SCRIPTS:
            run_sql_file(script)

    if GOLD_SCRIPTS:
        print("\n=== GOLD: create star schema + build dimensions/facts ===")
        for script in GOLD_SCRIPTS:
            run_sql_file(script)

    print_bronze_summary()
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

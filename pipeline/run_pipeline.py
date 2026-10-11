"""
Orchestrates the full Bronze -> Silver -> Gold run.

Usage (normally invoked via docker compose, not directly):
    docker compose run --rm elt-runner

Each layer is a full refresh: every *.sql script in sql/<layer>/ drops and
recreates its own tables, so reruns are idempotent — there is no manual
cleanup step between runs.
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

SOURCE_HOST = os.environ["SOURCE_DB_HOST"]
SOURCE_PORT = int(os.environ["SOURCE_DB_PORT"])
SOURCE_USER = os.environ["SOURCE_DB_USER"]
SOURCE_PASSWORD = os.environ["SOURCE_DB_PASSWORD"]
SOURCE_DB_NAME = os.environ["SOURCE_DB_NAME"]

# Execution order matters: each layer's DDL must run before its DML, and
# Gold DDL/DML order matters because facts carry FKs into dimensions.
BRONZE_SCRIPTS = [
    "bronze/01_create_bronze_tables.sql",
    "bronze/02_create_bronze_external_reference_tables.sql",
    "bronze/03_create_bronze_thai_geo_tables.sql",
]
SILVER_SCRIPTS = [
    "silver/01_create_silver_tables.sql",
    "silver/02_transform_silver.sql",
    "silver/03_create_silver_reference_tables.sql",
    "silver/04_transform_silver_reference.sql",
    "silver/05_create_silver_crosswalk_tables.sql",
    "silver/06_transform_silver_crosswalk.sql",
]
GOLD_SCRIPTS = [
    "gold/01_create_gold_dimensions.sql",
    "gold/02_create_gold_facts.sql",
    "gold/03_load_dim_date.sql",
    "gold/04_load_gold_dimensions.sql",
    "gold/05_load_gold_facts.sql",
    "gold/06_create_gold_population_reference.sql",
    "gold/07_load_gold_population_reference.sql",
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


def print_gold_summary() -> None:
    print_row_counts("gold", [
        "Dim_Date", "Dim_Patient", "Dim_Company", "Dim_Question", "Dim_Vaccine",
        "Dim_Vaccine_Lot", "Dim_District_Population", "Fact_Patient_Registration",
        "Fact_Screening_Response", "Fact_Vaccination",
    ])


def print_reference_summary() -> None:
    print_row_counts("bronze", ["dopa_population_monthly", "nso_population_registration"])
    print_row_counts("silver", ["population_reference_subdistrict", "population_reference_age_sex"])


def main() -> None:
    wait_for_mysql(SOURCE_HOST, SOURCE_PORT, SOURCE_USER, SOURCE_PASSWORD, "source-db")
    wait_for_mysql(DWH_HOST, DWH_PORT, DWH_USER, DWH_PASSWORD, "warehouse-db")

    print("\n=== BRONZE: create tables ===")
    for script in BRONZE_SCRIPTS:
        run_sql_file(script)

    print("\n=== BRONZE: extract from source, load raw replicas ===")
    import extract_load_bronze
    extract_load_bronze.run()

    print("\n=== BRONZE: load external population reference files ===")
    import extract_load_external_reference
    extract_load_external_reference.run()

    print("\n=== SILVER: create tables + transform ===")
    for script in SILVER_SCRIPTS:
        run_sql_file(script)

    print("\n=== GOLD: create star schema + build dimensions/facts ===")
    for script in GOLD_SCRIPTS:
        run_sql_file(script)

    print_reference_summary()
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

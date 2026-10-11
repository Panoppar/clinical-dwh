"""
Orchestrates the full Bronze -> Silver -> Gold run.

Usage (normally invoked via docker compose, not directly):
    docker compose run --rm elt-runner

Each layer is a full refresh: every *.sql script in sql/<layer>/ drops and
recreates its own tables, so reruns are idempotent — there is no manual
cleanup step between runs.

This warehouse is built entirely from externally-sourced reference data
(DOPA/NSO population, HDC/DDS health surveillance, Lat Krabang/KMCH
local-area data) from the shared Drive folder -- there is no clinic/
patient source system feeding it.
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
BRONZE_SCRIPTS = [
    "bronze/02_create_bronze_external_reference_tables.sql",
    "bronze/03_create_bronze_thai_geo_tables.sql",
    "bronze/04_create_bronze_hdc_dds_tables.sql",
    "bronze/05_create_bronze_lat_krabang_tables.sql",
    "bronze/06_create_bronze_kmch_other_health_tables.sql",
]
SILVER_SCRIPTS = [
    "silver/03_create_silver_reference_tables.sql",
    "silver/04_transform_silver_reference.sql",
    "silver/05_create_silver_crosswalk_tables.sql",
    "silver/06_transform_silver_crosswalk.sql",
    "silver/07_create_silver_phase2_tables.sql",
    "silver/08_transform_silver_phase2.sql",
]
GOLD_SCRIPTS = [
    "gold/06_create_gold_population_reference.sql",
    "gold/07_load_gold_population_reference.sql",
    "gold/08_create_gold_population_age_sex.sql",
    "gold/09_load_gold_population_age_sex.sql",
    "gold/10_create_gold_phase2_facts.sql",
    "gold/11_load_gold_phase2_facts.sql",
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
        "Dim_District_Population", "Dim_Population_By_Age_Sex",
        "Fact_HDC_Pop_Age", "Fact_HDC_Incidence", "Fact_HDC_Death_Age",
        "Fact_DDS_Disease_Ranking", "Fact_Lat_Krabang_Population", "Fact_Lat_Krabang_Deaths",
        "Dim_Lat_Krabang_POI",
    ])


def print_reference_summary() -> None:
    print_row_counts("bronze", ["dopa_population_monthly", "nso_population_registration"])
    print_row_counts("silver", ["population_reference_subdistrict", "population_reference_age_sex"])
    print_row_counts("bronze", [
        "hdc_disease_pop_age", "hdc_disease_incidence", "hdc_disease_death_age",
        "dds_yearly_disease_ranking", "dds_unit_indicator_snapshot", "hdc_occupational_health",
        "dds_pdf_report_inventory", "kmch_catchment_places",
        "other_health_disease_cases", "other_health_subdistrict_cases",
        "other_health_sick_by_group", "other_health_disease_by_year",
        "lat_krabang_population_by_subdistrict", "lat_krabang_deaths_by_subdistrict",
        "lat_krabang_universities", "lat_krabang_vocational_colleges", "lat_krabang_schools",
        "lat_krabang_risk_points", "lat_krabang_religious_sites", "lat_krabang_businesses",
        "lat_krabang_hospitals",
    ])
    print_row_counts("silver", [
        "hdc_disease_pop_age", "hdc_disease_incidence", "hdc_disease_death_age",
        "dds_yearly_disease_ranking", "lat_krabang_population_by_subdistrict",
        "lat_krabang_deaths_by_subdistrict", "lat_krabang_points_of_interest", "kmch_catchment_places",
        "other_health_disease_cases", "other_health_subdistrict_cases",
        "other_health_sick_by_group", "other_health_disease_by_year",
    ])


def main() -> None:
    wait_for_mysql(DWH_HOST, DWH_PORT, DWH_USER, DWH_PASSWORD, "warehouse-db")

    print("\n=== BRONZE: create tables ===")
    for script in BRONZE_SCRIPTS:
        run_sql_file(script)

    print("\n=== BRONZE: load external population reference files ===")
    import extract_load_external_reference
    extract_load_external_reference.run()

    print("\n=== BRONZE: load Phase 2 shared-drive data (HDC/DDS/Lat Krabang/KMCH/other) ===")
    import extract_load_phase2
    extract_load_phase2.run()

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

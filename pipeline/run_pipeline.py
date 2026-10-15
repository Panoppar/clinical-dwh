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
    "bronze/03_create_bronze_lat_krabang_tables.sql",
    "bronze/04_create_bronze_kmch_tables.sql",
    "bronze/05_create_bronze_factory_list_tables.sql",
    "bronze/06_create_bronze_dds_health_region_tables.sql",
    "bronze/07_create_bronze_nso_tables.sql",
    "bronze/08_create_bronze_hdc_region6_13_tables.sql",
    "bronze/09_create_bronze_other_health_tables.sql",
]
SILVER_SCRIPTS: list[str] = [
    "silver/01_create_silver_dopa_tables.sql",
    "silver/02_transform_silver_dopa.sql",
    "silver/03_create_silver_nso_tables.sql",
    "silver/04_create_silver_other_health_population_tables.sql",
    "silver/05_create_silver_hdc_manual_tables.sql",
    "silver/06_create_silver_hdc_region6_13_tables.sql",
    "silver/07_transform_silver_hdc_region6_13.sql",
    "silver/08_create_silver_dds_health_region_tables.sql",
    "silver/09_transform_silver_dds_health_region.sql",
    "silver/10_create_silver_other_health_disease_tables.sql",
    "silver/11_transform_silver_other_health_disease.sql",
    "silver/12_create_silver_lat_krabang_tables.sql",
    "silver/13_transform_silver_lat_krabang.sql",
    "silver/14_create_silver_kmch_factory_tables.sql",
    "silver/15_transform_silver_kmch_factory.sql",
    "silver/16_create_silver_other_health_local_tables.sql",
    "silver/17_transform_silver_other_health_local.sql",
]
# Split in two: scripts before dim_geography is populated (pure DDL, or
# dimensions sourced straight from Silver) vs. scripts after (fact tables
# that JOIN against dim_geography, which transform_gold_dim_geography.py
# populates in Python between the two lists -- it's created as an empty
# table by 02_create_dim_geography.sql but only gets rows via that script).
GOLD_SCRIPTS_PRE_GEO: list[str] = [
    "gold/01_create_dim_date.sql",
    "gold/02_create_dim_geography.sql",
    "gold/03_create_dim_age_sex_and_component.sql",
]
GOLD_SCRIPTS_POST_GEO: list[str] = [
    "gold/04_create_fact_population_by_area.sql",
    "gold/05_transform_fact_population_by_area.sql",
    "gold/06_create_fact_population_age_sex.sql",
    "gold/07_transform_fact_population_age_sex.sql",
    "gold/08_create_obt_population_by_geography.sql",
    "gold/09_transform_obt_population_by_geography.sql",
    "gold/10_create_agg_population_summary_yearly.sql",
    "gold/11_transform_agg_population_summary_yearly.sql",
    "gold/12_create_feat_geography_month.sql",
    "gold/13_transform_feat_geography_month.sql",
    "gold/14_create_dim_disease.sql",
    "gold/15_create_fact_disease_event.sql",
    "gold/16_transform_fact_disease_event.sql",
    "gold/17_create_fact_disease_incidence_hdc.sql",
    "gold/18_transform_fact_disease_incidence_hdc.sql",
    "gold/19_create_obt_disease_surveillance.sql",
    "gold/20_transform_obt_disease_surveillance.sql",
    "gold/21_create_agg_disease_kpi_monthly.sql",
    "gold/22_transform_agg_disease_kpi_monthly.sql",
    "gold/23_alter_feat_geography_month_add_disease.sql",
    "gold/24_transform_feat_geography_month_disease.sql",
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


def print_bronze_summary() -> None:
    print_row_counts("bronze", [
        "dopa_population_by_area_month", "dopa_source_file_registry", "dopa_metadata_file_registry",
    ])
    print_row_counts("bronze", [
        "schema_registry", "report_catalog",
        "ncd_reports", "morbidity_mortality_causes",
        "occupational_environmental_diseases", "air_pollution_diseases",
    ])
    print_row_counts("bronze", [
        "edu_vocational_college", "edu_university", "edu_school", "health_hospital",
        "religious_site", "business_establishment", "safety_risk_point", "community",
        "population_total", "population_death",
    ])
    print_row_counts("bronze", ["kmch_catchment_places"])
    print_row_counts("bronze", ["factory_list"])
    print_row_counts("bronze", ["dds_health_region_disease_report"])
    print_row_counts("bronze", [
        "ingestion_log", "pop_reg_national", "pop_reg_province",
        "pop_reg_structure_metadata", "pop_sur_survey",
    ])
    print_row_counts("bronze", [
        "inc_monthly_asthma", "inc_monthly_copd", "inc_monthly_coronary", "inc_monthly_dm", "inc_monthly_ht",
        "inc_annual_ihd",
        "pop_age_ca_breast", "pop_age_ca_cervix", "pop_age_ca_lung", "pop_age_copd", "pop_age_coronary",
        "pop_age_dm", "pop_age_emphysema", "pop_age_ht", "pop_age_stroke",
        "death_age_copd", "death_age_coronary", "death_age_dm", "death_age_ht",
    ])
    print_row_counts("bronze", [
        "sick_298group_long", "sick_298group_wide",
        "surveillance_top_diseases_2566", "surveillance_top_diseases_2567",
        "compare_cases_by_disease", "compare_cases_by_subdistrict",
        "ncd_mortality_multisheet", "cause_of_death_top10_with_rate", "cause_of_death_top10_no_rate",
        "population_by_age_subdistrict_bkk", "population_by_tambon_national",
        "elderly_dependency_by_district", "health_kpi_export",
        "community_count_by_district_bkk", "foreign_labor_permit_by_area_bkk",
        "_ingestion_manifest",
    ])


def print_silver_summary() -> None:
    print_row_counts("silver", ["population_by_area_month"])
    print_row_counts("silver", [
        "pop_indicator_lookup", "population_reference_age_sex", "labor_force_survey",
    ])
    print_row_counts("silver", [
        "population_by_age_subdistrict_bkk", "population_by_tambon_national",
        "elderly_dependency_by_district",
    ])
    print_row_counts("silver", ["hdc_indicator_observations"])
    print_row_counts("silver", [
        "hdc_incidence_monthly", "hdc_incidence_annual", "hdc_population_by_age", "hdc_death_by_age",
    ])
    print_row_counts("silver", ["dds_health_region_disease_report"])
    print_row_counts("silver", [
        "sick_298group_long", "sick_298group_wide", "surveillance_top_diseases",
        "compare_cases_by_disease", "compare_cases_by_subdistrict", "ncd_mortality_by_disease",
        "cause_of_death_top10_with_rate", "cause_of_death_top10_no_rate",
    ])
    print_row_counts("silver", [
        "edu_vocational_college", "edu_university", "edu_school", "health_hospital",
        "religious_site", "business_establishment", "safety_risk_point",
        "lat_krabang_population_by_subdistrict", "lat_krabang_deaths_by_subdistrict",
    ])
    print_row_counts("silver", ["kmch_catchment_places", "factory_list"])
    print_row_counts("silver", [
        "health_kpi_export", "community_count_by_district_bkk", "foreign_labor_permit_by_area_bkk",
    ])


def print_gold_summary() -> None:
    print_row_counts("gold", ["dim_date", "dim_geography", "dim_age_sex", "dim_population_component"])
    print_row_counts("gold", ["fact_population_by_area", "fact_population_age_sex"])
    print_row_counts("gold", ["obt_population_by_geography", "agg_population_summary_yearly", "feat_geography_month"])
    print_row_counts("gold", ["dim_disease", "fact_disease_event", "fact_disease_incidence_hdc"])
    print_row_counts("gold", ["obt_disease_surveillance", "agg_disease_kpi_monthly"])


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

    print("\n=== BRONZE: load Lat Krabang district office tables ===")
    import extract_load_lat_krabang
    extract_load_lat_krabang.run()

    print("\n=== BRONZE: load KMCH catchment places ===")
    import extract_load_kmch
    extract_load_kmch.run()

    print("\n=== BRONZE: load Factory list ===")
    import extract_load_factory_list
    extract_load_factory_list.run()

    print("\n=== BRONZE: load DDS health region weekly reports ===")
    import extract_load_dds_health_region
    extract_load_dds_health_region.run()

    print("\n=== BRONZE: load NSO population data ===")
    import extract_load_nso
    extract_load_nso.run()

    print("\n=== BRONZE: load HDC region6_13 by-age API exports ===")
    import extract_load_hdc_region6_13
    extract_load_hdc_region6_13.run()

    print("\n=== BRONZE: load other health & population tables ===")
    import extract_load_other_health
    extract_load_other_health.run()

    if SILVER_SCRIPTS:
        print("\n=== SILVER: create tables + transform ===")
        for script in SILVER_SCRIPTS:
            run_sql_file(script)

        print("\n=== SILVER: transform NSO population & labor force data ===")
        import transform_silver_nso
        transform_silver_nso.run()

        print("\n=== SILVER: transform other_health population tables ===")
        import transform_silver_other_health_population
        transform_silver_other_health_population.run()

        print("\n=== SILVER: unpivot HDC_manual_exports ===")
        import transform_silver_hdc_manual
        transform_silver_hdc_manual.run()

    if GOLD_SCRIPTS_PRE_GEO:
        print("\n=== GOLD: create dimensions ===")
        for script in GOLD_SCRIPTS_PRE_GEO:
            run_sql_file(script)

        print("\n=== GOLD: build dim_geography ===")
        import transform_gold_dim_geography
        transform_gold_dim_geography.run()

        print("\n=== GOLD: create + load facts ===")
        for script in GOLD_SCRIPTS_POST_GEO:
            run_sql_file(script)

    print_bronze_summary()
    if SILVER_SCRIPTS:
        print_silver_summary()
    if GOLD_SCRIPTS_PRE_GEO:
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

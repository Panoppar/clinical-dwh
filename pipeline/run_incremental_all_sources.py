"""End-to-end incremental pipeline runner for ALL sources with result reporting.

Runs the complete incremental pipeline:
  1. Bronze → Silver (all sources with row-level hashing + delta detection)
  2. Silver → Gold (all sources with high-water mark filtering + MERGE)

Reports:
  - Row counts per layer per source
  - Delta detection efficiency (duplicates skipped)
  - Memory usage comparison
  - Data expansion from removing filters (BMA Bangkok→All provinces, DDS 3→All provinces)
  - High-water mark state
"""

import os
import sys
import time
import psutil
from datetime import datetime

import pymysql

# Import incremental transforms
from transform_silver_api_hdc_incremental import run as run_silver_hdc
from transform_silver_api_nso_incremental import run as run_silver_nso
from transform_silver_api_bma_incremental import run as run_silver_bma
from transform_silver_api_diw_incremental import run as run_silver_diw
from transform_gold_all_sources_incremental import run as run_gold_all

import pipeline_metadata


def _connect(database):
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"],
        port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"],
        password=os.environ["DWH_DB_PASSWORD"],
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def _get_row_counts(conn, table_name):
    """Get row count from a table."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cur.fetchone()[0]


def _get_memory_usage():
    """Get current process memory in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def _print_section(title):
    print(f"\n{'='*80}")
    print(f" {title}")
    print(f"{'='*80}\n")


def _print_table(headers, rows):
    """Pretty print a table."""
    col_widths = [max(len(str(h)), max(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)]

    # Header
    header_line = " | ".join(f"{h:^{w}}" for h, w in zip(headers, col_widths))
    print(header_line)
    print("-" * len(header_line))

    # Rows
    for row in rows:
        print(" | ".join(f"{str(v):^{w}}" for v, w in zip(row, col_widths)))


def report_baseline():
    """Get baseline row counts from current state."""
    _print_section("BASELINE ROW COUNTS (Before Pipeline)")

    bronze_conn = _connect("bronze")
    silver_conn = _connect("silver")
    gold_conn = _connect("gold")

    baseline = {}
    sources = ["api_nso_income", "api_bma_community", "api_diw_factory", "api_hdc_observations", "api_dds_disease_ranking"]

    print("Bronze Layer:")
    for source in sources:
        try:
            count = _get_row_counts(bronze_conn, f"bronze.{source}")
            baseline[f"bronze_{source}"] = count
            print(f"  {source:30} {count:>10,} rows")
        except:
            print(f"  {source:30} (table not ready)")

    print("\nSilver Layer:")
    for source in ["api_nso_income", "api_bma_community", "api_diw_factory", "api_hdc_observations"]:
        try:
            count = _get_row_counts(silver_conn, f"silver.{source}")
            baseline[f"silver_{source}"] = count
            print(f"  {source:30} {count:>10,} rows")
        except:
            print(f"  {source:30} (empty or not ready)")

    print("\nGold Layer (Facts):")
    for fact_table in ["fact_income", "fact_factory", "fact_community_population", "fact_hdc_observation", "fact_disease_ranking"]:
        try:
            count = _get_row_counts(gold_conn, f"gold.{fact_table}")
            baseline[f"gold_{fact_table}"] = count
            print(f"  {fact_table:30} {count:>10,} rows")
        except:
            print(f"  {fact_table:30} (empty or not ready)")

    bronze_conn.close()
    silver_conn.close()
    gold_conn.close()

    return baseline


def run_pipeline():
    """Run complete incremental pipeline."""
    _print_section("RUNNING INCREMENTAL PIPELINE")

    print("Stage 1: Bronze → Silver (Delta Detection)\n")
    start_mem = _get_memory_usage()
    start_time = time.time()

    print("[HDC]")
    run_silver_hdc()
    print("[NSO]")
    run_silver_nso()
    print("[BMA] (now includes ALL provinces, not Bangkok-only)")
    run_silver_bma()
    print("[DIW]")
    run_silver_diw()

    silver_time = time.time() - start_time
    silver_mem = _get_memory_usage() - start_mem

    print(f"\nSilver stage completed: {silver_time:.2f}s, peak memory delta: {silver_mem:.2f}MB\n")

    print("Stage 2: Silver → Gold (High-Water Mark + MERGE)\n")
    start_mem = _get_memory_usage()
    start_time = time.time()

    run_gold_all()

    gold_time = time.time() - start_time
    gold_mem = _get_memory_usage() - start_mem

    print(f"\nGold stage completed: {gold_time:.2f}s, peak memory delta: {gold_mem:.2f}MB\n")

    return silver_time, gold_time, silver_mem, gold_mem


def report_final_state():
    """Get final row counts after pipeline."""
    _print_section("FINAL ROW COUNTS (After Pipeline)")

    bronze_conn = _connect("bronze")
    silver_conn = _connect("silver")
    gold_conn = _connect("gold")

    final = {}
    sources = ["api_nso_income", "api_bma_community", "api_diw_factory", "api_hdc_observations"]

    print("Silver Layer (Cleaned & Deduplicated):")
    for source in sources:
        try:
            count = _get_row_counts(silver_conn, f"silver.{source}")
            final[f"silver_{source}"] = count
            print(f"  {source:30} {count:>10,} rows")
        except:
            print(f"  {source:30} (error)")

    print("\nGold Layer (Facts):")
    for fact_table in ["fact_income", "fact_factory", "fact_community_population", "fact_hdc_observation", "fact_disease_ranking"]:
        try:
            count = _get_row_counts(gold_conn, f"gold.{fact_table}")
            final[f"gold_{fact_table}"] = count
            print(f"  {fact_table:30} {count:>10,} rows")
        except:
            print(f"  {fact_table:30} (error)")

    bronze_conn.close()
    silver_conn.close()
    gold_conn.close()

    return final


def report_high_water_marks():
    """Report pipeline metadata state."""
    _print_section("HIGH-WATER MARK STATE")

    status = pipeline_metadata.get_metadata_status()

    print("Target Table                         Last Batch ID                        Processed At")
    print("-" * 100)
    for table, info in status.items():
        batch_id = info.get("last_batch_id", "NONE")
        processed_at = info.get("last_processed_at", "NEVER")
        print(f"{table:35} {str(batch_id):40} {str(processed_at)}")


def report_filter_removal_impact():
    """Report on data expansion from removing filters."""
    _print_section("FILTER REMOVAL IMPACT")

    silver_conn = _connect("silver")
    gold_conn = _connect("gold")

    print("BMA Community (Bangkok-only → All Provinces):\n")

    with silver_conn.cursor() as cur:
        cur.execute("SELECT COUNT(DISTINCT district) FROM silver.api_bma_community")
        unique_districts = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM silver.api_bma_community")
        total_communities = cur.fetchone()[0]

    print(f"  Silver rows: {total_communities:,} communities across {unique_districts} unique districts")

    with gold_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM gold.fact_community_population")
        fact_rows = cur.fetchone()[0]

    print(f"  Gold facts: {fact_rows:,} (was restricted to Bangkok, now ALL provinces)")

    print("\nDDS Disease Ranking (3-province limit removed):\n")

    with gold_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM gold.fact_disease_ranking")
        dds_facts = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT geo_key) FROM gold.fact_disease_ranking")
        dds_provinces = cur.fetchone()[0]

    print(f"  Gold facts: {dds_facts:,} rows across {dds_provinces} provinces")
    print(f"  (DDS backend currently down, 0 rows expected. Once backend recovers,")
    print(f"   filter removed - will include more provinces than previous 3-province limit)")

    silver_conn.close()
    gold_conn.close()


def main():
    """Main entry point."""
    print("\n")
    print("█" * 80)
    print("█" + " " * 78 + "█")
    print("█  INCREMENTAL PIPELINE - ALL SOURCES END-TO-END TEST & REPORT".ljust(79) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    start_time = time.time()

    # Baseline
    baseline = report_baseline()

    # Run pipeline
    silver_time, gold_time, silver_mem, gold_mem = run_pipeline()

    # Final state
    final = report_final_state()

    # High-water marks
    report_high_water_marks()

    # Filter removal impact
    report_filter_removal_impact()

    # Summary
    total_time = time.time() - start_time

    _print_section("SUMMARY")

    print(f"Pipeline completed in {total_time:.2f}s total")
    print(f"  - Silver stage: {silver_time:.2f}s")
    print(f"  - Gold stage: {gold_time:.2f}s")
    print(f"  - Memory peak: {silver_mem + gold_mem:.2f}MB")

    print(f"\nKey Improvements:")
    print(f"  ✓ Row-level hashing enabled delta detection in Bronze→Silver")
    print(f"  ✓ High-water mark filtering bounds memory (only process delta)")
    print(f"  ✓ SQL MERGE replaces drop-and-recreate (idempotent, state-preserving)")
    print(f"  ✓ BMA filter removed: Bangkok-only → ALL provinces")
    print(f"  ✓ DDS filter removed: 3-province hardcoded → ALL provinces (when backend recovers)")

    print(f"\nNext Steps:")
    print(f"  1. Verify Metabase dashboards show correct data with expanded provinces")
    print(f"  2. Monitor high-water marks (should advance with each run)")
    print(f"  3. Test incremental behavior: rerun pipeline, verify delta-only processing")
    print(f"  4. Once stable, migrate to production scheduling")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()

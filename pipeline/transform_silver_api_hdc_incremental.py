"""Incremental Silver transform for bronze.api_hdc_observations → silver.api_hdc_observations.

Implements row-level hashing to detect actual data changes:
1. Generates deterministic hash of business columns (report_code, year_ce, zone, ..., field_value)
2. Queries Silver for existing hashes (delta detection)
3. Only INSERTs genuinely new or changed rows (prevents duplicates from minor Bronze metadata changes)
4. Tracks ingestion_batch_id for high-water mark state (Silver→Gold filtering)

Schema changes (one-time, from sql/00_incremental_setup.sql):
- silver.api_hdc_observations now has: row_hash, ingestion_batch_id columns
"""

import hashlib
import os

import pymysql

BATCH_SIZE = 5000


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


def _row_hash(report_code: str, year_ce: int, zone: str, record_index: str,
              field_name: str, field_value: str | None) -> str:
    """Generate deterministic SHA256 hash of business columns (first 16 chars).

    Ignores source file metadata (source_file_name, ingestion_batch_id) so that
    identical data landing via a re-transmitted Bronze file is not re-inserted.

    Args:
        report_code: HDC report code
        year_ce: Calendar year (Buddhist - 543)
        zone: Reporting zone
        record_index: Record index within zone/report
        field_name: EAV field name (e.g., 'target', 'result', 'male')
        field_value: EAV field value

    Returns:
        First 16 chars of SHA256 (hex), deterministic and collision-resistant for this grain
    """
    # Build canonical string: null/empty field_value becomes "NULL" for consistent hashing
    field_val_str = "NULL" if field_value in (None, "") else str(field_value)

    # Deterministic order: all business columns, no source lineage
    data = f"{report_code}|{year_ce}|{zone}|{record_index}|{field_name}|{field_val_str}"
    digest = hashlib.sha256(data.encode()).hexdigest()
    return digest[:16]


def run() -> None:
    read_conn = _connect("bronze")
    write_conn = _connect("silver")

    # Load report name lookup (same as original)
    with read_conn.cursor() as rcur:
        rcur.execute("SELECT raw_report_code, raw_report_name FROM api_hdc_report_catalog")
        report_name_by_code = {code: (name or "").strip() or None for code, name in rcur}

    # Load existing row hashes from Silver (delta detection)
    existing_hashes = set()
    with write_conn.cursor() as wcur:
        wcur.execute("SELECT COALESCE(row_hash, '') FROM api_hdc_observations WHERE row_hash IS NOT NULL")
        for (hash_val,) in wcur:
            existing_hashes.add(hash_val)
    print(f"[silver_api_hdc_incremental] loaded {len(existing_hashes)} existing row hashes from Silver")

    # Read Bronze, compute hashes, filter new rows
    insert_sql = (
        "INSERT INTO api_hdc_observations "
        "(report_code, report_name, year_be, year_ce, zone, record_index, field_name, field_value, row_hash, ingestion_batch_id) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    rows_to_insert = []
    skipped_duplicates = 0

    with read_conn.cursor(pymysql.cursors.SSCursor) as rcur:
        rcur.execute(
            "SELECT raw_report_code, raw_year, raw_zone, raw_record_index, raw_field_name, raw_field_value, ingestion_batch_id "
            "FROM api_hdc_observations"
        )

        total_processed = 0
        total_inserted = 0

        with write_conn.cursor() as wcur:
            for (report_code, year, zone, record_index, field_name, field_value, batch_id) in rcur:
                total_processed += 1

                # Year conversion (Bronze→Silver): Thai Buddhist → CE
                try:
                    year_be = int(year)
                except (TypeError, ValueError):
                    continue
                year_ce = year_be - 543

                # Compute row hash (deterministic, business columns only)
                hash_val = _row_hash(report_code, year_ce, zone, record_index, field_name, field_value)

                # Delta detection: skip if hash already in Silver
                if hash_val in existing_hashes:
                    skipped_duplicates += 1
                    continue

                # New row: prepare for insert and add to in-memory set
                field_value_clean = None if field_value in (None, "") else str(field_value)[:1000]
                rows_to_insert.append((
                    report_code,
                    report_name_by_code.get(report_code),
                    year_be,
                    year_ce,
                    zone,
                    record_index,
                    field_name,
                    field_value_clean,
                    hash_val,
                    batch_id,
                ))

                # Track in local set to avoid duplicates within this batch
                existing_hashes.add(hash_val)

                # Batch insert
                if len(rows_to_insert) >= BATCH_SIZE:
                    wcur.executemany(insert_sql, rows_to_insert)
                    write_conn.commit()
                    total_inserted += len(rows_to_insert)
                    rows_to_insert.clear()

            # Final batch
            if rows_to_insert:
                wcur.executemany(insert_sql, rows_to_insert)
                write_conn.commit()
                total_inserted += len(rows_to_insert)

    read_conn.close()
    write_conn.close()

    print(f"[silver_api_hdc_incremental] processed {total_processed} Bronze rows")
    print(f"[silver_api_hdc_incremental] skipped {skipped_duplicates} existing rows (delta detection)")
    print(f"[silver_api_hdc_incremental] inserted {total_inserted} new/changed rows to Silver")


if __name__ == "__main__":
    run()

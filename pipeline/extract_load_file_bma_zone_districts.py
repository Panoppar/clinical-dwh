"""Loads bronze.bma_zone_districts from the file landed by
ingest_file_bma_zone_districts.py. File-based, single snapshot (static
reference data, no per-year/per-resource split).
"""

import csv
import hashlib
import io
import os
from datetime import datetime, timezone

import pymysql

import landing_store

COLUMNS = ["zone_id", "zone_name_th", "district_name"]


def _connect():
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"], port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"], password=os.environ["DWH_DB_PASSWORD"],
        database="bronze", charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def run() -> None:
    key = landing_store.latest_version("bma_zone_districts", "zone_districts", "csv")
    if key is None:
        print("[extract_load_file_bma_zone_districts] no landed object found, skipping "
              "(run ingest_file_bma_zone_districts first)")
        return

    content = landing_store.read_bytes(key)
    file_hash = hashlib.sha256(content).hexdigest()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    if reader.fieldnames != COLUMNS:
        raise RuntimeError(f"bma_zone_districts CSV header changed for {key}, "
                            f"expected {COLUMNS}, got {reader.fieldnames}")

    loaded_at = datetime.now(timezone.utc)
    batch_id = f"bma_zone_districts_load_{loaded_at:%Y%m%dT%H%M%S}"

    rows = [
        ("bma_zone_districts", key, i, file_hash, batch_id, "BMA_ZONE_DISTRICTS",
         record["zone_id"], record["zone_name_th"], record["district_name"])
        for i, record in enumerate(reader, start=1)
    ]

    insert_sql = (
        "INSERT INTO bma_zone_districts "
        "(source_folder, source_file_name, source_row_number, file_hash, ingestion_batch_id, source_system, "
        "raw_zone_id, raw_zone_name_th, raw_district_name) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    conn = _connect()
    with conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    conn.commit()
    conn.close()
    print(f"[extract_load_file_bma_zone_districts] bma_zone_districts: loaded {len(rows)} rows from {key}")


if __name__ == "__main__":
    run()

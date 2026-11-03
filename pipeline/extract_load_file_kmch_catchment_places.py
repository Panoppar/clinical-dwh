"""Loads bronze.kmch_catchment_places from the file landed by
ingest_file_kmch_catchment_places.py. Straight 1:1 field mapping, no
transformation -- casting and the market_potential tier/detail split
happen in Silver.
"""

import csv
import hashlib
import io
import os
from datetime import datetime, timezone

import pymysql

import landing_store

BATCH_SIZE = 2000
EXPECTED_COLUMNS = [
    "Category", "Place Name (Thai)", "Place Name (English)", "Address",
    "Sub-district", "District", "Province", "Avg Distance (km)",
    "Avg Travel Time (mins)", "Market Potential (ML Target)",
]


def _connect():
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"], port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"], password=os.environ["DWH_DB_PASSWORD"],
        database="bronze", charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def _insert_batch(cur, insert_sql, rows):
    row_count = 0
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) >= BATCH_SIZE:
            cur.executemany(insert_sql, batch)
            row_count += len(batch)
            batch.clear()
    if batch:
        cur.executemany(insert_sql, batch)
        row_count += len(batch)
    return row_count


def run() -> None:
    key = landing_store.latest_version("kmch_catchment_places", "kmch_catchment_places", "csv")
    if key is None:
        print("[extract_load_file_kmch_catchment_places] no landed object found, skipping "
              "(run ingest_file_kmch_catchment_places first)")
        return
    content = landing_store.read_bytes(key)
    file_hash = hashlib.sha256(content).hexdigest()

    loaded_at = datetime.now(timezone.utc)
    batch_id = f"kmch_catchment_places_load_{loaded_at:%Y%m%dT%H%M%S}"

    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != EXPECTED_COLUMNS:
        raise RuntimeError(f"kmch_catchment_places CSV header changed, expected {EXPECTED_COLUMNS}, got {reader.fieldnames}")

    insert_sql = (
        "INSERT INTO kmch_catchment_places "
        "(source_folder, source_file_name, source_row_number, file_hash, ingestion_batch_id, source_system, "
        "raw_category, raw_place_name_th, raw_place_name_en, raw_address, raw_subdistrict, raw_district, "
        "raw_province, raw_avg_distance_km, raw_avg_travel_time_min, raw_market_potential) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    rows = []
    for i, record in enumerate(reader, start=1):
        values = [record[col] for col in EXPECTED_COLUMNS]
        rows.append(("kmch_catchment_places", key, i, file_hash, batch_id, "KMCH_CATCHMENT_PLACES", *values))

    conn = _connect()
    with conn.cursor() as cur:
        n = _insert_batch(cur, insert_sql, rows)
    conn.commit()
    conn.close()
    print(f"[extract_load_file_kmch_catchment_places] kmch_catchment_places: loaded {n} rows from {key}")


if __name__ == "__main__":
    run()

"""Loads bronze.kmch_catchment_places from the single KMCH source CSV."""

import csv
import os
from datetime import datetime, timezone

import pymysql

EXTERNAL_SOURCES_ROOT = "/app/external-sources/kmch_places"
FILENAME = "KMCH_Catchment_Places_Extended_All - ลิตส์เอง.csv"
BATCH_SIZE = 2000


def _connect():
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"],
        port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"],
        password=os.environ["DWH_DB_PASSWORD"],
        database="bronze",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
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
    loaded_at = datetime.now(timezone.utc)
    batch_id = f"kmch_load_{loaded_at:%Y%m%dT%H%M%S}"
    path = os.path.join(EXTERNAL_SOURCES_ROOT, FILENAME)

    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        for i, row in enumerate(reader, start=1):
            if not row or not any(row):
                continue
            row = (row + [None] * 10)[:10]
            rows.append((FILENAME, i, batch_id, None, *row))

    insert_sql = (
        "INSERT INTO kmch_catchment_places "
        "(source_file_name, source_row_number, load_batch_id, file_hash, "
        "raw_category, raw_place_name_th, raw_place_name_en, raw_address, "
        "raw_sub_district, raw_district, raw_province, raw_avg_distance_km, "
        "raw_avg_travel_time_mins, raw_market_potential) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    conn = _connect()
    with conn.cursor() as cur:
        n = _insert_batch(cur, insert_sql, rows)
    conn.commit()
    conn.close()
    print(f"[kmch] kmch_catchment_places: loaded {n} rows")

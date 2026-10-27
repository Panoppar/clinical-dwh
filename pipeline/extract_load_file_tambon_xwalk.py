"""Loads bronze.tambon_xwalk from the tambon_xwalk CSV landed by
ingest_file_tambon_xwalk.py. File-based, single snapshot (no per-year/
per-resource split like the live-API sources) -- always reads the latest
landed version.
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
    "tambon_code", "tambon_th", "tambon_en", "amphoe_code", "postal_code",
    "unit_code", "is_split", "amphoe_th", "province_code",
]


def _connect():
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"], port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"], password=os.environ["DWH_DB_PASSWORD"],
        database="bronze", charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def run() -> None:
    key = landing_store.latest_version("tambon_xwalk", "xwalk_tambon_unit", "csv")
    if key is None:
        print("[extract_load_file_tambon_xwalk] no landed object found, skipping "
              "(run ingest_file_tambon_xwalk first)")
        return

    content = landing_store.read_bytes(key)
    file_hash = hashlib.sha256(content).hexdigest()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    header = reader.fieldnames
    if header != EXPECTED_COLUMNS:
        raise RuntimeError(f"tambon_xwalk CSV header changed for {key}, expected {EXPECTED_COLUMNS}, got {header}")

    loaded_at = datetime.now(timezone.utc)
    batch_id = f"tambon_xwalk_load_{loaded_at:%Y%m%dT%H%M%S}"

    insert_sql = (
        "INSERT INTO tambon_xwalk "
        "(source_folder, source_file_name, source_row_number, file_hash, ingestion_batch_id, source_system, "
        "raw_tambon_code, raw_tambon_th, raw_tambon_en, raw_amphoe_code, raw_postal_code, "
        "raw_unit_code, raw_is_split, raw_amphoe_th, raw_province_code) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    rows = []
    for i, record in enumerate(reader, start=1):
        values = [record[col] for col in header]
        rows.append(("tambon_xwalk", key, i, file_hash, batch_id, "TAMBON_XWALK", *values))

    conn = _connect()
    with conn.cursor() as cur:
        n = 0
        batch = []
        for row in rows:
            batch.append(row)
            if len(batch) >= BATCH_SIZE:
                cur.executemany(insert_sql, batch)
                n += len(batch)
                batch.clear()
        if batch:
            cur.executemany(insert_sql, batch)
            n += len(batch)
    conn.commit()
    conn.close()
    print(f"[extract_load_file_tambon_xwalk] tambon_xwalk: loaded {n} rows from {key}")


if __name__ == "__main__":
    run()

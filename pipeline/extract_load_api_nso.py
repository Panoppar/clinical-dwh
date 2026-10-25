"""Loads bronze.api_nso_income from the latest NSO CSV landed in the
landing zone by ingest_api_nso.py. Reads the object bytes straight into
memory -- never written to this container's own filesystem.
"""

import csv
import hashlib
import io
import os
from datetime import datetime, timezone

import pymysql

import landing_store

NSO_TABLE = "SFD_SPB0802_66"
BATCH_SIZE = 2000
EXPECTED_COLUMNS = [
    "year", "province", "source_income1", "source_income2", "source_income3",
    "soc_eco_class1", "soc_eco_class2", "value", "unit", "attribute", "source",
]


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
    key = landing_store.latest_version("nso", NSO_TABLE, "csv")
    if key is None:
        print("[extract_load_api_nso] no landed NSO object found, skipping (run ingest_api_nso first)")
        return
    content = landing_store.read_bytes(key)
    file_hash = hashlib.sha256(content).hexdigest()

    loaded_at = datetime.now(timezone.utc)
    batch_id = f"api_nso_load_{loaded_at:%Y%m%dT%H%M%S}"

    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    header = [c.lower() for c in reader.fieldnames]
    if header != EXPECTED_COLUMNS:
        raise RuntimeError(f"NSO CSV header changed, expected {EXPECTED_COLUMNS}, got {header}")

    rows = []
    for i, record in enumerate(reader, start=1):
        values = [record[col] for col in reader.fieldnames]
        rows.append(("nso", key, None, i, file_hash, batch_id, "NSO", *values))

    insert_sql = (
        "INSERT INTO api_nso_income "
        "(source_folder, source_file_name, source_sheet_name, source_row_number, "
        "file_hash, ingestion_batch_id, source_system, "
        "raw_year, raw_province, raw_source_income1, raw_source_income2, raw_source_income3, "
        "raw_soc_eco_class1, raw_soc_eco_class2, raw_value, raw_unit, raw_attribute, raw_source) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    conn = _connect()
    with conn.cursor() as cur:
        n = _insert_batch(cur, insert_sql, rows)
    conn.commit()
    conn.close()
    print(f"[extract_load_api_nso] api_nso_income: loaded {n} rows from {key}")


if __name__ == "__main__":
    run()

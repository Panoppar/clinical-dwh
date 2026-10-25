"""Loads bronze.api_bma_community from every BMA fiscal-year CSV landed in
the landing zone by ingest_api_bma.py. Enumerates landed objects directly
(no network call here) -- one resource per fiscal year, grouped by the
CKAN resource id embedded in each object's key.
"""

import csv
import hashlib
import io
import os
import re
from datetime import datetime, timezone

import pymysql

import landing_store

BATCH_SIZE = 2000
EXPECTED_COLUMNS = [
    "fiscal_year", "district", "subdistrict", "name_of_community",
    "type_of_community", "number_of_population", "male", "female",
]
# landing_store keys look like "bma/<stem>__<date>_<hash>.csv"
_KEY_STEM_RE = re.compile(r"^bma/(.+)__\d{8}_[0-9a-f]{8}\.csv$")


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


def _landed_resource_stems() -> list[str]:
    stems = set()
    for key in landing_store.list_prefix("bma"):
        m = _KEY_STEM_RE.match(key)
        if m:
            stems.add(m.group(1))
    return sorted(stems)


def run() -> None:
    stems = _landed_resource_stems()
    if not stems:
        print("[extract_load_api_bma] no landed BMA objects found, skipping (run ingest_api_bma first)")
        return

    loaded_at = datetime.now(timezone.utc)
    batch_id = f"api_bma_load_{loaded_at:%Y%m%dT%H%M%S}"

    insert_sql = (
        "INSERT INTO api_bma_community "
        "(source_folder, source_file_name, source_sheet_name, source_row_number, "
        "file_hash, ingestion_batch_id, source_system, "
        "raw_fiscal_year, raw_district, raw_subdistrict, raw_name_of_community, "
        "raw_type_of_community, raw_number_of_population, raw_male, raw_female) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    conn = _connect()
    total = 0
    for stem in stems:
        key = landing_store.latest_version("bma", stem, "csv")
        content = landing_store.read_bytes(key)
        file_hash = hashlib.sha256(content).hexdigest()

        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        header = reader.fieldnames
        if header != EXPECTED_COLUMNS:
            raise RuntimeError(f"BMA CSV header changed for {key}, expected {EXPECTED_COLUMNS}, got {header}")

        rows = []
        for i, record in enumerate(reader, start=1):
            values = [record[col] for col in header]
            rows.append(("bma", key, None, i, file_hash, batch_id, "BMA", *values))

        with conn.cursor() as cur:
            n = _insert_batch(cur, insert_sql, rows)
        conn.commit()
        total += n
        print(f"[extract_load_api_bma] api_bma_community: loaded {n} rows from {key}")
    conn.close()
    print(f"[extract_load_api_bma] api_bma_community: loaded {total} rows total across {len(stems)} fiscal-year resource(s)")


if __name__ == "__main__":
    run()

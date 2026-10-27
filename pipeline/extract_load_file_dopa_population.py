"""Loads bronze.dopa_population_year and bronze.dopa_population_supplement
from the two DOPA population files landed by ingest_file_dopa_population.py.
File-based, single snapshot each (no per-year/per-resource split) -- always
reads the latest landed version of each.
"""

import csv
import hashlib
import io
import os
from datetime import datetime, timezone

import pymysql

import landing_store

BATCH_SIZE = 2000

YEAR_COLUMNS = [
    "unit_code", "year_be", "ref_month",
    "fine_male_0-4", "fine_female_0-4", "fine_male_5-9", "fine_female_5-9",
    "fine_male_10-14", "fine_female_10-14", "fine_male_15-17", "fine_female_15-17",
    "fine_male_18-22", "fine_female_18-22", "fine_male_23-29", "fine_female_23-29",
    "fine_male_30-39", "fine_female_30-39", "fine_male_40-49", "fine_female_40-49",
    "fine_male_50-59", "fine_female_50-59", "fine_male_60+", "fine_female_60+",
    "coarse_male_0-14", "coarse_female_0-14", "coarse_male_15-59", "coarse_female_15-59",
    "coarse_male_60+", "coarse_female_60+",
    "pop_male", "pop_female", "pop_total", "pop_age_known", "pop_unknown_age", "source_file",
]
SUPPLEMENT_COLUMNS = ["unit_code", "year_be", "pop_total", "source"]


def _connect():
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"], port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"], password=os.environ["DWH_DB_PASSWORD"],
        database="bronze", charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def _insert_batch(cur, insert_sql, rows):
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
    return n


def _load_one(conn, stem, expected_columns, table, batch_id):
    key = landing_store.latest_version("dopa_population", stem, "csv")
    if key is None:
        print(f"[extract_load_file_dopa_population] no landed '{stem}' object found, skipping "
              f"(run ingest_file_dopa_population first)")
        return

    content = landing_store.read_bytes(key)
    file_hash = hashlib.sha256(content).hexdigest()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    header = reader.fieldnames
    if header != expected_columns:
        raise RuntimeError(f"{table} CSV header changed for {key}, expected {expected_columns}, got {header}")

    cols = ["raw_" + c.replace("-", "_").replace("+", "_plus") for c in header]
    insert_sql = (
        f"INSERT INTO {table} (source_folder, source_file_name, source_row_number, "
        f"file_hash, ingestion_batch_id, source_system, {', '.join(cols)}) "
        f"VALUES ({', '.join(['%s'] * (6 + len(cols)))})"
    )

    rows = [
        ("dopa_population", key, i, file_hash, batch_id, "DOPA_POPULATION", *[record[c] for c in header])
        for i, record in enumerate(reader, start=1)
    ]
    with conn.cursor() as cur:
        n = _insert_batch(cur, insert_sql, rows)
    conn.commit()
    print(f"[extract_load_file_dopa_population] {table}: loaded {n} rows from {key}")


def run() -> None:
    loaded_at = datetime.now(timezone.utc)
    batch_id = f"dopa_population_load_{loaded_at:%Y%m%dT%H%M%S}"
    conn = _connect()
    _load_one(conn, "year", YEAR_COLUMNS, "dopa_population_year", batch_id)
    _load_one(conn, "supplement", SUPPLEMENT_COLUMNS, "dopa_population_supplement", batch_id)
    conn.close()


if __name__ == "__main__":
    run()

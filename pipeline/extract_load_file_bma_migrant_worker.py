"""Loads the 4 bronze.bma_migrant_* tables from the file landed by
ingest_file_bma_migrant_worker.py. Fixed row/column positions, not a
single-header DictReader -- the source is a multi-section pivot with its
own header shape per section (see sql/bronze/15's header note), not a
plain tabular CSV. Positions confirmed by direct verification (every
section's grand-total row exactly equals the sum of its 10 zone rows,
every column) before this was written.
"""

import csv
import hashlib
import io
import os
from datetime import datetime, timezone

import pymysql

import landing_store

# (bronze_table, total_row_index, zone_rows_slice, n_data_cols)
SECTIONS = [
    ("bma_migrant_general", 4, slice(5, 15), 18),
    ("bma_migrant_mou_import", 19, slice(20, 30), 12),
    ("bma_migrant_renewal", 34, slice(35, 45), 12),
    ("bma_migrant_illegal", 49, slice(50, 60), 12),
]


def _connect():
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"], port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"], password=os.environ["DWH_DB_PASSWORD"],
        database="bronze", charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def run() -> None:
    key = landing_store.latest_version("bma_migrant_worker", "bma_migrant_worker_2568", "csv")
    if key is None:
        print("[extract_load_file_bma_migrant_worker] no landed object found, skipping "
              "(run ingest_file_bma_migrant_worker first)")
        return

    content = landing_store.read_bytes(key)
    file_hash = hashlib.sha256(content).hexdigest()
    text = content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))

    loaded_at = datetime.now(timezone.utc)
    batch_id = f"bma_migrant_worker_load_{loaded_at:%Y%m%dT%H%M%S}"

    conn = _connect()
    for table, total_idx, zone_slice, n_data_cols in SECTIONS:
        data_cols = ", ".join(f"raw_col{i}" for i in range(n_data_cols))
        # column names in the DDL are semantic (raw_general_total, etc.) --
        # map positionally here instead of hardcoding 18 vs 12 distinct
        # name lists; the actual INSERT lists real column names per table.
        source_rows = [rows[total_idx]] + [rows[i] for i in range(zone_slice.start, zone_slice.stop)]

        with conn.cursor() as cur:
            cur.execute(f"SHOW COLUMNS FROM {table}")
            all_cols = [c[0] for c in cur.fetchall()]
        value_cols = [c for c in all_cols if c.startswith("raw_") and c not in
                      ("raw_zone_label", "raw_zone_districts_or_label")]
        if len(value_cols) != n_data_cols:
            raise RuntimeError(f"{table}: expected {n_data_cols} data columns, found {len(value_cols)}")

        insert_sql = (
            f"INSERT INTO {table} (source_folder, source_file_name, source_row_number, file_hash, "
            f"ingestion_batch_id, source_system, raw_zone_label, raw_zone_districts_or_label, "
            + ", ".join(value_cols) + ") VALUES ("
            + ", ".join(["%s"] * (8 + n_data_cols)) + ")"
        )

        db_rows = []
        for i, raw_row in enumerate(source_rows):
            zone_label = raw_row[0]
            district_or_label = raw_row[1]
            values = raw_row[2:2 + n_data_cols]
            db_rows.append(("bma_migrant_worker", key, i, file_hash, batch_id, "BMA_MIGRANT_WORKER",
                             zone_label, district_or_label, *values))

        with conn.cursor() as cur:
            cur.executemany(insert_sql, db_rows)
        conn.commit()
        print(f"[extract_load_file_bma_migrant_worker] {table}: loaded {len(db_rows)} rows "
              f"(1 grand-total + {len(db_rows) - 1} zones)")
    conn.close()


if __name__ == "__main__":
    run()

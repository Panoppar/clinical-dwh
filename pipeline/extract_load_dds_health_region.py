"""Loads bronze.dds_health_region_disease_report from skr6/skr13 weekly CSVs."""

import csv
import os
import re
from datetime import datetime, timezone

import pymysql

EXTERNAL_SOURCES_ROOT = "/app/external-sources/dds_health_region"
REGIONS = ["skr6", "skr13"]
BATCH_SIZE = 2000

FILENAME_RE = re.compile(r"^(skr\d+)_(\d{4})_(.+)\.csv$")


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


INSERT_SQL = (
    "INSERT INTO dds_health_region_disease_report "
    "(source_folder, health_region_code, source_file_name, report_year, report_period_label, "
    "source_row_number, load_batch_id, raw_no, raw_disease_name_th, raw_patient_count, "
    "raw_morbidity_rate, raw_ipd_count, raw_death_count, raw_case_fatality_rate) "
    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
)


def run() -> None:
    loaded_at = datetime.now(timezone.utc)
    batch_id = f"dds_health_region_load_{loaded_at:%Y%m%dT%H%M%S}"

    conn = _connect()
    total = 0
    with conn.cursor() as cur:
        for region in REGIONS:
            region_dir = os.path.join(EXTERNAL_SOURCES_ROOT, region)
            for filename in sorted(os.listdir(region_dir)):
                m = FILENAME_RE.match(filename)
                if not m:
                    raise ValueError(f"cannot parse {filename!r}")
                _region_from_name, report_year, report_period_label = m.groups()

                path = os.path.join(region_dir, filename)
                with open(path, "r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.reader(f)
                    next(reader, None)  # header
                    rows = []
                    for i, row in enumerate(reader, start=1):
                        if not row or not any(row):
                            continue
                        row = (row + [None] * 7)[:7]
                        rows.append((region, region, filename, report_year, report_period_label,
                                     i, batch_id, *row))
                n = _insert_batch(cur, INSERT_SQL, rows)
                total += n
                print(f"[dds_health_region] loaded {n} rows from {region}/{filename}")
    conn.commit()
    conn.close()
    print(f"[dds_health_region] total rows loaded: {total}")

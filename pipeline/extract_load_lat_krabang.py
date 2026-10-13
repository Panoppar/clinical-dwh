"""
Loads the 9 Lat Krabang district office bronze tables.

Group 06 (community, ข้อมูลชุมชนในพื้นที่เขตลาดกระบัง.csv) is intentionally
NOT loaded -- not even copied into this repo. Its name_head/tel columns
carry a real community leader's name and phone number, with no
de-identified alternative available. bronze.community is created (see
sql/bronze/03_create_bronze_lat_krabang_tables.sql) but stays empty.

Two file shapes:
  - 7 tables: header row only, read by position (DictReader not used
    since a couple of real headers have cosmetic differences from the
    DDL's column names, e.g. "count_community committee" vs
    count_community_committee -- positional reading sidesteps that).
  - 2 tables (population_total, population_death): a title row ABOVE the
    real header row -- skip 2 rows, not 1.
"""

import csv
import os
from datetime import datetime, timezone

import pymysql

EXTERNAL_SOURCES_ROOT = "/app/external-sources/lat_krabang"
BATCH_SIZE = 2000

# (relative_path, table, n_business_cols, skip_rows)
FILES = [
    ("01_การศึกษา/มหาวิทยาลัย/รายชื่อมหาวิทยาลัย_เขตลาดกระบัง.csv", "edu_university", 9, 1),
    ("01_การศึกษา/สถาบันอาชีวศึกษา/รายชื่อวิทยาลัยอาชีวศึกษา_เขตลาดกระบัง.csv", "edu_vocational_college", 9, 1),
    ("01_การศึกษา/โรงเรียน/ข้อมูลโรงเรียนและจำนวนนักเรียน_เขตลาดกระบัง.csv", "edu_school", 13, 1),
    ("02_สาธารณสุข/รายชื่อโรงพยาบาล_เขตลาดกระบัง.csv", "health_hospital", 9, 1),
    ("03_ศาสนา/รายชื่อศาสนสถาน_เขตลาดกระบัง.csv", "religious_site", 9, 1),
    ("04_เศรษฐกิจและธุรกิจ/ข้อมูลสถานประกอบการ_เขตลาดกระบัง.csv", "business_establishment", 10, 1),
    ("05_ความปลอดภัย/ข้อมูลจุดเสี่ยงภัยในพื้นที่_เขตลาดกระบัง.csv", "safety_risk_point", 14, 1),
    ("07_ประชากร/ประชากรทั้งหมด/ข้อมูลจำนวนประชากรแยกตามแขวง_เขตลาดกระบัง.csv", "population_total", 4, 2),
    ("07_ประชากร/การเสียชีวิต/ข้อมูลจำนวนการตายของประชากรแยกตามแขวง_เขตลาดกระบัง.csv", "population_death", 4, 2),
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


def _read_rows(path, n_cols, skip_rows):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for _ in range(skip_rows):
            next(reader, None)
        for row in reader:
            if not row or not any(row):
                continue
            row = (row + [None] * n_cols)[:n_cols]
            yield row


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
    batch_id = f"lat_krabang_load_{loaded_at:%Y%m%dT%H%M%S}"

    conn = _connect()
    with conn.cursor() as cur:
        for rel_path, table, n_cols, skip_rows in FILES:
            path = os.path.join(EXTERNAL_SOURCES_ROOT, rel_path)
            filename = os.path.basename(rel_path)
            # Unnamed INSERT...VALUES needs a value for every column, including
            # _ingested_at -- its DEFAULT CURRENT_TIMESTAMP only applies when a
            # column is omitted from a *named* column list, not here.
            placeholders = ", ".join(["%s"] * (n_cols + 3))
            insert_sql = f"INSERT INTO {table} VALUES ({placeholders})"
            rows = [
                (*row, filename, batch_id, loaded_at)
                for row in _read_rows(path, n_cols, skip_rows)
            ]
            n = _insert_batch(cur, insert_sql, rows)
            print(f"[lat_krabang] {table}: loaded {n} rows")
    conn.commit()
    conn.close()

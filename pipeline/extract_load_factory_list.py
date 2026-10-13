"""
Loads bronze.factory_list from the two Factory_list xlsx workbooks.

Both files share the exact same 32 columns in the exact same order --
confirmed by inspection -- so this reads by position, not by header name,
which sidesteps the two cosmetic header-text differences between permit
years (FID column label, owner-name column label) entirely.
"""

import os
from datetime import datetime, timezone

import openpyxl
import pymysql

EXTERNAL_SOURCES_ROOT = "/app/external-sources/factory_list"
SHEET_NAME = "ทั่วประเทศรวมนิคมฯ"
BATCH_SIZE = 2000

# (filename, permit_year_be)
FILES = [
    ("รายชื่อโรงงานปี 2567 - สำนักงานโรคติดต่อ กทม.xlsx", "2567"),
    ("รายชื่อโรงงานปี 2568 - สำนักงานโรคติดต่อ กทม.xlsx", "2568"),
]

N_RAW_COLS = 32


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
    "INSERT INTO factory_list "
    "(source_file_name, source_sheet_name, source_permit_year_be, source_row_number, "
    "load_batch_id, raw_factory_reg_no, raw_factory_fid, raw_tsic_code, raw_factory_type_code, "
    "raw_factory_type_desc, raw_category, raw_class, raw_permit_year_be, raw_factory_name, "
    "raw_owner_name, raw_business_activity, raw_address_no, raw_moo, raw_soi, raw_road, "
    "raw_sub_district, raw_district, raw_province_code, raw_province, raw_postal_code, raw_phone, "
    "raw_building_value, raw_land_value, raw_machinery_value, raw_working_capital, "
    "raw_total_investment, raw_male_workers, raw_female_workers, raw_total_workers, "
    "raw_total_horsepower, raw_factory_area_sqm, raw_building_area_sqm) "
    "VALUES (" + ",".join(["%s"] * 37) + ")"
)


def run() -> None:
    loaded_at = datetime.now(timezone.utc)
    batch_id = f"factory_list_load_{loaded_at:%Y%m%dT%H%M%S}"

    conn = _connect()
    total = 0
    with conn.cursor() as cur:
        for filename, permit_year_be in FILES:
            path = os.path.join(EXTERNAL_SOURCES_ROOT, filename)
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            ws = wb[SHEET_NAME]
            rows_iter = ws.iter_rows(values_only=True)
            next(rows_iter, None)  # header

            rows = []
            for i, row in enumerate(rows_iter, start=1):
                if row is None or not any(row):
                    continue
                row = (list(row) + [None] * N_RAW_COLS)[:N_RAW_COLS]
                rows.append((filename, SHEET_NAME, permit_year_be, i, batch_id, *row))
            wb.close()

            n = _insert_batch(cur, INSERT_SQL, rows)
            total += n
            print(f"[factory_list] loaded {n} rows from {filename}")
    conn.commit()
    conn.close()
    print(f"[factory_list] total rows loaded: {total}")

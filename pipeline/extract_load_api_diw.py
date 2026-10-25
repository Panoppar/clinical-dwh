"""Loads bronze.api_diw_factory from every DIW amphoe .xls landed in the
landing zone by ingest_api_diw.py. Reads object bytes straight into memory.

PII EXCLUSION: DIW's raw sheet includes operator_name (factory owner's
personal name) and phone number. kmch-ml's own documented rule for this
source is that these stay local and are never added to outputs or printed
-- both are read off the sheet (needed to keep column positions aligned)
but dropped immediately, before any row is built, logged, or inserted.
"""

import hashlib
import os
import re
from datetime import datetime, timezone

import pymysql
import xlrd

import landing_store

BATCH_SIZE = 2000
# Full column layout as DIW actually returns it -- including the two PII
# columns, which must stay in this list (to keep every other column's
# position correct) but are filtered out in _row_values() before any row
# reaches the database.
DIW_FACTORY_COLUMNS = [
    "reg_no", "factory_name", "operator_name", "business_desc",
    "address_no", "moo", "soi", "road", "tambon", "amphoe", "province",
    "postcode", "phone", "factory_type_code", "capital", "workers", "horsepower",
    "tsic", "old_reg_no",
]
_PII_COLUMNS = {"operator_name", "phone"}
_KEPT_COLUMNS = [c for c in DIW_FACTORY_COLUMNS if c not in _PII_COLUMNS]
DIW_FOOTER_MARKER = "ข้อมูลเมื่อวันที่"
_KEY_STEM_RE = re.compile(r"^diw/(.+)__\d{8}_[0-9a-f]{8}\.xls$")


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


def _landed_stems() -> list[str]:
    stems = set()
    for key in landing_store.list_prefix("diw"):
        m = _KEY_STEM_RE.match(key)
        if m:
            stems.add(m.group(1))
    return sorted(stems)


def _clean_cell(v) -> str:
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = str(v)
    s = s.replace("\xa0", " ")
    return " ".join(s.split())


def _parse_amphoe_xls(raw_xls: bytes) -> list[dict[str, str]]:
    wb = xlrd.open_workbook(file_contents=raw_xls, encoding_override="cp874")
    sh = wb.sheet_by_index(0)
    if sh.nrows < 1:
        return []
    header = [str(c).strip() for c in sh.row_values(0)]
    if len(header) != len(DIW_FACTORY_COLUMNS):
        raise RuntimeError(f"DIW: column count changed ({len(header)} != {len(DIW_FACTORY_COLUMNS)})")
    records = []
    for r in range(1, sh.nrows):
        vals = sh.row_values(r)
        first = vals[0]
        if isinstance(first, str) and first.strip() == DIW_FOOTER_MARKER:
            continue
        if not str(first).strip():
            continue
        full = {col: _clean_cell(v) for col, v in zip(DIW_FACTORY_COLUMNS, vals)}
        records.append({col: full[col] for col in _KEPT_COLUMNS})
    return records


def run() -> None:
    stems = _landed_stems()
    if not stems:
        print("[extract_load_api_diw] no landed DIW objects found, skipping (run ingest_api_diw first)")
        return

    loaded_at = datetime.now(timezone.utc)
    batch_id = f"api_diw_load_{loaded_at:%Y%m%dT%H%M%S}"

    insert_sql = (
        "INSERT INTO api_diw_factory "
        "(source_folder, source_file_name, source_sheet_name, source_row_number, "
        "file_hash, ingestion_batch_id, source_system, "
        "raw_reg_no, raw_factory_name, raw_business_desc, raw_address_no, raw_moo, "
        "raw_soi, raw_road, raw_tambon, raw_amphoe, raw_province, raw_postcode, "
        "raw_factory_type_code, raw_capital, raw_workers, raw_horsepower, raw_tsic, raw_old_reg_no) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    conn = _connect()
    total = 0
    for stem in stems:
        key = landing_store.latest_version("diw", stem, "xls")
        content = landing_store.read_bytes(key)
        file_hash = hashlib.sha256(content).hexdigest()

        records = _parse_amphoe_xls(content)
        rows = []
        for i, rec in enumerate(records, start=1):
            values = [rec[col] for col in _KEPT_COLUMNS]
            rows.append(("diw", key, None, i, file_hash, batch_id, "DIW", *values))

        with conn.cursor() as cur:
            n = _insert_batch(cur, insert_sql, rows)
        conn.commit()
        total += n
        print(f"[extract_load_api_diw] api_diw_factory: loaded {n} rows from {key}")
    conn.close()
    print(f"[extract_load_api_diw] api_diw_factory: loaded {total} rows total across {len(stems)} amphoe object(s)")


if __name__ == "__main__":
    run()

"""Loads bronze.api_dds_disease_ranking from every DDS province PDF landed
in the landing zone by ingest_api_dds.py. Extracts Table 1 (page varies by
province -- more disease categories push it to a later page in Bangkok's
PDF than Samut Prakan's) with pdfplumber, searching every page for the
table whose header starts with "ที่"/"โรค".

Adapted from kmch-ml's dds_parse_table1() (Paiiyahh/kmch-ml, private repo).
"""

import hashlib
import io
import os
import re
from datetime import datetime, timezone

import pdfplumber
import pymysql

import landing_store

BATCH_SIZE = 2000
_KEY_STEM_RE = re.compile(r"^dds/(\d{4})_(\d+)__\d{8}_[0-9a-f]{8}\.pdf$")


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


def _landed_year_province_stems() -> list[tuple[str, str, str]]:
    """-> list of (year, province_code, stem) for every landed DDS PDF."""
    out = []
    for key in landing_store.list_prefix("dds"):
        m = _KEY_STEM_RE.match(key)
        if m:
            year, province_code = m.group(1), m.group(2)
            out.append((year, province_code, f"{year}_{province_code}"))
    return sorted(set(out))


def _parse_table1(pdf_bytes: bytes) -> list[list[str]]:
    table = None
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for t in page.extract_tables():
                if t and t[0] and t[0][0] == "ที่" and t[0][1] == "โรค":
                    table = t
                    break
            if table:
                break
    if not table:
        raise RuntimeError("DDS: Table 1 (header 'ที่'/'โรค') not found on any page -- PDF layout may have changed")
    return table[1:]


def run() -> None:
    stems = _landed_year_province_stems()
    if not stems:
        print("[extract_load_api_dds] no landed DDS objects found, skipping (run ingest_api_dds first)")
        return

    loaded_at = datetime.now(timezone.utc)
    batch_id = f"api_dds_load_{loaded_at:%Y%m%dT%H%M%S}"

    insert_sql = (
        "INSERT INTO api_dds_disease_ranking "
        "(source_folder, source_file_name, source_sheet_name, source_row_number, "
        "file_hash, ingestion_batch_id, source_system, "
        "raw_year, raw_province_code, raw_rank, raw_disease_name, raw_case_count, "
        "raw_rate_per_100k, raw_ipd_count, raw_death_count, raw_case_fatality_pct) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    conn = _connect()
    total = 0
    for year, province_code, stem in stems:
        key = landing_store.latest_version("dds", stem, "pdf")
        content = landing_store.read_bytes(key)
        file_hash = hashlib.sha256(content).hexdigest()

        table_rows = _parse_table1(content)
        rows = []
        for i, r in enumerate(table_rows, start=1):
            if len(r) < 7 or not r[0]:
                continue
            rank, disease_name, case_count, rate_per_100k, ipd_count, death_count, case_fatality_pct = r[:7]
            rows.append((
                "dds", key, None, i, file_hash, batch_id, "DDS",
                year, province_code, rank, disease_name, case_count,
                rate_per_100k, ipd_count, death_count, case_fatality_pct,
            ))

        with conn.cursor() as cur:
            n = _insert_batch(cur, insert_sql, rows)
        conn.commit()
        total += n
        print(f"[extract_load_api_dds] api_dds_disease_ranking: loaded {n} rows from {key}")
    conn.close()
    print(f"[extract_load_api_dds] api_dds_disease_ranking: loaded {total} rows total across {len(stems)} province-year PDF(s)")


if __name__ == "__main__":
    run()

"""Loads bronze.dds_health_region_disease_report from every skr6/skr13 PDF
landed in the landing zone by ingest_file_dds_health_region.py. Parses the
PDF directly with pdfplumber -- confirmed by direct inspection of all 10
files that each PDF's ranking table is always exactly one table, always on
the LAST page, always 21 rows (1 header + 20 ranked diseases), always the
same 7-column header (ที่/โรค/ผู้ป่วย/อัตราป่วย/ผู้ป่วยใน(IPD)/ผู้เสียชีวิต/
อัตราป่วยตาย) regardless of total page count (4 or 5 pages, varying by
report). The narrative pages before it (trend summary text + embedded
chart images) carry no extractable tables and are not used.
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
EXPECTED_HEADER_PREFIX = ["ที่", "โรค"]  # tolerate the \n-wrapped measure-column headers varying slightly
# landing_store keys look like "dds_health_region/<stem>__<date>_<hash>.pdf"
_KEY_STEM_RE = re.compile(r"^dds_health_region/(.+)__\d{8}_[0-9a-f]{8}\.pdf$")
_FILENAME_RE = re.compile(r"^(skr\d+)_(\d{4})_(.+)$")


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
    for key in landing_store.list_prefix("dds_health_region"):
        m = _KEY_STEM_RE.match(key)
        if m:
            stems.add(m.group(1))
    return sorted(stems)


def _parse_table(content: bytes, stem: str) -> list[list[str]]:
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        tables = pdf.pages[-1].extract_tables()
        if not tables:
            raise RuntimeError(f"DDS health region: no table found on last page of {stem}")
        table = tables[0]
    header = table[0]
    if header[:2] != EXPECTED_HEADER_PREFIX:
        raise RuntimeError(f"DDS health region: unexpected table header for {stem}, got {header}")
    data_rows = table[1:]
    if len(data_rows) != 20:
        raise RuntimeError(f"DDS health region: expected 20 ranked disease rows for {stem}, got {len(data_rows)}")
    return data_rows


def run() -> None:
    stems = _landed_stems()
    if not stems:
        print("[extract_load_file_dds_health_region] no landed DDS health-region PDFs found, skipping "
              "(run ingest_file_dds_health_region first)")
        return

    loaded_at = datetime.now(timezone.utc)
    batch_id = f"dds_health_region_load_{loaded_at:%Y%m%dT%H%M%S}"

    insert_sql = (
        "INSERT INTO dds_health_region_disease_report "
        "(source_folder, source_file_name, source_row_number, file_hash, ingestion_batch_id, source_system, "
        "health_region_code, report_year, report_period_label, "
        "raw_no, raw_disease_name_th, raw_patient_count, raw_morbidity_rate, raw_ipd_count, "
        "raw_death_count, raw_case_fatality_rate) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    conn = _connect()
    total = 0
    for stem in stems:
        m = _FILENAME_RE.match(stem)
        if not m:
            raise RuntimeError(f"DDS health region: cannot parse filename stem {stem!r}")
        health_region_code, report_year, report_period_label = m.groups()

        key = landing_store.latest_version("dds_health_region", stem, "pdf")
        content = landing_store.read_bytes(key)
        file_hash = hashlib.sha256(content).hexdigest()

        data_rows = _parse_table(content, stem)
        rows = []
        for i, row in enumerate(data_rows, start=1):
            values = [v.strip() if v else v for v in row]
            rows.append((
                "dds_health_region", key, i, file_hash, batch_id, "DDS_HEALTH_REGION",
                health_region_code, report_year, report_period_label, *values
            ))

        with conn.cursor() as cur:
            n = _insert_batch(cur, insert_sql, rows)
        conn.commit()
        total += n
        print(f"[extract_load_file_dds_health_region] {stem}: loaded {n} rows from {key}")
    conn.close()
    print(f"[extract_load_file_dds_health_region] dds_health_region_disease_report: "
          f"loaded {total} rows total across {len(stems)} report(s)")


if __name__ == "__main__":
    run()

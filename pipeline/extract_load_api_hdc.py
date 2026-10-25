"""Loads bronze.api_hdc_report_catalog and bronze.api_hdc_observations from
every object ingest_api_hdc.py landed in the landing zone. Generic EAV
shred of the data responses (one row per report/year/zone/record/field) --
see sql/bronze/10_create_bronze_api_sources.sql for why: live HDC reports
vary in column layout per report, so Bronze keeps everything rather than
picking a fixed schema per report.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone

import pymysql

import landing_store

BATCH_SIZE = 2000
_CATALOG_KEY_RE = re.compile(r"^hdc/catalog_(.+)__\d{8}_[0-9a-f]{8}\.json$")
_INFO_KEY_RE = re.compile(r"^hdc/info_(.+)__\d{8}_[0-9a-f]{8}\.json$")
_DATA_KEY_RE = re.compile(r"^hdc/data_(.+)_(\d+)_(\d+)__\d{8}_[0-9a-f]{8}\.json$")


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


def _latest_by_stem(prefix: str, pattern: re.Pattern, ext: str) -> dict[str, str]:
    """-> {stem: landing-zone key}, newest version per stem."""
    stems = set()
    for key in landing_store.list_prefix(prefix):
        m = pattern.match(key)
        if m:
            stems.add(m.group(0).rsplit("__", 1)[0].split("/", 1)[1])
    out = {}
    for stem in stems:
        key = landing_store.latest_version(prefix, stem, ext)
        if key:
            out[stem] = key
    return out


def _load_report_catalog(conn) -> dict[str, dict]:
    """Builds the report_code -> {subcatalog_id, subcatalog_name, catalog_label} map from
    landed catalog_*.json objects, and returns it (also used by _load_observations to
    attribute report names, after merging in per-report info)."""
    catalog_stems = _latest_by_stem("hdc", _CATALOG_KEY_RE, "json")
    report_meta: dict[str, dict] = {}

    def expand(nodes, subcat_id, subcat_name):
        for node in nodes:
            children = node.get("children") or []
            if children:
                expand(children, subcat_id, subcat_name)
                continue
            code = node.get("report_code")
            if code:
                report_meta[code] = {"subcatalog_id": subcat_id, "subcatalog_name": subcat_name, "catalog_label": node.get("label", "")}

    for stem, key in catalog_stems.items():
        subcat_id = stem.removeprefix("catalog_")
        body = json.loads(landing_store.read_bytes(key))
        rows = body.get("rows")
        raw_reports = (rows[0].get("reports") if isinstance(rows, list) and rows else []) or []
        subcat_name = rows[0].get("subcatalog_name", "") if isinstance(rows, list) and rows else ""
        expand(raw_reports, subcat_id, subcat_name)
    return report_meta


def _run_report_catalog(conn, report_meta: dict[str, dict]) -> int:
    info_stems = _latest_by_stem("hdc", _INFO_KEY_RE, "json")
    if not info_stems:
        return 0

    loaded_at = datetime.now(timezone.utc)
    batch_id = f"api_hdc_catalog_load_{loaded_at:%Y%m%dT%H%M%S}"
    insert_sql = (
        "INSERT INTO api_hdc_report_catalog "
        "(source_folder, source_file_name, source_sheet_name, source_row_number, "
        "file_hash, ingestion_batch_id, source_system, "
        "raw_report_code, raw_report_name, raw_subcatalog_id, raw_subcatalog_name, "
        "raw_catalog_label, raw_active, raw_byear_list) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    rows = []
    for stem, key in info_stems.items():
        report_code = stem.removeprefix("info_")
        content = landing_store.read_bytes(key)
        file_hash = hashlib.sha256(content).hexdigest()
        body = json.loads(content)
        info_rows = body.get("rows") or {}
        if isinstance(info_rows, list):
            info_rows = info_rows[0] if info_rows else {}
        active = body.get("ok") is not False and bool(info_rows.get("byear_list"))
        years = sorted({str(y) for y in (info_rows.get("byear_list") or [])})
        meta = report_meta.get(report_code, {})
        rows.append((
            "hdc", key, None, 1, file_hash, batch_id, "HDC",
            report_code, (info_rows.get("report_name") or "").strip(),
            meta.get("subcatalog_id"), meta.get("subcatalog_name"), meta.get("catalog_label"),
            "1" if active else "0", ",".join(years),
        ))

    with conn.cursor() as cur:
        n = _insert_batch(cur, insert_sql, rows)
    conn.commit()
    return n


def _run_observations(conn) -> int:
    data_stems: dict[str, tuple[str, str, str, str]] = {}  # stem -> (report_code, year, zone, key)
    for key in landing_store.list_prefix("hdc"):
        m = _DATA_KEY_RE.match(key)
        if m:
            report_code, year, zone = m.group(1), m.group(2), m.group(3)
            stem = f"data_{report_code}_{year}_{zone}"
            data_stems[stem] = (report_code, year, zone, key)
    # keep only the latest key per stem
    latest_keys = _latest_by_stem("hdc", _DATA_KEY_RE, "json")
    resolved = {stem: (report_code, year, zone, latest_keys[stem]) for stem, (report_code, year, zone, _) in data_stems.items() if stem in latest_keys}

    if not resolved:
        return 0

    loaded_at = datetime.now(timezone.utc)
    batch_id = f"api_hdc_obs_load_{loaded_at:%Y%m%dT%H%M%S}"
    insert_sql = (
        "INSERT INTO api_hdc_observations "
        "(source_folder, source_file_name, source_sheet_name, source_row_number, "
        "file_hash, ingestion_batch_id, source_system, "
        "raw_report_code, raw_year, raw_zone, raw_record_index, raw_field_name, raw_field_value) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    conn_cur_total = 0
    for stem, (report_code, year, zone, key) in resolved.items():
        content = landing_store.read_bytes(key)
        file_hash = hashlib.sha256(content).hexdigest()
        body = json.loads(content)
        body_rows = body.get("rows") or []
        data = (body_rows[0].get("data") if body_rows else None) or []
        if not data:
            continue

        rows = []
        for record_index, record in enumerate(data):
            if not isinstance(record, dict):
                continue
            for field_name, field_value in record.items():
                rows.append((
                    "hdc", key, None, record_index, file_hash, batch_id, "HDC",
                    report_code, year, zone, record_index, field_name,
                    None if field_value is None else str(field_value),
                ))
        if not rows:
            continue
        with conn.cursor() as cur:
            n = _insert_batch(cur, insert_sql, rows)
        conn.commit()
        conn_cur_total += n
    return conn_cur_total


def run() -> None:
    conn = _connect()
    try:
        report_meta = _load_report_catalog(conn)
        n_catalog = _run_report_catalog(conn, report_meta)
        print(f"[extract_load_api_hdc] api_hdc_report_catalog: loaded {n_catalog} rows")
        n_obs = _run_observations(conn)
        print(f"[extract_load_api_hdc] api_hdc_observations: loaded {n_obs} rows")
    finally:
        conn.close()


if __name__ == "__main__":
    run()

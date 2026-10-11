"""
Loads Phase 2 shared-drive data into Bronze: HDC/DDS health surveillance
(groups 1, 2, 9, 10 — usage-rights-restricted, loaded on explicit
instruction from the project owner, see docs/03_external_reference_sources.md),
Lat Krabang district office tables (group 7, unrestricted), KMCH catchment
places and other health/population tables (groups 8, 6, unrestricted).

Group 3 is intentionally skipped (the source README states it duplicates
group 2's API-pulled data). The Lat Krabang communities file is intentionally
skipped (contains a community leader's name and phone number — real PII).
"""

import csv
import io
import json
import os
import re
import sys
from datetime import datetime, timezone

import pymysql

SOURCE_SYSTEM_NAME = "shared_drive_phase2"
EXTERNAL_SOURCES_ROOT = "/app/external-sources"
BATCH_SIZE = 2000


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


def _read_csv_rows(path, skip_rows=1):
    with open(path, "r", encoding="utf-8-sig") as f:
        raw = f.read()
    cleaned = raw.replace("\r\n", "\n").replace("\r", "\n")
    reader = csv.reader(io.StringIO(cleaned))
    for _ in range(skip_rows):
        next(reader, None)
    for row in reader:
        if row and any(row):
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


# ---------------------------------------------------------------------------
# Group 2: HDC by-age/disease CSVs (19 files, 3 shapes by filename suffix)
# ---------------------------------------------------------------------------
# n_cols = exact raw CSV column count for that shape (province_code .. ip),
# counted directly from each file's header row.
HDC_SHAPES = {
    "_pop_age": ("hdc_disease_pop_age", 19),
    "_incidence": ("hdc_disease_incidence", 23),
    "_death_age": ("hdc_disease_death_age", 19),
}


def load_hdc_by_age(conn, loaded_at) -> int:
    folder = os.path.join(EXTERNAL_SOURCES_ROOT, "hdc_by_age")
    total = 0
    with conn.cursor() as cur:
        for filename in sorted(os.listdir(folder)):
            if not filename.endswith(".csv"):
                continue
            for suffix, (table, n_cols) in HDC_SHAPES.items():
                if filename.endswith(suffix + ".csv"):
                    disease = filename[len("s_"):-len(suffix + ".csv")] if filename.startswith("s_") else filename[:-len(suffix + ".csv")]
                    placeholders = ", ".join(["%s"] * (n_cols + 4))
                    insert_sql = f"INSERT INTO {table} VALUES ({placeholders})"
                    rows = []
                    for row in _read_csv_rows(os.path.join(folder, filename), skip_rows=1):
                        row = (row + [None] * n_cols)[:n_cols]
                        rows.append((disease, *row, loaded_at, SOURCE_SYSTEM_NAME, filename))
                    total += _insert_batch(cur, insert_sql, rows)
                    break
    conn.commit()
    return total


# ---------------------------------------------------------------------------
# Group 10: DDS extracted-from-PDF CSVs (2 files, fixed known shapes)
# ---------------------------------------------------------------------------
def load_dds_extracted(conn, loaded_at) -> dict:
    folder = os.path.join(EXTERNAL_SOURCES_ROOT, "dds_extracted")
    counts = {}
    with conn.cursor() as cur:
        insert_sql = (
            "INSERT INTO dds_yearly_disease_ranking VALUES ("
            + ",".join(["%s"] * 26) + ")"
        )
        rows = []
        for row in _read_csv_rows(os.path.join(folder, "track_e_dds_yearly.csv"), skip_rows=1):
            row = (row + [None] * 23)[:23]
            rows.append((*row, loaded_at, SOURCE_SYSTEM_NAME, "track_e_dds_yearly.csv"))
        counts["dds_yearly_disease_ranking"] = _insert_batch(cur, insert_sql, rows)

        insert_sql = "INSERT INTO dds_unit_indicator_snapshot VALUES (" + ",".join(["%s"] * 9) + ")"
        rows = []
        for row in _read_csv_rows(os.path.join(folder, "dds_snapshot_history.csv"), skip_rows=1):
            row = (row + [None] * 6)[:6]
            rows.append((*row, loaded_at, SOURCE_SYSTEM_NAME, "dds_snapshot_history.csv"))
        counts["dds_unit_indicator_snapshot"] = _insert_batch(cur, insert_sql, rows)
    conn.commit()
    return counts


# ---------------------------------------------------------------------------
# Group 9: HDC occupational-health JSON API-response cache (330 files)
# ---------------------------------------------------------------------------
_PERIOD_RE = re.compile(r"^([0-9a-f]{32})__(.+)\.json$")


def load_hdc_occupational(conn, loaded_at) -> int:
    folder = os.path.join(EXTERNAL_SOURCES_ROOT, "hdc_occupational")
    insert_sql = (
        "INSERT INTO hdc_occupational_health "
        "(source_hash, period, fetched_at, occupation, target, result, "
        "_bronze_loaded_at, _source_system, _source_file) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    total = 0
    with conn.cursor() as cur:
        for filename in sorted(os.listdir(folder)):
            if not filename.endswith(".json"):
                continue
            m = _PERIOD_RE.match(filename)
            source_hash, period = (m.group(1), m.group(2)) if m else (None, None)
            with open(os.path.join(folder, filename), "r", encoding="utf-8") as f:
                try:
                    doc = json.load(f)
                except json.JSONDecodeError:
                    continue
            fetched_at = doc.get("fetched_at")
            batch = []
            for row_group in doc.get("body", {}).get("rows", []):
                for item in row_group.get("data", []):
                    batch.append((
                        source_hash, period, fetched_at,
                        item.get("occupation"), item.get("target"), item.get("result"),
                        loaded_at, SOURCE_SYSTEM_NAME, filename,
                    ))
            total += _insert_batch(cur, insert_sql, batch)
    conn.commit()
    return total


# ---------------------------------------------------------------------------
# Group 1 + 9: DDS PDF report inventory (lineage only, no content extraction)
# ---------------------------------------------------------------------------
def load_dds_pdf_inventory(conn, loaded_at) -> int:
    path = os.path.join(EXTERNAL_SOURCES_ROOT, "dds_pdf_inventory", "pdf_inventory.csv")
    insert_sql = (
        "INSERT INTO dds_pdf_report_inventory "
        "(filename, size_bytes, sha256, source_group, _bronze_loaded_at, _source_system) "
        "VALUES (%s,%s,%s,%s,%s,%s)"
    )
    with conn.cursor() as cur:
        rows = [
            (row[0], row[1], row[2], row[3], loaded_at, SOURCE_SYSTEM_NAME)
            for row in _read_csv_rows(path, skip_rows=1)
        ]
        n = _insert_batch(cur, insert_sql, rows)
    conn.commit()
    return n


# ---------------------------------------------------------------------------
# Group 7: Lat Krabang district office tables (9 files; communities file
# with PII is deliberately not in this list)
# ---------------------------------------------------------------------------
LAT_KRABANG_FILES = [
    # (filename, table, skip_rows, n_cols)
    ("population_by_subdistrict.csv", "lat_krabang_population_by_subdistrict", 2, 4),
    ("deaths_by_subdistrict.csv", "lat_krabang_deaths_by_subdistrict", 2, 4),
    ("universities.csv", "lat_krabang_universities", 1, 9),
    ("vocational_colleges.csv", "lat_krabang_vocational_colleges", 1, 9),
    ("schools.csv", "lat_krabang_schools", 1, 13),
    ("risk_points.csv", "lat_krabang_risk_points", 1, 14),
    ("religious_sites.csv", "lat_krabang_religious_sites", 1, 9),
    ("businesses.csv", "lat_krabang_businesses", 1, 10),
    ("hospitals.csv", "lat_krabang_hospitals", 1, 9),
]


def load_lat_krabang(conn, loaded_at) -> dict:
    folder = os.path.join(EXTERNAL_SOURCES_ROOT, "lat_krabang")
    counts = {}
    with conn.cursor() as cur:
        for filename, table, skip_rows, n_cols in LAT_KRABANG_FILES:
            placeholders = ", ".join(["%s"] * (n_cols + 2))
            insert_sql = f"INSERT INTO {table} VALUES ({placeholders})"
            rows = []
            for row in _read_csv_rows(os.path.join(folder, filename), skip_rows=skip_rows):
                row = (row + [None] * n_cols)[:n_cols]
                rows.append((*row, loaded_at, SOURCE_SYSTEM_NAME))
            counts[table] = _insert_batch(cur, insert_sql, rows)
    conn.commit()
    return counts


# ---------------------------------------------------------------------------
# Group 8: KMCH catchment places (4 files, 2 shapes unified to one table)
# ---------------------------------------------------------------------------
KMCH_FILES = {
    "KMCH_Catchment_Places.csv": "basic",
    "KMCH_Catchment_Places_Master_1000.csv": "basic_market",
    "KMCH_Catchment_Places_Extended_All - ลิตส์เอง.csv": "extended",
    "KMCH_Catchment_Places_Extended_SamutPrakan.csv": "extended",
}


def load_kmch_places(conn, loaded_at) -> int:
    folder = os.path.join(EXTERNAL_SOURCES_ROOT, "kmch_places")
    insert_sql = (
        "INSERT INTO kmch_catchment_places "
        "(category, place_name_th, place_name_en, address_th, subdistrict_th, district_th, "
        "province_th, avg_distance_km, avg_travel_time_mins, market_potential, "
        "_bronze_loaded_at, _source_system, _source_file) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    total = 0
    with conn.cursor() as cur:
        for filename, shape in KMCH_FILES.items():
            path = os.path.join(folder, filename)
            if not os.path.exists(path):
                continue
            rows = []
            for row in _read_csv_rows(path, skip_rows=1):
                if shape == "basic":
                    cat, th, en, dist, mins = (row + [None] * 5)[:5]
                    rows.append((cat, th, en, None, None, None, None, dist, mins, None, loaded_at, SOURCE_SYSTEM_NAME, filename))
                elif shape == "basic_market":
                    cat, th, en, dist, mins, market = (row + [None] * 6)[:6]
                    rows.append((cat, th, en, None, None, None, None, dist, mins, market, loaded_at, SOURCE_SYSTEM_NAME, filename))
                else:  # extended
                    cat, th, en, addr, subd, dist_, prov, km, mins, market = (row + [None] * 10)[:10]
                    rows.append((cat, th, en, addr, subd, dist_, prov, km, mins, market, loaded_at, SOURCE_SYSTEM_NAME, filename))
            total += _insert_batch(cur, insert_sql, rows)
    conn.commit()
    return total


# ---------------------------------------------------------------------------
# Group 6: other health & population tables (4 clean CSVs, distinct shapes)
# ---------------------------------------------------------------------------
def load_other_health(conn, loaded_at) -> dict:
    folder = os.path.join(EXTERNAL_SOURCES_ROOT, "other_health")
    counts = {}
    with conn.cursor() as cur:
        insert_sql = "INSERT INTO other_health_disease_cases VALUES (%s,%s,%s,%s,%s,%s)"
        rows = [(*row[:4], loaded_at, SOURCE_SYSTEM_NAME) for row in _read_csv_rows(os.path.join(folder, "disease_cases.csv"), 1)]
        counts["other_health_disease_cases"] = _insert_batch(cur, insert_sql, rows)

        insert_sql = "INSERT INTO other_health_subdistrict_cases VALUES (%s,%s,%s,%s,%s,%s,%s)"
        rows = [(*row[:5], loaded_at, SOURCE_SYSTEM_NAME) for row in _read_csv_rows(os.path.join(folder, "subdistrict_cases.csv"), 1)]
        counts["other_health_subdistrict_cases"] = _insert_batch(cur, insert_sql, rows)

        insert_sql = "INSERT INTO other_health_sick_by_group VALUES (%s,%s,%s,%s,%s,%s,%s)"
        rows = [(*row[:5], loaded_at, SOURCE_SYSTEM_NAME) for row in _read_csv_rows(os.path.join(folder, "sick1-10.csv"), 1)]
        counts["other_health_sick_by_group"] = _insert_batch(cur, insert_sql, rows)

        insert_sql = "INSERT INTO other_health_disease_by_year VALUES (%s,%s,%s,%s,%s)"
        rows = [(*row[:3], loaded_at, SOURCE_SYSTEM_NAME) for row in _read_csv_rows(os.path.join(folder, "2567.csv"), 1)]
        counts["other_health_disease_by_year"] = _insert_batch(cur, insert_sql, rows)
    conn.commit()
    return counts


def run() -> None:
    conn = _connect()
    loaded_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        n = load_hdc_by_age(conn, loaded_at)
        print(f"[bronze] hdc_disease_* (19 files): {n} rows loaded")

        counts = load_dds_extracted(conn, loaded_at)
        for table, n in counts.items():
            print(f"[bronze] {table}: {n} rows loaded")

        n = load_hdc_occupational(conn, loaded_at)
        print(f"[bronze] hdc_occupational_health (330 files): {n} rows loaded")

        n = load_dds_pdf_inventory(conn, loaded_at)
        print(f"[bronze] dds_pdf_report_inventory: {n} rows loaded")

        counts = load_lat_krabang(conn, loaded_at)
        for table, n in counts.items():
            print(f"[bronze] {table}: {n} rows loaded")

        n = load_kmch_places(conn, loaded_at)
        print(f"[bronze] kmch_catchment_places: {n} rows loaded")

        counts = load_other_health(conn, loaded_at)
        for table, n in counts.items():
            print(f"[bronze] {table}: {n} rows loaded")
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        print(f"[bronze] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

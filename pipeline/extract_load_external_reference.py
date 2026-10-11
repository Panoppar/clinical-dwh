"""
Loads external population-reference flat files (DOPA, NSO) into Bronze.

Unlike extract_load_bronze.py, there is no "source database" here — these
are government open-data flat files checked into external-sources/ and
bind-mounted into this container (see docker-compose.yml). Assumes
sql/bronze/02_create_bronze_external_reference_tables.sql has already
(re)created empty tables in this run.

Scope and provenance: see docs/03_external_reference_sources.md.
"""

import csv
import io
import os
import sys
from datetime import datetime, timezone

import pymysql
import pymysql.cursors

SOURCE_SYSTEM_NAME = "external_reference"
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


def load_dopa_population_monthly(conn, loaded_at: str) -> int:
    path = os.path.join(EXTERNAL_SOURCES_ROOT, "dopa", "stat_t.txt")
    insert_sql = (
        "INSERT INTO dopa_population_monthly ("
        "yymm, province_code, province_name, regoffice_code, regoffice_name, "
        "subdistrict_code, subdistrict_name, village_code, village_name, "
        "male_raw, female_raw, total_raw, house_raw, "
        "_bronze_loaded_at, _source_system, _source_file"
        ") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    row_count = 0
    batch = []
    with open(path, "r", encoding="utf-8") as f, conn.cursor() as cur:
        next(f)  # skip header
        for line in f:
            fields = line.rstrip("\n").rstrip("\r").split("|")
            if fields and fields[-1] == "":
                fields = fields[:-1]  # trailing pipe produces an empty final field
            if len(fields) != 13:
                continue  # skip malformed lines rather than failing the whole load
            batch.append((*fields, loaded_at, SOURCE_SYSTEM_NAME, "stat_t.txt"))
            if len(batch) >= BATCH_SIZE:
                cur.executemany(insert_sql, batch)
                row_count += len(batch)
                batch.clear()
        if batch:
            cur.executemany(insert_sql, batch)
            row_count += len(batch)
    conn.commit()
    return row_count


def load_nso_population_registration(conn, loaded_at: str, filename: str) -> int:
    path = os.path.join(EXTERNAL_SOURCES_ROOT, "nso", filename)
    insert_sql = (
        "INSERT INTO nso_population_registration ("
        "dataflow, pop_subj, pop_ind, sex_code, age_code, cwt_code, amphoe_code, "
        "tambon_code, unit, freq, time_period, obs_value, source_th, note, obs_value_alt, "
        "_bronze_loaded_at, _source_system, _source_file"
        ") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    # Some of these government exports carry corrupted "\r\r\n" line endings
    # (verified via hexdump on reg_age_2567.csv). Opened with newline='' (as
    # recommended for the csv module), that stray extra \r is interpreted by
    # csv.reader as its own row terminator, producing a spurious all-NULL row
    # after every real one. Normalize to \n before handing off to csv.reader
    # rather than trusting the file's own line endings.
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    cleaned = raw.replace("\r\n", "\n").replace("\r", "\n")

    row_count = 0
    batch = []
    with conn.cursor() as cur:
        reader = csv.reader(io.StringIO(cleaned))
        next(reader)  # skip header
        for row in reader:
            if not row or not any(row):
                continue  # skip any remaining blank/all-empty rows defensively
            # reg_age_2567.csv has 14 columns, reg_prov_2567.csv has 15 (extra
            # trailing "v" alt-value column) — pad to a consistent 15 so both
            # files land in the same table shape.
            row = row + [None] * (15 - len(row))
            batch.append((*row[:15], loaded_at, SOURCE_SYSTEM_NAME, filename))
            if len(batch) >= BATCH_SIZE:
                cur.executemany(insert_sql, batch)
                row_count += len(batch)
                batch.clear()
        if batch:
            cur.executemany(insert_sql, batch)
            row_count += len(batch)
    conn.commit()
    return row_count


def load_thai_geo_csv(conn, loaded_at: str, subdir: str, filename: str, table: str, n_cols: int) -> int:
    path = os.path.join(EXTERNAL_SOURCES_ROOT, subdir, filename)
    placeholders = ", ".join(["%s"] * (n_cols + 2))
    insert_sql = f"INSERT INTO {table} VALUES ({placeholders})"

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    cleaned = raw.replace("\r\n", "\n").replace("\r", "\n")

    row_count = 0
    batch = []
    with conn.cursor() as cur:
        reader = csv.reader(io.StringIO(cleaned))
        next(reader)  # skip header
        for row in reader:
            if not row or not any(row):
                continue
            row = (row + [None] * n_cols)[:n_cols]
            batch.append((*row, loaded_at, SOURCE_SYSTEM_NAME))
            if len(batch) >= BATCH_SIZE:
                cur.executemany(insert_sql, batch)
                row_count += len(batch)
                batch.clear()
        if batch:
            cur.executemany(insert_sql, batch)
            row_count += len(batch)
    conn.commit()
    return row_count


def run() -> None:
    conn = _connect()
    loaded_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        n = load_dopa_population_monthly(conn, loaded_at)
        print(f"[bronze] dopa_population_monthly: {n} rows loaded")

        n = load_nso_population_registration(conn, loaded_at, "reg_age_2567.csv")
        print(f"[bronze] nso_population_registration (reg_age_2567.csv): {n} rows loaded")

        n = load_nso_population_registration(conn, loaded_at, "reg_prov_2567.csv")
        print(f"[bronze] nso_population_registration (reg_prov_2567.csv): {n} rows loaded")

        n = load_thai_geo_csv(conn, loaded_at, "thai_geo", "provinces.csv", "thai_geo_province", 9)
        print(f"[bronze] thai_geo_province: {n} rows loaded")

        n = load_thai_geo_csv(conn, loaded_at, "thai_geo", "districts.csv", "thai_geo_district", 9)
        print(f"[bronze] thai_geo_district: {n} rows loaded")

        n = load_thai_geo_csv(conn, loaded_at, "thai_geo", "sub_districts.csv", "thai_geo_subdistrict", 12)
        print(f"[bronze] thai_geo_subdistrict: {n} rows loaded")
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        print(f"[bronze] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

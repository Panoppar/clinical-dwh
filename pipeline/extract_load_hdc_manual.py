"""
Loads bronze.schema_registry, bronze.report_catalog, and the four
category tables (ncd_reports, morbidity_mortality_causes,
occupational_environmental_diseases, air_pollution_diseases) from
HDC_manual_exports_checked.

Design note: this source's own CSV headers are the schema -- the same
report number (e.g. "18") can appear under several different schema_NN
folders because HDC's export tool bakes the comparison year into some
column names (confirmed by inspection: report 18's 2022 extract header
reads "...ปี 2564" / "...ปี 2565", its 2023 extract reads "...ปี 2565" /
"...ปี 2566" -- literally different text, same meaning). So this loader
never assumes a fixed column layout: it reads each file's actual header
row via csv.DictReader and stores every original column verbatim in
raw_data, promoting only the handful of dimension columns
(fiscal_year/health_region/province/area) that are present in virtually
every export, by Thai column name rather than by position.
"""

import csv
import hashlib
import json
import os
import re
from datetime import datetime, timezone

import pymysql

EXTERNAL_SOURCES_ROOT = "/app/external-sources/hdc_manual"
BATCH_SIZE = 2000

CATEGORY_FOLDERS = {
    "01_การป่วยด้วยโรคไม่ติดต่อที่สำคัญ_NCD": ("01", "ncd_reports"),
    "02_สาเหตุการป่วย-ตาย": ("02", "morbidity_mortality_causes"),
    "03_โรคจากการประกอบอาชีพและสิ่งแวดล้อม": ("03", "occupational_environmental_diseases"),
    "04_การป่วยด้วยโรคจากมลพิษทางอากาศ": ("04", "air_pollution_diseases"),
}

DIM_COLUMN_MAP = {
    "fiscal_year": "ปีงบประมาณ",
    "health_region": "เขตสุขภาพ",
    "province": "จังหวัด",
    "area": "พื้นที่",
}

REPORT_NO_RE = re.compile(r"^(\d+(?:\.\d+)?)_")
TABLE_VARIANT_RE = re.compile(r"_table(\d+)\.csv$", re.IGNORECASE)


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


def _read_schema_index(path):
    """Yields (schema_folder, n_columns, report_no, report_name, columns_full) per row."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        for row in reader:
            if not row or not any(row):
                continue
            schema_folder, n_columns, report_no, report_name, columns_full = row[:5]
            yield schema_folder, int(n_columns), report_no, report_name, columns_full


def _first_csv_header(schema_dir):
    """Returns the real header row (list of column names) of the first data
    file in a schema_NN folder. This is the authoritative source for
    columns_json -- the index's own "columns_full" field uses " | " both as
    its top-level separator AND inside hierarchical column names themselves
    (e.g. "รายกลุ่มอายุ | น้อยกว่า 15 ปี | B" is ONE column, not three), so
    splitting that field naively overcounts columns 2-3x. The real CSV
    header has no such ambiguity."""
    for filename in sorted(os.listdir(schema_dir)):
        if filename.endswith(".csv") and filename != "_SCHEMA_INDEX.csv":
            with open(os.path.join(schema_dir, filename), "r", encoding="utf-8-sig", newline="") as f:
                return next(csv.reader(f))
    return None


def load_schema_registry_and_build_lookup(conn):
    """Returns {(category_code, schema_folder): schema_registry_id} and
    {(category_code, schema_folder, report_no): report_name}."""
    registry_id_lookup = {}
    report_name_lookup = {}

    with conn.cursor() as cur:
        for folder_name, (category_code, _table) in CATEGORY_FOLDERS.items():
            index_path = os.path.join(EXTERNAL_SOURCES_ROOT, folder_name, "_SCHEMA_INDEX.csv")
            groups = {}  # schema_folder -> dict(n_columns_declared, report_nos: [], example_name)
            for schema_folder, n_columns, report_no, report_name, _columns_full in _read_schema_index(index_path):
                report_name_lookup[(category_code, schema_folder, report_no)] = report_name
                g = groups.setdefault(schema_folder, {
                    "n_columns_declared": n_columns, "report_nos": [], "example_name": report_name,
                })
                g["report_nos"].append(report_no)

            for schema_folder, g in groups.items():
                schema_dir = os.path.join(EXTERNAL_SOURCES_ROOT, folder_name, schema_folder)
                header = _first_csv_header(schema_dir)
                if header is None:
                    raise ValueError(f"no CSV file found in {folder_name}/{schema_folder}")
                if len(header) != g["n_columns_declared"]:
                    print(f"[hdc_manual] WARNING: {folder_name}/{schema_folder} real header has "
                          f"{len(header)} columns but _SCHEMA_INDEX.csv declares n_columns="
                          f"{g['n_columns_declared']}")

                columns_json = json.dumps(header, ensure_ascii=False)
                columns_hash = hashlib.sha256("|".join(header).encode("utf-8")).hexdigest()
                report_numbers_json = json.dumps(sorted(set(g["report_nos"])), ensure_ascii=False)
                cur.execute(
                    "INSERT INTO schema_registry "
                    "(category_code, category_name, schema_folder, n_columns, columns_json, "
                    "columns_hash, report_numbers_json, example_report_name) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (category_code, folder_name, schema_folder, len(header), columns_json,
                     columns_hash, report_numbers_json, g["example_name"]),
                )
                registry_id_lookup[(category_code, schema_folder)] = cur.lastrowid
    conn.commit()
    return registry_id_lookup, report_name_lookup


def load_report_catalog(conn) -> int:
    ref_dir = os.path.join(EXTERNAL_SOURCES_ROOT, "_reference")
    total = 0
    with conn.cursor() as cur:
        # Master catalog: subcatalog, group, no, label, report_code (covers all 4 categories;
        # report_code is an Excel ="..." -wrapped hash with no column in the provided
        # report_catalog schema -- bronze principle here is to use the given schema as-is,
        # not to invent a new column for a field the DDL didn't provide one for).
        path = os.path.join(ref_dir, "report_catalog_all_categories_master.csv")
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)
            rows = []
            for row in reader:
                if not row or not any(row):
                    continue
                subcatalog, _group, no, label, _report_code = (row + [None] * 5)[:5]
                rows.append((subcatalog, no, label, None, None, None, "report_catalog_all_categories_master.csv"))
            cur.executemany(
                "INSERT INTO report_catalog "
                "(category_name, report_no, report_name, years_available, export_status, export_note, source_catalog_file) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                rows,
            )
            total += len(rows)

        # part1/part2: หัวข้อ, ลำดับ, ชื่อรายงาน, ปีที่มีข้อมูล, ผล, หมายเหตุ
        for fname in ("report_catalog_หัวข้อ02-04_part1.csv", "report_catalog_หัวข้อ02-04_part2.csv"):
            path = os.path.join(ref_dir, fname)
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                next(reader, None)
                rows = []
                for row in reader:
                    if not row or not any(row):
                        continue
                    topic, order_no, name, years, status, note = (row + [None] * 6)[:6]
                    rows.append((topic, order_no, name, years, status, note, fname))
                cur.executemany(
                    "INSERT INTO report_catalog "
                    "(category_name, report_no, report_name, years_available, export_status, export_note, source_catalog_file) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    rows,
                )
                total += len(rows)
    conn.commit()
    return total


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


def load_category_data(conn, registry_id_lookup, report_name_lookup, loaded_at) -> dict:
    counts = {}
    insert_sql_template = (
        "INSERT INTO {table} "
        "(source_file, source_folder, category_code, report_no, report_name, table_variant, "
        "schema_registry_id, fiscal_year, health_region, province, area, row_in_file, raw_data, ingested_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    with conn.cursor() as cur:
        for folder_name, (category_code, table) in CATEGORY_FOLDERS.items():
            category_dir = os.path.join(EXTERNAL_SOURCES_ROOT, folder_name)
            insert_sql = insert_sql_template.format(table=table)
            total_rows = 0

            for schema_folder in sorted(
                d for d in os.listdir(category_dir)
                if os.path.isdir(os.path.join(category_dir, d)) and d.startswith("schema_")
            ):
                schema_dir = os.path.join(category_dir, schema_folder)
                schema_registry_id = registry_id_lookup[(category_code, schema_folder)]

                for filename in sorted(os.listdir(schema_dir)):
                    if not filename.endswith(".csv") or filename == "_SCHEMA_INDEX.csv":
                        continue
                    m = REPORT_NO_RE.match(filename)
                    if not m:
                        raise ValueError(f"cannot parse report_no from filename {filename!r}")
                    report_no = m.group(1)
                    report_name = report_name_lookup.get((category_code, schema_folder, report_no), "")
                    tv_match = TABLE_VARIANT_RE.search(filename)
                    table_variant = f"table{tv_match.group(1)}" if tv_match else None

                    path = os.path.join(schema_dir, filename)
                    with open(path, "r", encoding="utf-8-sig", newline="") as f:
                        reader = csv.DictReader(f)
                        rows = []
                        for row_in_file, row in enumerate(reader, start=1):
                            raw_data = json.dumps(row, ensure_ascii=False)
                            rows.append((
                                filename, schema_folder, category_code, report_no, report_name, table_variant,
                                schema_registry_id,
                                row.get(DIM_COLUMN_MAP["fiscal_year"]),
                                row.get(DIM_COLUMN_MAP["health_region"]),
                                row.get(DIM_COLUMN_MAP["province"]),
                                row.get(DIM_COLUMN_MAP["area"]),
                                row_in_file, raw_data, loaded_at,
                            ))
                        n = _insert_batch(cur, insert_sql, rows)
                        total_rows += n

            counts[table] = total_rows
            print(f"[hdc_manual] {table}: loaded {total_rows} rows")

    conn.commit()
    return counts


def run() -> None:
    loaded_at = datetime.now(timezone.utc)
    conn = _connect()

    registry_id_lookup, report_name_lookup = load_schema_registry_and_build_lookup(conn)
    print(f"[hdc_manual] schema_registry: {len(registry_id_lookup)} rows")

    catalog_rows = load_report_catalog(conn)
    print(f"[hdc_manual] report_catalog: {catalog_rows} rows")

    counts = load_category_data(conn, registry_id_lookup, report_name_lookup, loaded_at)
    print(f"[hdc_manual] total data rows loaded: {sum(counts.values())}")

    conn.close()

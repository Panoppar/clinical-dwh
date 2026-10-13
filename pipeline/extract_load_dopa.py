"""
Loads bronze.dopa_population_by_area_month from the files described in
bronze.dopa_source_file_registry (populated by
sql/bronze/01_create_bronze_dopa_tables.sql, which must run before this).

The registry is the single source of truth for which file lives where and
what admin_level/schema_variant/source_format it carries -- this loader
does not duplicate that mapping, it reads it back from the table that was
seeded verbatim from the provided DDL.

Row-count convention learned by inspection (documented here since it isn't
spelled out in the source DDL): registry.row_count_raw counts the header
row too, for every format (csv/xlsx/html alike) -- so expected data rows
per file = row_count_raw - 1, except the triplicated file where it's
(row_count_raw / distinct_table_count) - 1 per copy.
"""

import csv
import hashlib
import io
import os
from datetime import datetime, timezone
from html.parser import HTMLParser

import openpyxl
import pymysql

EXTERNAL_SOURCES_ROOT = "/app/external-sources/dopa"
BATCH_SIZE = 2000

# Business columns only (excludes lineage columns), in source order.
BUSINESS_COLS = [
    "yymm", "cc_code", "cc_desc", "rcode_code", "rcode_desc",
    "ccaatt_code", "ccaatt_desc", "ccaattmm_code", "ccaattmm_desc",
    "male", "female", "total", "house",
]


def _connect():
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"],
        port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"],
        password=os.environ["DWH_DB_PASSWORD"],
        database="bronze",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
    )


def _row_hash(business_values) -> str:
    return hashlib.sha256("|".join("" if v is None else str(v) for v in business_values).encode("utf-8")).hexdigest()


def _strip_bom(value):
    if isinstance(value, str):
        return value.replace("﻿", "")
    return value


def _read_pipe_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter="|")
        next(reader, None)  # header
        for row in reader:
            if not row or not any(row):
                continue
            row = [_strip_bom(v) for v in row[:13]]  # drop trailing empty field from trailing "|"
            row = (row + [None] * 13)[:13]
            yield row


def _read_comma_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        for row in reader:
            if not row or not any(row):
                continue
            row = [_strip_bom(v) for v in row]
            row = (row + [None] * 13)[:13]
            yield row


def _read_xlsx(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    next(rows, None)  # header
    for row in rows:
        if row is None or not any(row):
            continue
        row = [_strip_bom(v) if v is None else _strip_bom(str(v)) for v in row]
        row = (row + [None] * 13)[:13]
        yield row
    wb.close()


class _TableExtractor(HTMLParser):
    """Extracts <table><tr><td>...</td></tr></table> rows. Handles multiple
    sibling <table> elements (the triplicated file) by starting a new table
    buffer each time <table is seen."""

    def __init__(self):
        super().__init__()
        self.tables = []
        self._cur_table = None
        self._cur_row = None
        self._cur_cell = None
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._cur_table = []
            self.tables.append(self._cur_table)
        elif tag == "tr":
            self._cur_row = []
        elif tag == "td":
            self._in_cell = True
            self._cur_cell = []

    def handle_endtag(self, tag):
        if tag == "td":
            self._in_cell = False
            self._cur_row.append("".join(self._cur_cell).strip())
            self._cur_cell = None
        elif tag == "tr":
            if self._cur_table is not None and self._cur_row:
                self._cur_table.append(self._cur_row)
            self._cur_row = None
        elif tag == "table":
            self._cur_table = None

    def handle_data(self, data):
        if self._in_cell:
            self._cur_cell.append(data)


def _read_html_tables(path):
    """Yields one list-of-rows per <table> found in the file (each row a
    list of 13 cell strings, header row included)."""
    with open(path, "r", encoding="utf-8-sig") as f:
        raw = f.read()
    parser = _TableExtractor()
    parser.feed(raw)
    for table in parser.tables:
        rows = []
        for row in table[1:]:  # skip header row
            if not row or not any(row):
                continue
            row = [_strip_bom(v) for v in row]
            row = (row + [None] * 13)[:13]
            rows.append(row)
        yield rows


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
    "INSERT INTO dopa_population_by_area_month "
    "(yymm, cc_code, cc_desc, rcode_code, rcode_desc, ccaatt_code, ccaatt_desc, "
    "ccaattmm_code, ccaattmm_desc, male, female, total, house, "
    "admin_level, source_file_name, original_file_name, source_format, schema_variant, "
    "source_row_number, is_duplicate_row, row_sha256, batch_id, ingested_at) "
    "VALUES (" + ",".join(["%s"] * 23) + ")"
)


def run() -> None:
    loaded_at = datetime.now(timezone.utc)
    batch_id = f"dopa_load_{loaded_at:%Y%m%dT%H%M%S}"

    conn = _connect()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT source_file_name, original_file_name, folder_path, admin_level, "
            "schema_variant, file_format, distinct_table_count "
            "FROM dopa_source_file_registry ORDER BY file_registry_id"
        )
        files = cur.fetchall()

    total_loaded = 0
    with conn.cursor() as cur:
        for f in files:
            path = os.path.join(EXTERNAL_SOURCES_ROOT, f["folder_path"], f["source_file_name"])
            fmt = f["file_format"]
            rows_to_insert = []

            if fmt == "csv" and f["schema_variant"] == "long_format_pipe_delimited":
                source_format = "csv_pipe"
                data_rows = list(_read_pipe_csv(path))
                for i, row in enumerate(data_rows, start=1):
                    rows_to_insert.append((*row, f["admin_level"], f["source_file_name"],
                                            f["original_file_name"], source_format, f["schema_variant"],
                                            i, 0, _row_hash(row), batch_id, loaded_at))

            elif fmt == "csv":  # raw_source_corrupted_text
                source_format = "csv_comma"
                data_rows = list(_read_comma_csv(path))
                for i, row in enumerate(data_rows, start=1):
                    rows_to_insert.append((*row, f["admin_level"], f["source_file_name"],
                                            f["original_file_name"], source_format, f["schema_variant"],
                                            i, 0, _row_hash(row), batch_id, loaded_at))

            elif fmt == "xlsx":
                source_format = "xlsx"
                data_rows = list(_read_xlsx(path))
                for i, row in enumerate(data_rows, start=1):
                    rows_to_insert.append((*row, f["admin_level"], f["source_file_name"],
                                            f["original_file_name"], source_format, f["schema_variant"],
                                            i, 0, _row_hash(row), batch_id, loaded_at))

            elif fmt == "html":
                source_format = "html_table"
                tables = list(_read_html_tables(path))
                for table_idx, data_rows in enumerate(tables):
                    is_dup = 1 if table_idx > 0 else 0
                    for i, row in enumerate(data_rows, start=1):
                        rows_to_insert.append((*row, f["admin_level"], f["source_file_name"],
                                                f["original_file_name"], source_format, f["schema_variant"],
                                                i, is_dup, _row_hash(row), batch_id, loaded_at))

            else:
                raise ValueError(f"unhandled file_format {fmt!r} for {f['source_file_name']}")

            n = _insert_batch(cur, INSERT_SQL, rows_to_insert)
            total_loaded += n
            print(f"[dopa] loaded {n} rows from {f['source_file_name']}")

    conn.commit()
    conn.close()
    print(f"[dopa] total rows loaded: {total_loaded}")

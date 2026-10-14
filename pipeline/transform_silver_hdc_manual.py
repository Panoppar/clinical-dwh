"""Silver transform: unpivot HDC_manual_exports' 4 category tables' raw_data JSON."""

import json
import os

import pymysql

CATEGORY_TABLES = [
    "ncd_reports",
    "morbidity_mortality_causes",
    "occupational_environmental_diseases",
    "air_pollution_diseases",
]
BATCH_SIZE = 5000


def _connect(database="silver"):
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"],
        port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"],
        password=os.environ["DWH_DB_PASSWORD"],
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.SSCursor,  # streaming: ~287 files' worth of JSON rows
        connect_timeout=10,
    )


def _year_ce(fiscal_year_be):
    if fiscal_year_be is None:
        return None, None
    try:
        be = int(fiscal_year_be)
        return be, be - 543
    except ValueError:
        return None, None


def _insert_batch(cur, insert_sql, rows):
    n = 0
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) >= BATCH_SIZE:
            cur.executemany(insert_sql, batch)
            n += len(batch)
            batch.clear()
    if batch:
        cur.executemany(insert_sql, batch)
        n += len(batch)
    return n


def run() -> None:
    insert_sql = (
        "INSERT INTO hdc_indicator_observations "
        "(category_code, report_no, report_name, table_variant, fiscal_year_be, fiscal_year_ce, "
        "health_region, province, area, source_file, row_in_file, column_name, raw_value) "
        "VALUES (" + ",".join(["%s"] * 13) + ")"
    )

    read_conn = _connect(database="bronze")
    write_conn = pymysql.connect(
        host=os.environ["DWH_DB_HOST"], port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"], password=os.environ["DWH_DB_PASSWORD"],
        database="silver", charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )

    total = 0
    with write_conn.cursor() as wcur:
        for table in CATEGORY_TABLES:
            with read_conn.cursor() as rcur:
                rcur.execute(
                    f"SELECT category_code, report_no, report_name, table_variant, fiscal_year, "
                    f"health_region, province, area, source_file, row_in_file, raw_data FROM {table}"
                )
                rows = []
                table_total = 0
                for (category_code, report_no, report_name, table_variant, fiscal_year,
                     health_region, province, area, source_file, row_in_file, raw_data) in rcur:
                    fiscal_year_be, fiscal_year_ce = _year_ce(fiscal_year)
                    payload = json.loads(raw_data)
                    for column_name, raw_value in payload.items():
                        rows.append((
                            category_code, report_no, report_name, table_variant,
                            fiscal_year_be, fiscal_year_ce, health_region, province, area,
                            source_file, row_in_file, column_name,
                            None if raw_value in (None, "") else str(raw_value)[:1000],
                        ))
                        if len(rows) >= BATCH_SIZE:
                            n = _insert_batch(wcur, insert_sql, rows)
                            write_conn.commit()
                            table_total += n
                            rows = []
                if rows:
                    n = _insert_batch(wcur, insert_sql, rows)
                    write_conn.commit()
                    table_total += n
            print(f"[silver_hdc_manual] {table}: unpivoted {table_total} observation rows")
            total += table_total

    read_conn.close()
    write_conn.close()
    print(f"[silver_hdc_manual] hdc_indicator_observations: loaded {total} rows total")

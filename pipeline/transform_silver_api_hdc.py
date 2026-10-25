"""Silver transform for bronze.api_hdc_observations -> silver.api_hdc_observations.
Resolves report_name via a join against api_hdc_report_catalog and casts
year BE->CE (HDC's byear_list is Buddhist era, e.g. 2569/2568/...).
field_value stays TEXT, same convention as silver.hdc_indicator_observations
(sql/silver/05) -- cast per-report in Gold, not here."""

import os

import pymysql

BATCH_SIZE = 5000


def _connect(database):
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"], port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"], password=os.environ["DWH_DB_PASSWORD"],
        database=database, charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def run() -> None:
    read_conn = _connect("bronze")
    write_conn = _connect("silver")

    with read_conn.cursor() as rcur:
        rcur.execute("SELECT raw_report_code, raw_report_name FROM api_hdc_report_catalog")
        report_name_by_code = {code: (name or "").strip() or None for code, name in rcur}

    insert_sql = (
        "INSERT INTO api_hdc_observations "
        "(report_code, report_name, year_be, year_ce, zone, record_index, field_name, field_value) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    with read_conn.cursor(pymysql.cursors.SSCursor) as rcur:
        rcur.execute(
            "SELECT raw_report_code, raw_year, raw_zone, raw_record_index, raw_field_name, raw_field_value "
            "FROM api_hdc_observations"
        )
        rows = []
        total = 0
        with write_conn.cursor() as wcur:
            for (report_code, year, zone, record_index, field_name, field_value) in rcur:
                try:
                    year_be = int(year)
                except (TypeError, ValueError):
                    continue
                year_ce = year_be - 543
                rows.append((
                    report_code, report_name_by_code.get(report_code), year_be, year_ce,
                    zone, record_index, field_name,
                    None if field_value in (None, "") else str(field_value)[:1000],
                ))
                if len(rows) >= BATCH_SIZE:
                    wcur.executemany(insert_sql, rows)
                    write_conn.commit()
                    total += len(rows)
                    rows = []
            if rows:
                wcur.executemany(insert_sql, rows)
                write_conn.commit()
                total += len(rows)

    read_conn.close()
    write_conn.close()
    print(f"[silver_api_hdc] api_hdc_observations: loaded {total} rows")


if __name__ == "__main__":
    run()

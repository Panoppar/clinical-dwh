"""Silver transform for bronze.api_nso_income -> silver.api_nso_income.
Casts year BE->CE and value to DECIMAL; trims text dimension columns."""

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


def _to_decimal(s):
    if s is None or s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_int(s):
    if s is None or s == "":
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def run() -> None:
    read_conn = _connect("bronze")
    write_conn = _connect("silver")

    insert_sql = (
        "INSERT INTO api_nso_income "
        "(year_be, year_ce, province, source_income1, source_income2, source_income3, "
        "soc_eco_class1, soc_eco_class2, value, unit, attribute_note, source_agency) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    with read_conn.cursor() as rcur:
        rcur.execute(
            "SELECT raw_year, raw_province, raw_source_income1, raw_source_income2, raw_source_income3, "
            "raw_soc_eco_class1, raw_soc_eco_class2, raw_value, raw_unit, raw_attribute, raw_source "
            "FROM api_nso_income"
        )
        rows = []
        total = 0
        with write_conn.cursor() as wcur:
            for (year, province, si1, si2, si3, sec1, sec2, value, unit, attribute, source) in rcur:
                year_be = _to_int(year)
                year_ce = year_be - 543 if year_be is not None else None
                if year_be is None or year_ce is None:
                    continue
                rows.append((
                    year_be, year_ce, (province or "").strip(),
                    (si1 or "").strip() or None, (si2 or "").strip() or None, (si3 or "").strip() or None,
                    (sec1 or "").strip() or None, (sec2 or "").strip() or None,
                    _to_decimal(value), (unit or "").strip() or None,
                    (attribute or "").strip() or None, (source or "").strip() or None,
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
    print(f"[silver_api_nso] api_nso_income: loaded {total} rows")


if __name__ == "__main__":
    run()

"""Silver transform for bronze.api_bma_community -> silver.api_bma_community.
Casts fiscal_year BE->CE and population/male/female to INT; trims text."""

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
        "INSERT INTO api_bma_community "
        "(fiscal_year_be, fiscal_year_ce, district, subdistrict, name_of_community, "
        "type_of_community, population, male, female) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    with read_conn.cursor() as rcur:
        rcur.execute(
            "SELECT raw_fiscal_year, raw_district, raw_subdistrict, raw_name_of_community, "
            "raw_type_of_community, raw_number_of_population, raw_male, raw_female "
            "FROM api_bma_community"
        )
        rows = []
        total = 0
        with write_conn.cursor() as wcur:
            for (fy, district, subdistrict, name, type_of_community, population, male, female) in rcur:
                fy_be = _to_int(fy)
                fy_ce = fy_be - 543 if fy_be is not None else None
                if fy_be is None or fy_ce is None:
                    continue
                rows.append((
                    fy_be, fy_ce, (district or "").strip(), (subdistrict or "").strip(),
                    (name or "").strip(), (type_of_community or "").strip() or None,
                    _to_int(population), _to_int(male), _to_int(female),
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
    print(f"[silver_api_bma] api_bma_community: loaded {total} rows")


if __name__ == "__main__":
    run()

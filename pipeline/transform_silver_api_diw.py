"""Silver transform for bronze.api_diw_factory -> silver.api_diw_factory.
Casts capital/workers/horsepower to numeric; trims text. PII exclusion
(operator_name/phone) was already enforced at Bronze -- nothing to drop here."""

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
        return float(str(s).replace(",", ""))
    except ValueError:
        return None


def _to_int(s):
    d = _to_decimal(s)
    return int(d) if d is not None else None


def run() -> None:
    read_conn = _connect("bronze")
    write_conn = _connect("silver")

    insert_sql = (
        "INSERT INTO api_diw_factory "
        "(reg_no, factory_name, business_desc, address_no, moo, soi, road, tambon, amphoe, "
        "province, postcode, factory_type_code, capital, workers, horsepower, tsic, old_reg_no) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    with read_conn.cursor() as rcur:
        rcur.execute(
            "SELECT raw_reg_no, raw_factory_name, raw_business_desc, raw_address_no, raw_moo, "
            "raw_soi, raw_road, raw_tambon, raw_amphoe, raw_province, raw_postcode, "
            "raw_factory_type_code, raw_capital, raw_workers, raw_horsepower, raw_tsic, raw_old_reg_no "
            "FROM api_diw_factory"
        )
        rows = []
        total = 0
        with write_conn.cursor() as wcur:
            for (reg_no, name, desc, addr, moo, soi, road, tambon, amphoe, province, postcode,
                 type_code, capital, workers, horsepower, tsic, old_reg_no) in rcur:
                if not reg_no or not reg_no.strip():
                    continue
                rows.append((
                    reg_no.strip(), (name or "").strip() or None, (desc or "").strip() or None,
                    (addr or "").strip() or None, (moo or "").strip() or None, (soi or "").strip() or None,
                    (road or "").strip() or None, (tambon or "").strip() or None, (amphoe or "").strip() or None,
                    (province or "").strip() or None, (postcode or "").strip() or None,
                    (type_code or "").strip() or None, _to_decimal(capital), _to_int(workers),
                    _to_decimal(horsepower), (tsic or "").strip() or None, (old_reg_no or "").strip() or None,
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
    print(f"[silver_api_diw] api_diw_factory: loaded {total} rows")


if __name__ == "__main__":
    run()

"""Silver transform for bronze.api_dds_disease_ranking -> silver.api_dds_disease_ranking.
Casts rank/metrics to numeric (stripping thousands-separator commas, same
as kmch-ml's own _dds_to_num()); DDS's year is already CE, unlike the
BE-sourced NSO/BMA/HDC (confirmed in ingest_api_dds.py's probing: candidate
years are plain calendar years like 2026, not Buddhist-era 2569)."""

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
        "INSERT INTO api_dds_disease_ranking "
        "(year_ce, province_code, rank, disease_name, case_count, rate_per_100k, "
        "ipd_count, death_count, case_fatality_pct) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    with read_conn.cursor() as rcur:
        rcur.execute(
            "SELECT raw_year, raw_province_code, raw_rank, raw_disease_name, raw_case_count, "
            "raw_rate_per_100k, raw_ipd_count, raw_death_count, raw_case_fatality_pct "
            "FROM api_dds_disease_ranking"
        )
        rows = []
        total = 0
        with write_conn.cursor() as wcur:
            for (year, province_code, rank, disease_name, case_count, rate, ipd, death, cfp) in rcur:
                year_ce = _to_int(year)
                if year_ce is None or not province_code or not disease_name:
                    continue
                rows.append((
                    year_ce, province_code.strip(), _to_int(rank), disease_name.strip(),
                    _to_decimal(case_count), _to_decimal(rate), _to_decimal(ipd),
                    _to_decimal(death), _to_decimal(cfp),
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
    print(f"[silver_api_dds] api_dds_disease_ranking: loaded {total} rows"
          + (" (0 expected -- DDS's backend has been down since 2026-10-25)" if total == 0 else ""))


if __name__ == "__main__":
    run()

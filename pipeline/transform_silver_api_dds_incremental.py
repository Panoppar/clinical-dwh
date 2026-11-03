"""Incremental Silver transform: bronze.api_dds_disease_ranking -> silver.api_dds_disease_ranking.

Row-level hashing for delta detection (same pattern as every other
incremental source in this pipeline). Business key:
(province_code, year_ce, disease_name).

DDS's year is already CE, unlike the BE-sourced NSO/BMA/HDC (confirmed in
ingest_api_dds.py's probing: candidate years are plain calendar years like
2026, not Buddhist-era 2569) -- no -543 conversion applied, matching the
original transform_silver_api_dds.py.
"""

import hashlib
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


def _row_hash(province_code: str, year_ce: int, disease_name: str, rank, case_count,
              rate, ipd, death, cfp) -> str:
    data = f"{province_code}|{year_ce}|{disease_name}|{rank}|{case_count}|{rate}|{ipd}|{death}|{cfp}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


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

    existing_hashes = set()
    with write_conn.cursor() as wcur:
        wcur.execute("SELECT COALESCE(row_hash, '') FROM api_dds_disease_ranking WHERE row_hash IS NOT NULL")
        for (hash_val,) in wcur:
            existing_hashes.add(hash_val)
    print(f"[silver_api_dds_incremental] loaded {len(existing_hashes)} existing row hashes")

    insert_sql = (
        "INSERT INTO api_dds_disease_ranking "
        "(year_ce, province_code, `rank`, disease_name, case_count, rate_per_100k, "
        "ipd_count, death_count, case_fatality_pct, row_hash, ingestion_batch_id) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    rows_to_insert = []
    skipped_duplicates = 0
    total_processed = 0

    with read_conn.cursor(pymysql.cursors.SSCursor) as rcur:
        rcur.execute(
            "SELECT raw_year, raw_province_code, raw_rank, raw_disease_name, raw_case_count, "
            "raw_rate_per_100k, raw_ipd_count, raw_death_count, raw_case_fatality_pct, ingestion_batch_id "
            "FROM api_dds_disease_ranking"
        )

        total_inserted = 0
        with write_conn.cursor() as wcur:
            for (year, province_code, rank, disease_name, case_count, rate, ipd, death, cfp, batch_id) in rcur:
                total_processed += 1

                year_ce = _to_int(year)
                disease_clean = (disease_name or "").strip()
                province_clean = (province_code or "").strip()
                if year_ce is None or not province_clean or not disease_clean:
                    continue

                hash_val = _row_hash(province_clean, year_ce, disease_clean, rank, case_count, rate, ipd, death, cfp)

                if hash_val in existing_hashes:
                    skipped_duplicates += 1
                    continue

                rows_to_insert.append((
                    year_ce, province_clean, _to_int(rank), disease_clean,
                    _to_decimal(case_count), _to_decimal(rate), _to_decimal(ipd),
                    _to_decimal(death), _to_decimal(cfp), hash_val, batch_id,
                ))
                existing_hashes.add(hash_val)

                if len(rows_to_insert) >= BATCH_SIZE:
                    wcur.executemany(insert_sql, rows_to_insert)
                    write_conn.commit()
                    total_inserted += len(rows_to_insert)
                    rows_to_insert.clear()

            if rows_to_insert:
                wcur.executemany(insert_sql, rows_to_insert)
                write_conn.commit()
                total_inserted += len(rows_to_insert)

    read_conn.close()
    write_conn.close()

    print(f"[silver_api_dds_incremental] processed {total_processed} Bronze rows")
    print(f"[silver_api_dds_incremental] skipped {skipped_duplicates} existing rows")
    print(f"[silver_api_dds_incremental] inserted {total_inserted} new rows"
          + (" (0 expected -- DDS backend down since 2026-10-25)" if total_processed == 0 else ""))


if __name__ == "__main__":
    run()

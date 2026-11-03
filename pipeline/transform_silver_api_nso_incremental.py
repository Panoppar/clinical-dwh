"""Incremental Silver transform: bronze.api_nso_income → silver.api_nso_income

Row-level hashing for delta detection (same pattern as HDC).
Business key: (year_ce, province, source_income1, source_income2, source_income3, soc_eco_class1, soc_eco_class2)
"""

import hashlib
import os

import pymysql

BATCH_SIZE = 5000


def _connect(database):
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"],
        port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"],
        password=os.environ["DWH_DB_PASSWORD"],
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def _row_hash(year_ce: int, province: str, si1: str, si2: str, si3: str, sec1: str, sec2: str, value: str) -> str:
    """Deterministic hash of business columns."""
    data = f"{year_ce}|{province}|{si1}|{si2}|{si3}|{sec1}|{sec2}|{value}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


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

    # Load existing row hashes
    existing_hashes = set()
    with write_conn.cursor() as wcur:
        wcur.execute("SELECT COALESCE(row_hash, '') FROM api_nso_income WHERE row_hash IS NOT NULL")
        for (hash_val,) in wcur:
            existing_hashes.add(hash_val)
    print(f"[silver_api_nso_incremental] loaded {len(existing_hashes)} existing row hashes")

    insert_sql = (
        "INSERT INTO api_nso_income "
        "(year_be, year_ce, province, source_income1, source_income2, source_income3, "
        "soc_eco_class1, soc_eco_class2, value, unit, attribute_note, source_agency, row_hash, ingestion_batch_id) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    rows_to_insert = []
    skipped_duplicates = 0
    total_processed = 0

    with read_conn.cursor(pymysql.cursors.SSCursor) as rcur:
        rcur.execute(
            "SELECT raw_year, raw_province, raw_source_income1, raw_source_income2, raw_source_income3, "
            "raw_soc_eco_class1, raw_soc_eco_class2, raw_value, raw_unit, raw_attribute, raw_source, ingestion_batch_id "
            "FROM api_nso_income"
        )

        total_inserted = 0
        with write_conn.cursor() as wcur:
            for (year, province, si1, si2, si3, sec1, sec2, value, unit, attribute, source, batch_id) in rcur:
                total_processed += 1

                # Convert year BE → CE
                year_be = _to_int(year)
                year_ce = year_be - 543 if year_be is not None else None
                if year_be is None or year_ce is None:
                    continue

                # Clean text
                province_clean = (province or "").strip() or None
                si1_clean = (si1 or "").strip() or None
                si2_clean = (si2 or "").strip() or None
                si3_clean = (si3 or "").strip() or None
                sec1_clean = (sec1 or "").strip() or None
                sec2_clean = (sec2 or "").strip() or None

                # Row hash
                hash_val = _row_hash(year_ce, province_clean or "", si1_clean or "", si2_clean or "",
                                     si3_clean or "", sec1_clean or "", sec2_clean or "", value or "")

                # Delta detection
                if hash_val in existing_hashes:
                    skipped_duplicates += 1
                    continue

                # New row
                value_decimal = _to_decimal(value)
                rows_to_insert.append((
                    year_be, year_ce, province_clean, si1_clean, si2_clean, si3_clean,
                    sec1_clean, sec2_clean, value_decimal,
                    (unit or "").strip() or None, (attribute or "").strip() or None,
                    (source or "").strip() or None, hash_val, batch_id
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

    print(f"[silver_api_nso_incremental] processed {total_processed} Bronze rows")
    print(f"[silver_api_nso_incremental] skipped {skipped_duplicates} existing rows")
    print(f"[silver_api_nso_incremental] inserted {total_inserted} new rows")


if __name__ == "__main__":
    run()

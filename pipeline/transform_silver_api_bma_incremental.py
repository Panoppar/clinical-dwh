"""Incremental Silver transform: bronze.api_bma_community → silver.api_bma_community

Row-level hashing for delta detection.
Business key: (fiscal_year_ce, district, subdistrict, name_of_community)
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


def _row_hash(fy_ce: int, district: str, subdistrict: str, name: str, pop: str) -> str:
    """Deterministic hash of business columns."""
    data = f"{fy_ce}|{district}|{subdistrict}|{name}|{pop}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


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

    # Load existing hashes
    existing_hashes = set()
    with write_conn.cursor() as wcur:
        wcur.execute("SELECT COALESCE(row_hash, '') FROM api_bma_community WHERE row_hash IS NOT NULL")
        for (hash_val,) in wcur:
            existing_hashes.add(hash_val)
    print(f"[silver_api_bma_incremental] loaded {len(existing_hashes)} existing row hashes")

    insert_sql = (
        "INSERT INTO api_bma_community "
        "(fiscal_year_be, fiscal_year_ce, district, subdistrict, name_of_community, "
        "type_of_community, population, male, female, row_hash, ingestion_batch_id) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    rows_to_insert = []
    skipped_duplicates = 0
    total_processed = 0

    with read_conn.cursor(pymysql.cursors.SSCursor) as rcur:
        rcur.execute(
            "SELECT raw_fiscal_year, raw_district, raw_subdistrict, raw_name_of_community, "
            "raw_type_of_community, raw_number_of_population, raw_male, raw_female, ingestion_batch_id "
            "FROM api_bma_community"
        )

        total_inserted = 0
        with write_conn.cursor() as wcur:
            for (fy, district, subdistrict, name, type_c, population, male, female, batch_id) in rcur:
                total_processed += 1

                # Convert year
                fy_be = _to_int(fy)
                fy_ce = fy_be - 543 if fy_be is not None else None
                if fy_be is None or fy_ce is None:
                    continue

                # Clean text
                district_clean = (district or "").strip()
                subdistrict_clean = (subdistrict or "").strip()
                name_clean = (name or "").strip()

                # Row hash
                hash_val = _row_hash(fy_ce, district_clean, subdistrict_clean, name_clean, population or "")

                # Delta detection
                if hash_val in existing_hashes:
                    skipped_duplicates += 1
                    continue

                # New row (NO FILTERING - all provinces/districts)
                rows_to_insert.append((
                    fy_be, fy_ce, district_clean, subdistrict_clean, name_clean,
                    (type_c or "").strip() or None,
                    _to_int(population), _to_int(male), _to_int(female),
                    hash_val, batch_id
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

    print(f"[silver_api_bma_incremental] processed {total_processed} Bronze rows")
    print(f"[silver_api_bma_incremental] skipped {skipped_duplicates} existing rows")
    print(f"[silver_api_bma_incremental] inserted {total_inserted} new rows (ALL provinces, no filtering)")


if __name__ == "__main__":
    run()

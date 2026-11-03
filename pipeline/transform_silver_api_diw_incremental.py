"""Incremental Silver transform: bronze.api_diw_factory → silver.api_diw_factory

Row-level hashing for delta detection.
Business key: (reg_no, tsic, factory_type_code)
DIW is a snapshot (no time dimension), so hashing catches any changes to factory data.
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


def _row_hash(reg_no: str, name: str, capital: str, workers: str) -> str:
    """Deterministic hash of business columns."""
    data = f"{reg_no}|{name}|{capital}|{workers}"
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

    # Load existing hashes
    existing_hashes = set()
    with write_conn.cursor() as wcur:
        wcur.execute("SELECT COALESCE(row_hash, '') FROM api_diw_factory WHERE row_hash IS NOT NULL")
        for (hash_val,) in wcur:
            existing_hashes.add(hash_val)
    print(f"[silver_api_diw_incremental] loaded {len(existing_hashes)} existing row hashes")

    insert_sql = (
        "INSERT INTO api_diw_factory "
        "(reg_no, factory_name, business_desc, address_no, moo, soi, road, tambon, amphoe, province, "
        "postcode, factory_type_code, capital, workers, horsepower, tsic, old_reg_no, row_hash, ingestion_batch_id) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    rows_to_insert = []
    skipped_duplicates = 0
    total_processed = 0

    with read_conn.cursor(pymysql.cursors.SSCursor) as rcur:
        rcur.execute(
            "SELECT raw_reg_no, raw_factory_name, raw_business_desc, raw_address_no, raw_moo, "
            "raw_soi, raw_road, raw_tambon, raw_amphoe, raw_province, raw_postcode, "
            "raw_factory_type_code, raw_capital, raw_workers, raw_horsepower, raw_tsic, raw_old_reg_no, ingestion_batch_id "
            "FROM api_diw_factory"
        )

        total_inserted = 0
        with write_conn.cursor() as wcur:
            for (reg_no, name, bus_desc, addr, moo, soi, road, tambon, amphoe, province,
                 postcode, ftc, capital, workers, hp, tsic, old_reg, batch_id) in rcur:
                total_processed += 1

                # Clean text
                reg_no_clean = (reg_no or "").strip() or None
                if not reg_no_clean:
                    continue

                # Row hash (key factory identifiers)
                hash_val = _row_hash(reg_no_clean, name or "", capital or "", workers or "")

                # Delta detection
                if hash_val in existing_hashes:
                    skipped_duplicates += 1
                    continue

                # New row (NO FILTERING - all provinces/factories)
                rows_to_insert.append((
                    reg_no_clean, (name or "").strip() or None, (bus_desc or "").strip() or None,
                    (addr or "").strip() or None, (moo or "").strip() or None,
                    (soi or "").strip() or None, (road or "").strip() or None,
                    (tambon or "").strip() or None, (amphoe or "").strip() or None,
                    (province or "").strip() or None, (postcode or "").strip() or None,
                    (ftc or "").strip() or None, _to_decimal(capital), _to_int(workers),
                    _to_decimal(hp), (tsic or "").strip() or None,
                    (old_reg or "").strip() or None, hash_val, batch_id
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

    print(f"[silver_api_diw_incremental] processed {total_processed} Bronze rows")
    print(f"[silver_api_diw_incremental] skipped {skipped_duplicates} existing rows")
    print(f"[silver_api_diw_incremental] inserted {total_inserted} new rows (ALL provinces, no filtering)")


if __name__ == "__main__":
    run()

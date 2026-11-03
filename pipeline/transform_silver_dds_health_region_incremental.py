"""Incremental Silver transform: bronze.dds_health_region_disease_report ->
silver.dds_health_region_disease_report.

Row-level hashing for delta detection (same pattern as every other
incremental source in this pipeline). Business key:
(health_region_code, report_year_ce, report_period_label, disease_name_th).

YEAR NOTE: report_year is already Gregorian here (confirmed against the
PDF's own cover text and the filename) -- no BE->CE conversion, unlike
every other source in this project.
"""

import hashlib
import os

import pymysql

BATCH_SIZE = 2000


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


def _row_hash(region: str, year_ce: int, period: str, disease: str, patient_count,
              morbidity_rate, ipd_count, death_count, cfr) -> str:
    data = f"{region}|{year_ce}|{period}|{disease}|{patient_count}|{morbidity_rate}|{ipd_count}|{death_count}|{cfr}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def _to_int(s):
    if s is None or s == "":
        return None
    try:
        return int(str(s).replace(",", ""))
    except ValueError:
        return None


def _to_decimal(s):
    if s is None or s == "":
        return None
    try:
        return float(str(s).replace(",", ""))
    except ValueError:
        return None


def run() -> None:
    read_conn = _connect("bronze")
    write_conn = _connect("silver")

    existing_hashes = set()
    with write_conn.cursor() as wcur:
        wcur.execute("SELECT COALESCE(row_hash, '') FROM dds_health_region_disease_report WHERE row_hash IS NOT NULL")
        for (hash_val,) in wcur:
            existing_hashes.add(hash_val)
    print(f"[silver_dds_health_region_incremental] loaded {len(existing_hashes)} existing row hashes")

    insert_sql = (
        "INSERT INTO dds_health_region_disease_report "
        "(health_region_code, report_year_ce, report_period_label, rank_no, disease_name_th, "
        "patient_count, morbidity_rate_per_100k, ipd_count, death_count, case_fatality_rate_pct, "
        "is_aggregate_row, row_hash, ingestion_batch_id) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    rows_to_insert = []
    skipped_duplicates = 0
    total_processed = 0

    with read_conn.cursor(pymysql.cursors.SSCursor) as rcur:
        rcur.execute(
            "SELECT health_region_code, report_year, report_period_label, raw_no, raw_disease_name_th, "
            "raw_patient_count, raw_morbidity_rate, raw_ipd_count, raw_death_count, raw_case_fatality_rate, "
            "ingestion_batch_id "
            "FROM dds_health_region_disease_report"
        )

        total_inserted = 0
        with write_conn.cursor() as wcur:
            for (region, year, period, no, disease, patient_count, morbidity_rate,
                 ipd_count, death_count, cfr, batch_id) in rcur:
                total_processed += 1

                year_ce = _to_int(year)
                disease_clean = (disease or "").strip()
                if year_ce is None or not disease_clean:
                    continue

                hash_val = _row_hash(region, year_ce, period, disease_clean,
                                     patient_count, morbidity_rate, ipd_count, death_count, cfr)

                if hash_val in existing_hashes:
                    skipped_duplicates += 1
                    continue

                is_aggregate = 1 if disease_clean.endswith("รวม") else 0

                rows_to_insert.append((
                    region, year_ce, period, _to_int(no), disease_clean,
                    _to_int(patient_count), _to_decimal(morbidity_rate), _to_int(ipd_count),
                    _to_int(death_count), _to_decimal(cfr), is_aggregate, hash_val, batch_id,
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

    print(f"[silver_dds_health_region_incremental] processed {total_processed} Bronze rows")
    print(f"[silver_dds_health_region_incremental] skipped {skipped_duplicates} existing rows")
    print(f"[silver_dds_health_region_incremental] inserted {total_inserted} new rows")


if __name__ == "__main__":
    run()

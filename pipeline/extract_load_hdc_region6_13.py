"""
Loads the 19 HDC region6_13_by_age_api bronze tables. One table per source
file; all three measure-column shapes (monthly incidence, annual incidence,
pop_age, death_age) share the same 8 leading dimension columns
(province_code..b_year) followed by shape-specific measure columns, so a
single generic loader drives off a small manifest rather than writing
near-duplicate code per file.
"""

import csv
import os
from datetime import datetime, timezone

import pymysql

EXTERNAL_SOURCES_ROOT = "/app/external-sources/hdc_region6_13"
BATCH_SIZE = 2000

DIM_COLS = ["province_code", "province_name", "id", "hospcode", "areacode", "flag_sent", "date_com", "b_year"]

# (relative_path, table, measure_cols, n_raw_cols)
# n_raw_cols = len(DIM_COLS) + len(measure_cols) + 1 (trailing "ip" column)
FILES = [
    ("incidence/monthly/s_asthma_incidence.csv", "inc_monthly_asthma",
     ["target", "result", "result10", "result11", "result12", "result01", "result02",
      "result03", "result04", "result05", "result06", "result07", "result08", "result09"]),
    ("incidence/monthly/s_copd_incidence.csv", "inc_monthly_copd",
     ["target", "result", "result10", "result11", "result12", "result01", "result02",
      "result03", "result04", "result05", "result06", "result07", "result08", "result09"]),
    ("incidence/monthly/s_coronary_incidence.csv", "inc_monthly_coronary",
     ["target", "result", "result10", "result11", "result12", "result01", "result02",
      "result03", "result04", "result05", "result06", "result07", "result08", "result09"]),
    ("incidence/monthly/s_dm_incidence.csv", "inc_monthly_dm",
     ["target", "result", "result10", "result11", "result12", "result01", "result02",
      "result03", "result04", "result05", "result06", "result07", "result08", "result09"]),
    ("incidence/monthly/s_ht_incidence.csv", "inc_monthly_ht",
     ["target", "result", "result10", "result11", "result12", "result01", "result02",
      "result03", "result04", "result05", "result06", "result07", "result08", "result09"]),
    ("incidence/annual_target/s_ihd_incidence_annual.csv", "inc_annual_ihd",
     ["target", "result", "target1", "result1"]),
    ("population_by_age/s_ca_breast_pop_age.csv", "pop_age_ca_breast",
     ["pop_group1", "result_group1", "pop_group2", "result_group2", "pop_group3", "result_group3",
      "pop_group4", "result_group4", "pop_group5", "result_group5"]),
    ("population_by_age/s_ca_cervix_pop_age.csv", "pop_age_ca_cervix",
     ["pop_group1", "result_group1", "pop_group2", "result_group2", "pop_group3", "result_group3",
      "pop_group4", "result_group4", "pop_group5", "result_group5"]),
    ("population_by_age/s_ca_lung_pop_age.csv", "pop_age_ca_lung",
     ["pop_group1", "result_group1", "pop_group2", "result_group2", "pop_group3", "result_group3",
      "pop_group4", "result_group4", "pop_group5", "result_group5"]),
    ("population_by_age/s_copd_pop_age.csv", "pop_age_copd",
     ["pop_group1", "result_group1", "pop_group2", "result_group2", "pop_group3", "result_group3",
      "pop_group4", "result_group4", "pop_group5", "result_group5"]),
    ("population_by_age/s_coronary_pop_age.csv", "pop_age_coronary",
     ["pop_group1", "result_group1", "pop_group2", "result_group2", "pop_group3", "result_group3",
      "pop_group4", "result_group4", "pop_group5", "result_group5"]),
    ("population_by_age/s_dm_pop_age.csv", "pop_age_dm",
     ["pop_group1", "result_group1", "pop_group2", "result_group2", "pop_group3", "result_group3",
      "pop_group4", "result_group4", "pop_group5", "result_group5"]),
    ("population_by_age/s_emphysema_pop_age.csv", "pop_age_emphysema",
     ["pop_group1", "result_group1", "pop_group2", "result_group2", "pop_group3", "result_group3",
      "pop_group4", "result_group4", "pop_group5", "result_group5"]),
    ("population_by_age/s_ht_pop_age.csv", "pop_age_ht",
     ["pop_group1", "result_group1", "pop_group2", "result_group2", "pop_group3", "result_group3",
      "pop_group4", "result_group4", "pop_group5", "result_group5"]),
    ("population_by_age/s_stroke_pop_age.csv", "pop_age_stroke",
     ["pop_group1", "result_group1", "pop_group2", "result_group2", "pop_group3", "result_group3",
      "pop_group4", "result_group4", "pop_group5", "result_group5"]),
    ("death_by_age/s_copd_death_age.csv", "death_age_copd",
     ["pt_group1", "death_group1", "pt_group2", "death_group2", "pt_group3", "death_group3",
      "pt_group4", "death_group4", "pt_group5", "death_group5"]),
    ("death_by_age/s_coronary_death_age.csv", "death_age_coronary",
     ["pt_group1", "death_group1", "pt_group2", "death_group2", "pt_group3", "death_group3",
      "pt_group4", "death_group4", "pt_group5", "death_group5"]),
    ("death_by_age/s_dm_death_age.csv", "death_age_dm",
     ["pt_group1", "death_group1", "pt_group2", "death_group2", "pt_group3", "death_group3",
      "pt_group4", "death_group4", "pt_group5", "death_group5"]),
    ("death_by_age/s_ht_death_age.csv", "death_age_ht",
     ["pt_group1", "death_group1", "pt_group2", "death_group2", "pt_group3", "death_group3",
      "pt_group4", "death_group4", "pt_group5", "death_group5"]),
]


def _connect():
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"],
        port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"],
        password=os.environ["DWH_DB_PASSWORD"],
        database="bronze",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def _insert_batch(cur, insert_sql, rows):
    row_count = 0
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) >= BATCH_SIZE:
            cur.executemany(insert_sql, batch)
            row_count += len(batch)
            batch.clear()
    if batch:
        cur.executemany(insert_sql, batch)
        row_count += len(batch)
    return row_count


def run() -> None:
    loaded_at = datetime.now(timezone.utc)
    batch_id = f"hdc_region6_13_load_{loaded_at:%Y%m%dT%H%M%S}"

    conn = _connect()
    total = 0
    with conn.cursor() as cur:
        for rel_path, table, measure_cols in FILES:
            filename = os.path.basename(rel_path)
            path = os.path.join(EXTERNAL_SOURCES_ROOT, rel_path)
            n_raw_cols = len(DIM_COLS) + len(measure_cols) + 1  # + trailing "ip"
            n_measure = len(measure_cols)

            all_cols = DIM_COLS + measure_cols + ["ip"]
            insert_sql = (
                f"INSERT INTO {table} ({', '.join(all_cols)}, "
                "_source_file_name, _ingestion_batch_id, _source_row_num) "
                f"VALUES ({', '.join(['%s'] * (n_raw_cols + 3))})"
            )

            rows = []
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                next(reader, None)  # header
                for i, row in enumerate(reader, start=1):
                    if not row or not any(row):
                        continue
                    row = (row + [None] * n_raw_cols)[:n_raw_cols]
                    # Measure columns are DECIMAL in bronze; empty string must
                    # become NULL, not an invalid-for-DECIMAL ''.
                    dims = row[:8]
                    measures = [None if v == "" else v for v in row[8:8 + n_measure]]
                    ip = row[8 + n_measure] if len(row) > 8 + n_measure else None
                    rows.append((*dims, *measures, ip, filename, batch_id, i))

            n = _insert_batch(cur, insert_sql, rows)
            total += n
            print(f"[hdc_region6_13] {table}: loaded {n} rows from {filename}")
    conn.commit()
    conn.close()
    print(f"[hdc_region6_13] total rows loaded: {total}")

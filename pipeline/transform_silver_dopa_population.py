"""Cleanses bronze.dopa_population_year + bronze.dopa_population_supplement
into silver.dopa_population_by_unit_year -- casts text to INT, converts
year_be -> year_ce, and unions the two sources (confirmed zero overlapping
(unit_code, year_be) pairs between them, see sql/silver/21's header note).
"""

import os

import pymysql

FINE_COLS = [
    "fine_male_0_4", "fine_female_0_4", "fine_male_5_9", "fine_female_5_9",
    "fine_male_10_14", "fine_female_10_14", "fine_male_15_17", "fine_female_15_17",
    "fine_male_18_22", "fine_female_18_22", "fine_male_23_29", "fine_female_23_29",
    "fine_male_30_39", "fine_female_30_39", "fine_male_40_49", "fine_female_40_49",
    "fine_male_50_59", "fine_female_50_59", "fine_male_60_plus", "fine_female_60_plus",
]
COARSE_COLS = [
    "coarse_male_0_14", "coarse_female_0_14", "coarse_male_15_59", "coarse_female_15_59",
    "coarse_male_60_plus", "coarse_female_60_plus",
]


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
    return int(s)


def run() -> None:
    bronze_conn = _connect("bronze")
    silver_conn = _connect("silver")

    rows = []

    with bronze_conn.cursor() as bcur:
        cols = ", ".join(["raw_unit_code", "raw_year_be", "raw_ref_month"]
                          + [f"raw_{c}" for c in FINE_COLS]
                          + [f"raw_{c}" for c in COARSE_COLS]
                          + ["raw_pop_male", "raw_pop_female", "raw_pop_total",
                             "raw_pop_age_known", "raw_pop_unknown_age", "raw_source_file"])
        bcur.execute(f"SELECT {cols} FROM dopa_population_year")
        for rec in bcur.fetchall():
            unit_code, year_be, ref_month = rec[0], int(rec[1]), _to_int(rec[2])
            fine_vals = [_to_int(v) for v in rec[3:3 + len(FINE_COLS)]]
            coarse_vals = [_to_int(v) for v in rec[3 + len(FINE_COLS):3 + len(FINE_COLS) + len(COARSE_COLS)]]
            pop_male, pop_female, pop_total, pop_age_known, pop_unknown_age, source_file = rec[-6:]
            rows.append((
                unit_code, year_be, year_be - 543, ref_month, "full",
                *fine_vals, *coarse_vals,
                _to_int(pop_male), _to_int(pop_female), _to_int(pop_total),
                _to_int(pop_age_known), _to_int(pop_unknown_age), source_file,
            ))

        bcur.execute("SELECT raw_unit_code, raw_year_be, raw_pop_total, raw_source FROM dopa_population_supplement")
        for unit_code, year_be, pop_total, source in bcur.fetchall():
            year_be = int(year_be)
            rows.append((
                unit_code, year_be, year_be - 543, None, "total_only",
                *([None] * len(FINE_COLS)), *([None] * len(COARSE_COLS)),
                None, None, _to_int(pop_total), None, None, source,
            ))

    insert_sql = (
        "INSERT INTO dopa_population_by_unit_year "
        "(unit_code, year_be, year_ce, ref_month, data_source, "
        + ", ".join(FINE_COLS) + ", " + ", ".join(COARSE_COLS) + ", "
        "pop_male, pop_female, pop_total, pop_age_known, pop_unknown_age, source_note) "
        "VALUES (" + ", ".join(["%s"] * (5 + len(FINE_COLS) + len(COARSE_COLS) + 6)) + ")"
    )
    with silver_conn.cursor() as scur:
        scur.executemany(insert_sql, rows)
    silver_conn.commit()

    n_full = sum(1 for r in rows if r[4] == "full")
    n_total_only = sum(1 for r in rows if r[4] == "total_only")
    print(f"[silver_dopa_population] dopa_population_by_unit_year: {len(rows)} rows "
          f"({n_full} full, {n_total_only} total_only)")

    bronze_conn.close()
    silver_conn.close()


if __name__ == "__main__":
    run()

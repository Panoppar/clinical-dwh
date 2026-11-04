"""Builds the 4 Gold fact tables that fall outside the 5-source incremental
migration's scope: fact_hdc_weekly_observation, fact_hospital_access,
fact_population_by_area, fact_migrant_worker_permit. Must run after
transform_gold_dimensions.py (needs dim_hdc_report/dim_area/dim_facility/
dim_bma_zone/dim_date) and transform_gold_all_sources_incremental.py is not
a dependency, just a convenient place in run_pipeline.py's call order.

These 4 are a plain full rebuild every run (matching their own DDL in
sql/gold/05, 06, 08, 11, which is still DROP+CREATE, not CREATE TABLE IF
NOT EXISTS) -- restored 2026-11-03 after being lost when the old
transform_gold_facts.py was deleted during the incremental migration
cleanup. That file built 9 fact tables total; only 5 were ported to
transform_gold_all_sources_incremental.py (the ones the migration actually
targeted -- fact_income/factory/community_population/disease_ranking/
hdc_observation). These other 4 were never the OOM/duplication problem
that migration solved, so a full rebuild here is still the right shape for
them -- they just need to actually run again.
"""

import os
import re
from collections import defaultdict

import pymysql

# The 4 PM2.5-linked weekly disease reports (kmch-ml input-parity gap 2) --
# already discovered by the existing HDC subcatalog crawl under
# "การป่วยด้วยโรคจากมลพิษทางอากาศ" (air pollution disease), confirmed live
# 2026-10-26, not a separate report family needing ingest changes.
HDC_WEEKLY_REPORT_CODES = (
    "NL9idjvwQKjv6R6Maiw9", "cxG0gstCJkfG1X1c71y4o",
    "58t8PvddP1nCaDdSTuakd", "5968980caf87d4518aa9f0263a9299c9",
)
_WEEKLY_FIELD_RE = re.compile(r"^w_(\d+)_(\w+)$")
_ALL_FIELD_RE = re.compile(r"^all_(\w+)$")


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


def _build_fact_hdc_weekly(silver_conn, gold_conn):
    """kmch-ml input-parity gap 2. These 4 reports' field names (group_name/
    ordering/w_NN_variant/all_variant) never match fact_hdc_observation's
    headline-field set, so they're implicitly excluded from that pivot
    already (confirmed: 0 rows there for these report codes) -- this is a
    separate fact table, not a change to the existing one."""
    with gold_conn.cursor() as cur:
        cur.execute("SELECT report_key, report_code FROM dim_hdc_report")
        report_lookup = {code: key for key, code in cur.fetchall()}

    placeholders = ",".join(["%s"] * len(HDC_WEEKLY_REPORT_CODES))
    meta: dict[tuple, dict] = defaultdict(dict)  # (report_code,year,zone,record_index) -> {group_name, ordering}
    metrics: list[tuple] = []  # (report_code, year, zone, record_index, week_number, variant, value)
    with silver_conn.cursor(pymysql.cursors.SSCursor) as scur:
        scur.execute(
            f"SELECT report_code, year_ce, zone, record_index, field_name, field_value "
            f"FROM api_hdc_observations WHERE report_code IN ({placeholders})",
            HDC_WEEKLY_REPORT_CODES,
        )
        for report_code, year_ce, zone, record_index, field_name, field_value in scur:
            key = (report_code, year_ce, zone, record_index)
            if field_name == "group_name":
                meta[key]["group_name"] = field_value
            elif field_name == "ordering":
                meta[key]["ordering"] = _to_int(field_value)
            elif (m := _WEEKLY_FIELD_RE.match(field_name)):
                metrics.append((report_code, year_ce, zone, record_index, int(m.group(1)), m.group(2), field_value))
            elif (m := _ALL_FIELD_RE.match(field_name)):
                metrics.append((report_code, year_ce, zone, record_index, None, m.group(1), field_value))

    insert_sql = (
        "INSERT INTO fact_hdc_weekly_observation (report_key, date_key, zone, record_index, "
        "disease_group_name, ordering, week_number, metric_variant, metric_value) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    rows = []
    for report_code, year_ce, zone, record_index, week_number, variant, value in metrics:
        report_key = report_lookup.get(report_code)
        if report_key is None or year_ce is None:
            continue
        m = meta.get((report_code, year_ce, zone, record_index), {})
        rows.append((
            report_key, year_ce, zone, record_index,
            m.get("group_name"), m.get("ordering"), week_number, variant, _to_decimal(value),
        ))

    with gold_conn.cursor() as cur:
        BATCH = 5000
        for i in range(0, len(rows), BATCH):
            cur.executemany(insert_sql, rows[i:i + BATCH])
    gold_conn.commit()
    print(f"[gold_fact_extended] fact_hdc_weekly_observation: {len(rows)} rows")


def _build_fact_hospital_access(silver_conn, gold_conn):
    """kmch-ml input-parity gap 3. Raw travel matrix only -- no Huff
    share/E2SFCA scoring, see sql/gold/06."""
    with gold_conn.cursor() as cur:
        cur.execute("SELECT area_key, unit_code FROM dim_area")
        area_lookup = {code: key for key, code in cur.fetchall()}
        cur.execute("SELECT facility_key, destination_id FROM dim_facility")
        facility_lookup = {dest_id: key for key, dest_id in cur.fetchall()}

    with silver_conn.cursor() as scur:
        scur.execute("SELECT source_unit_code, destination_id, duration_s, distance_m FROM geo_travel_matrix")
        rows_in = scur.fetchall()

    rows = []
    for unit_code, dest_id, duration, distance in rows_in:
        area_key = area_lookup.get(unit_code)
        facility_key = facility_lookup.get(dest_id)
        if area_key is None or facility_key is None:
            continue
        rows.append((area_key, facility_key, duration, distance))

    with gold_conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO fact_hospital_access (area_key, facility_key, duration_s, distance_m) "
            "VALUES (%s,%s,%s,%s)", rows,
        )
    gold_conn.commit()
    print(f"[gold_fact_extended] fact_hospital_access: {len(rows)} rows")


_POPULATION_FINE_COLS = [
    "fine_male_0_4", "fine_female_0_4", "fine_male_5_9", "fine_female_5_9",
    "fine_male_10_14", "fine_female_10_14", "fine_male_15_17", "fine_female_15_17",
    "fine_male_18_22", "fine_female_18_22", "fine_male_23_29", "fine_female_23_29",
    "fine_male_30_39", "fine_female_30_39", "fine_male_40_49", "fine_female_40_49",
    "fine_male_50_59", "fine_female_50_59", "fine_male_60_plus", "fine_female_60_plus",
]
_POPULATION_COARSE_COLS = [
    "coarse_male_0_14", "coarse_female_0_14", "coarse_male_15_59", "coarse_female_15_59",
    "coarse_male_60_plus", "coarse_female_60_plus",
]


def _build_fact_population_by_area(silver_conn, gold_conn):
    """kmch-ml input-parity gap 1 (the previously-deferred "DOPA
    population" gap). Grain: one row per (unit, year) -- FK to dim_area,
    not dim_geography (this data is already at dim_area's merged-unit
    grain, see sql/gold/08's header note)."""
    with gold_conn.cursor() as cur:
        cur.execute("SELECT area_key, unit_code FROM dim_area")
        area_lookup = {code: key for key, code in cur.fetchall()}

    measure_cols = _POPULATION_FINE_COLS + _POPULATION_COARSE_COLS + [
        "pop_male", "pop_female", "pop_total", "pop_age_known", "pop_unknown_age",
    ]
    with silver_conn.cursor() as scur:
        scur.execute(
            f"SELECT unit_code, year_ce, data_source, {', '.join(measure_cols)} "
            f"FROM dopa_population_by_unit_year"
        )
        rows_in = scur.fetchall()

    rows = []
    skipped = 0
    for rec in rows_in:
        unit_code, year_ce, data_source = rec[0], rec[1], rec[2]
        area_key = area_lookup.get(unit_code)
        if area_key is None:
            skipped += 1
            continue
        rows.append((area_key, year_ce, data_source, *rec[3:]))

    insert_sql = (
        "INSERT INTO fact_population_by_area (area_key, date_key, data_source, "
        + ", ".join(measure_cols) + ") VALUES (" + ", ".join(["%s"] * (3 + len(measure_cols))) + ")"
    )
    with gold_conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    gold_conn.commit()

    if skipped:
        print(f"[gold_fact_extended] WARNING: fact_population_by_area: {skipped} row(s) had no matching dim_area.unit_code")
    print(f"[gold_fact_extended] fact_population_by_area: {len(rows)} rows")


def _build_fact_migrant_worker_permit(silver_conn, gold_conn):
    """Grain: (zone, date_key, report_month_num, permit_category,
    nationality) -- date_key/month resolved per ROW, not once globally,
    since silver now carries multiple report periods at once (one DOE PDF
    per month, up to the ~20-month history window ingest_api_doe_migrant_
    worker.py walks -- see that module's HISTORY note) and zone_id now also
    covers Samut Prakan/Chachoengsao's province-level rows (zone_id 11/24),
    not just BMA's 10 Bangkok zones -- see transform_silver_doe_migrant_
    worker.py's PROVINCE_ZONE_ID and this file's _build_dim_bma_zone()."""
    with silver_conn.cursor() as scur:
        scur.execute(
            "SELECT zone_id, report_year_ce, report_month_num, permit_category, nationality, total, male, female "
            "FROM doe_migrant_worker_permit_monthly"
        )
        silver_rows = scur.fetchall()

    if not silver_rows:
        print("[gold_fact_extended] fact_migrant_worker_permit: silver.doe_migrant_worker_permit_monthly is empty, skipping")
        return

    years_needed = {r[1] for r in silver_rows}
    with gold_conn.cursor() as cur:
        cur.execute("SELECT zone_key, zone_id FROM dim_bma_zone")
        zone_lookup = {zid: zkey for zkey, zid in cur.fetchall()}
        cur.execute(
            f"SELECT year_ce, date_key FROM dim_date WHERE year_ce IN ({','.join(['%s'] * len(years_needed))})",
            tuple(years_needed),
        )
        date_key_by_year = dict(cur.fetchall())
    missing_years = years_needed - set(date_key_by_year)
    if missing_years:
        raise RuntimeError(f"fact_migrant_worker_permit: dim_date has no row for year_ce in {sorted(missing_years)}")

    rows, skipped_zone = [], 0
    for zone_id, year_ce, month_num, category, nationality, total, male, female in silver_rows:
        zone_key = zone_lookup.get(zone_id)
        if zone_key is None:
            skipped_zone += 1
            continue
        rows.append((zone_key, date_key_by_year[year_ce], month_num, category, nationality, total, male, female))
    if skipped_zone:
        print(f"[gold_fact_extended] WARNING: fact_migrant_worker_permit: {skipped_zone} row(s) had a "
              f"zone_id not in dim_bma_zone, skipped")

    insert_sql = (
        "INSERT INTO fact_migrant_worker_permit "
        "(zone_key, date_key, report_month_num, permit_category, nationality, total, male, female) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    with gold_conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    gold_conn.commit()
    print(f"[gold_fact_extended] fact_migrant_worker_permit: {len(rows)} rows across {len(years_needed)} year(s)")


def run() -> None:
    silver_conn = _connect("silver")
    gold_conn = _connect("gold")

    _build_fact_hdc_weekly(silver_conn, gold_conn)
    _build_fact_hospital_access(silver_conn, gold_conn)
    _build_fact_population_by_area(silver_conn, gold_conn)
    _build_fact_migrant_worker_permit(silver_conn, gold_conn)

    silver_conn.close()
    gold_conn.close()


if __name__ == "__main__":
    run()

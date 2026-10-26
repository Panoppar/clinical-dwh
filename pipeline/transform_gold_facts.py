"""Builds gold's fact tables from silver.api_* (+ bronze.api_hdc_report_catalog
for dim_hdc_report lookups). Must run after transform_gold_dimensions.py.

fact_hdc_observation pivots Silver's EAV rows (one row per report x year x
zone x record x field) into one row per (report, year, zone, record),
with target/result/F3/male/female/total promoted to named columns -- the
headline fields the KPI tree's Health pillar needs (K-HLT-03/04). Every
other field_name silver carries stays in Silver only, not duplicated here.

fact_hdc_weekly_observation (kmch-ml input-parity gap 2) does the same
EAV-source pattern for the 4 PM2.5-linked weekly reports, but normalizes
(not wide-pivots) the w_NN_variant field-name pattern instead -- see
sql/gold/05_create_gold_hdc_weekly_facts.sql for why a literal 200+-column
pivot isn't the right shape here.
"""

import os
import re
from collections import defaultdict

import pymysql

# DDS's province_code is numeric (its own scheme, not a text name) --
# same mapping as ingest_api_dds.py's DDS_PROVINCE_NAMES.
DDS_PROVINCE_NAMES = {"10": "กรุงเทพมหานคร", "11": "สมุทรปราการ", "24": "ฉะเชิงเทรา"}

# field_name -> fact_hdc_observation column, for the headline fields the
# dashboard design actually uses (K-HLT-03/04). Every other field_name is
# dropped from this pivot (still available in silver.api_hdc_observations).
HDC_HEADLINE_FIELDS = {"target": "target", "result": "result", "F3": "f3_rate",
                        "male": "male", "female": "female", "total": "total"}

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


def _load_geo_lookup(gold_conn):
    """-> {(province, district_or_None, subdistrict_or_None): geo_key}"""
    lookup = {}
    with gold_conn.cursor() as cur:
        cur.execute("SELECT geo_key, province_name, district_name, subdistrict_name FROM dim_geography")
        for geo_key, province, district, subdistrict in cur.fetchall():
            lookup[(province, district, subdistrict)] = geo_key
    return lookup


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


def _build_fact_income(silver_conn, gold_conn, geo_lookup):
    insert_sql = (
        "INSERT INTO fact_income (geo_key, date_key, source_income1, source_income2, source_income3, "
        "soc_eco_class1, soc_eco_class2, income_value) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    rows = []
    with silver_conn.cursor() as scur:
        scur.execute(
            "SELECT province, year_ce, source_income1, source_income2, source_income3, "
            "soc_eco_class1, soc_eco_class2, value FROM api_nso_income"
        )
        for province, year_ce, si1, si2, si3, sec1, sec2, value in scur:
            geo_key = geo_lookup.get((province, None, None))
            if geo_key is None or year_ce is None:
                continue
            rows.append((geo_key, year_ce, si1, si2, si3, sec1, sec2, value))

    with gold_conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    gold_conn.commit()
    print(f"[gold_fact] fact_income: {len(rows)} rows")


def _build_fact_factory(silver_conn, gold_conn, geo_lookup):
    with gold_conn.cursor() as cur:
        cur.execute("SELECT industry_key, tsic_code, factory_type_code FROM dim_industry")
        industry_lookup = {(tsic, ftc): key for key, tsic, ftc in cur.fetchall()}

    insert_sql = (
        "INSERT INTO fact_factory (geo_key, industry_key, reg_no, factory_name, capital, workers, horsepower) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)"
    )
    rows = []
    with silver_conn.cursor() as scur:
        scur.execute(
            "SELECT province, amphoe, reg_no, factory_name, capital, workers, horsepower, tsic, factory_type_code "
            "FROM api_diw_factory"
        )
        for province, amphoe, reg_no, name, capital, workers, hp, tsic, ftc in scur:
            geo_key = geo_lookup.get((province, amphoe, None)) or geo_lookup.get((province, None, None))
            if geo_key is None:
                continue
            industry_key = industry_lookup.get((tsic, ftc))
            rows.append((geo_key, industry_key, reg_no, name, capital, workers, hp))

    with gold_conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    gold_conn.commit()
    print(f"[gold_fact] fact_factory: {len(rows)} rows")


def _build_fact_community_population(silver_conn, gold_conn, geo_lookup):
    insert_sql = (
        "INSERT INTO fact_community_population (geo_key, date_key, name_of_community, type_of_community, "
        "population, male, female) VALUES (%s,%s,%s,%s,%s,%s,%s)"
    )
    rows = []
    with silver_conn.cursor() as scur:
        scur.execute(
            "SELECT district, subdistrict, fiscal_year_ce, name_of_community, type_of_community, "
            "population, male, female FROM api_bma_community"
        )
        for district, subdistrict, fy, name, type_c, pop, male, female in scur:
            geo_key = (geo_lookup.get(("กรุงเทพมหานคร", district, subdistrict))
                       or geo_lookup.get(("กรุงเทพมหานคร", district, None)))
            if geo_key is None or fy is None:
                continue
            rows.append((geo_key, fy, name, type_c, pop, male, female))

    with gold_conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    gold_conn.commit()
    print(f"[gold_fact] fact_community_population: {len(rows)} rows")


def _build_fact_disease_ranking(silver_conn, gold_conn, geo_lookup):
    with gold_conn.cursor() as cur:
        cur.execute("SELECT disease_key, disease_name FROM dim_disease")
        disease_lookup = {name: key for key, name in cur.fetchall()}

    insert_sql = (
        "INSERT INTO fact_disease_ranking (geo_key, date_key, disease_key, `rank`, case_count, rate_per_100k, "
        "ipd_count, death_count, case_fatality_pct) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    rows = []
    with silver_conn.cursor() as scur:
        scur.execute(
            "SELECT province_code, year_ce, disease_name, `rank`, case_count, rate_per_100k, "
            "ipd_count, death_count, case_fatality_pct FROM api_dds_disease_ranking"
        )
        for province_code, year_ce, disease_name, rank, case_count, rate, ipd, death, cfp in scur:
            province_name = DDS_PROVINCE_NAMES.get(province_code)
            geo_key = geo_lookup.get((province_name, None, None)) if province_name else None
            disease_key = disease_lookup.get(disease_name)
            if geo_key is None or disease_key is None or year_ce is None:
                continue
            rows.append((geo_key, year_ce, disease_key, rank, case_count, rate, ipd, death, cfp))

    with gold_conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    gold_conn.commit()
    print(f"[gold_fact] fact_disease_ranking: {len(rows)} rows"
          + (" (0 expected -- DDS backend down)" if not rows else ""))


def _build_fact_hdc_observation(silver_conn, gold_conn, geo_lookup):
    with gold_conn.cursor() as cur:
        cur.execute("SELECT report_key, report_code FROM dim_hdc_report")
        report_lookup = {code: key for key, code in cur.fetchall()}

    # Group EAV rows by (report_code, year_ce, zone, record_index) into one
    # record dict each, streaming to keep memory bounded on 163K+ rows.
    records: dict[tuple, dict] = defaultdict(dict)
    with silver_conn.cursor(pymysql.cursors.SSCursor) as scur:
        scur.execute(
            "SELECT report_code, year_ce, zone, record_index, field_name, field_value FROM api_hdc_observations"
        )
        for report_code, year_ce, zone, record_index, field_name, field_value in scur:
            key = (report_code, year_ce, zone, record_index)
            if field_name == "a_name":
                records[key]["area_name_raw"] = field_value
            elif field_name in HDC_HEADLINE_FIELDS:
                records[key][HDC_HEADLINE_FIELDS[field_name]] = _to_decimal(field_value)

    insert_sql = (
        "INSERT INTO fact_hdc_observation (report_key, date_key, zone, record_index, geo_key, area_name_raw, "
        "target, result, f3_rate, male, female, total) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    rows = []
    for (report_code, year_ce, zone, record_index), fields in records.items():
        report_key = report_lookup.get(report_code)
        if report_key is None or year_ce is None:
            continue
        area_name = fields.get("area_name_raw")
        geo_key = geo_lookup.get((area_name, None, None)) if area_name else None
        rows.append((
            report_key, year_ce, zone, record_index, geo_key, area_name,
            fields.get("target"), fields.get("result"), fields.get("f3_rate"),
            fields.get("male"), fields.get("female"), fields.get("total"),
        ))

    with gold_conn.cursor() as cur:
        BATCH = 5000
        for i in range(0, len(rows), BATCH):
            cur.executemany(insert_sql, rows[i:i + BATCH])
    gold_conn.commit()
    print(f"[gold_fact] fact_hdc_observation: {len(rows)} rows "
          f"(pivoted from {sum(1 for _ in records)} distinct report/year/zone/record groups)")


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
    print(f"[gold_fact] fact_hdc_weekly_observation: {len(rows)} rows")


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
    print(f"[gold_fact] fact_hospital_access: {len(rows)} rows")


def run() -> None:
    silver_conn = _connect("silver")
    gold_conn = _connect("gold")
    geo_lookup = _load_geo_lookup(gold_conn)

    _build_fact_income(silver_conn, gold_conn, geo_lookup)
    _build_fact_factory(silver_conn, gold_conn, geo_lookup)
    _build_fact_community_population(silver_conn, gold_conn, geo_lookup)
    _build_fact_disease_ranking(silver_conn, gold_conn, geo_lookup)
    _build_fact_hdc_observation(silver_conn, gold_conn, geo_lookup)
    _build_fact_hdc_weekly(silver_conn, gold_conn)
    _build_fact_hospital_access(silver_conn, gold_conn)

    silver_conn.close()
    gold_conn.close()


if __name__ == "__main__":
    run()

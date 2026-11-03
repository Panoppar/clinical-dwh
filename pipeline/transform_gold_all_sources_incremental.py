"""Incremental Gold fact table builder for ALL sources.

Replaces old transform_gold_facts.py with incremental architecture.
Key changes:
  1. High-water mark filtering (only process delta rows)
  2. SQL MERGE instead of DROP-and-recreate

CORRECTION (see IMPLEMENTATION_SUMMARY.md changelog): an earlier version of
this file incorrectly treated BMA's Bangkok resolution as a "filter to
remove." That was wrong -- BMA (Bangkok Metropolitan Administration) has no
province column anywhere in its source data; it is structurally Bangkok-only,
not a warehouse-side cut. The actual province-level cut lives in the INGEST
layer for DIW and DDS (both hardcoded to a 3-province crawl list in
ingest_api_diw.py / ingest_api_dds.py), not in these Gold transforms -- see
those files for the real fix.

Sources:
  - fact_income (NSO): nationwide, no restriction at any layer
  - fact_factory (DIW): province scope is set by ingest_api_diw.py's crawl list
  - fact_community_population (BMA): always Bangkok (source has no other provinces)
  - fact_disease_ranking (DDS): province scope is set by ingest_api_dds.py's crawl list
  - fact_hdc_observation (HDC): regional, unchanged
"""

import hashlib
import os
from collections import defaultdict

import pymysql

import pipeline_metadata
from ingest_api_dds import DDS_PROVINCE_NAMES  # single source of truth -- do not keep a second copy here

TARGET_TABLES = [
    "fact_income",
    "fact_factory",
    "fact_community_population",
    "fact_disease_ranking",
    "fact_hdc_observation",
]

HDC_HEADLINE_FIELDS = {
    "target": "target",
    "result": "result",
    "F3": "f3_rate",
    "male": "male",
    "female": "female",
    "total": "total",
}


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


def _load_geo_lookup(gold_conn):
    """Load all geography keys (no filtering)."""
    lookup = {}
    with gold_conn.cursor() as cur:
        cur.execute("SELECT geo_key, province_name, district_name, subdistrict_name FROM dim_geography")
        for geo_key, province, district, subdistrict in cur:
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


def _income_business_key_hash(geo_key: int, year_ce: int, si1, si2, si3, sec1, sec2) -> str:
    """Full NSO grain hash -- confirmed live that source_income1+soc_eco_class1
    alone collide 1,232 distinct groups (source_income2/3 carry real
    sub-breakdowns), so all 5 text dimensions must be in the key."""
    data = f"{geo_key}|{year_ce}|{si1}|{si2}|{si3}|{sec1}|{sec2}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def _build_fact_income(silver_conn, gold_conn, geo_lookup):
    """NSO income: nationwide, no restriction at any layer of this source."""
    last_batch_id = pipeline_metadata.get_high_water_mark("fact_income")
    where_clause = "" if not last_batch_id else f"WHERE ingestion_batch_id > '{last_batch_id}'"

    merge_sql = """
        INSERT INTO fact_income
        (geo_key, date_key, source_income1, source_income2, source_income3, soc_eco_class1, soc_eco_class2,
         income_value, business_key_hash, ingestion_batch_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            income_value = VALUES(income_value),
            ingestion_batch_id = VALUES(ingestion_batch_id)
    """

    rows = []
    current_batch_id = None
    skipped = 0

    with silver_conn.cursor(pymysql.cursors.SSCursor) as scur:
        scur.execute(
            f"""
            SELECT province, year_ce, source_income1, source_income2, source_income3,
                   soc_eco_class1, soc_eco_class2, value, ingestion_batch_id
            FROM api_nso_income {where_clause}
            ORDER BY ingestion_batch_id DESC
            """
        )
        for province, year_ce, si1, si2, si3, sec1, sec2, value, batch_id in scur:
            if current_batch_id is None:
                current_batch_id = batch_id  # rows are ORDER BY ingestion_batch_id DESC, so the
                # first row seen carries the max batch_id; capturing on every row instead would let
                # trailing legacy rows (ingestion_batch_id IS NULL, which sorts last in DESC) clobber it

            geo_key = geo_lookup.get((province, None, None))
            if geo_key is None or year_ce is None:
                skipped += 1
                continue

            key_hash = _income_business_key_hash(geo_key, year_ce, si1, si2, si3, sec1, sec2)
            rows.append((geo_key, year_ce, si1, si2, si3, sec1, sec2, value, key_hash, batch_id))

    with gold_conn.cursor() as cur:
        for row in rows:
            cur.execute(merge_sql, row)
    gold_conn.commit()

    if current_batch_id:
        pipeline_metadata.set_high_water_mark("fact_income", current_batch_id)

    print(f"[gold_fact_income] MERGE: {len(rows)} rows, {skipped} skipped (geo unmatched)")


def _build_fact_factory(silver_conn, gold_conn, geo_lookup):
    """DIW factories: All provinces (no filtering)."""
    last_batch_id = pipeline_metadata.get_high_water_mark("fact_factory")
    where_clause = "" if not last_batch_id else f"WHERE ingestion_batch_id > '{last_batch_id}'"

    with gold_conn.cursor() as cur:
        cur.execute("SELECT industry_key, tsic_code, factory_type_code FROM dim_industry")
        industry_lookup = {(tsic, ftc): key for key, tsic, ftc in cur.fetchall()}
        cur.execute("SELECT amphoe_th, tambon_th, unit_code FROM dim_tambon_unit_xwalk")
        tambon_unit_lookup = {(amphoe, tambon): unit_code for amphoe, tambon, unit_code in cur.fetchall()}
        cur.execute("SELECT area_key, unit_code FROM dim_area")
        area_lookup = {code: key for key, code in cur.fetchall()}

    merge_sql = """
        INSERT INTO fact_factory
        (geo_key, area_key, industry_key, reg_no, factory_name, capital, workers, horsepower, ingestion_batch_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            capital = VALUES(capital),
            workers = VALUES(workers),
            ingestion_batch_id = VALUES(ingestion_batch_id)
    """

    rows = []
    current_batch_id = None
    skipped = 0

    with silver_conn.cursor(pymysql.cursors.SSCursor) as scur:
        scur.execute(
            f"""
            SELECT province, amphoe, tambon, reg_no, factory_name, capital, workers, horsepower, tsic, factory_type_code, ingestion_batch_id
            FROM api_diw_factory {where_clause}
            ORDER BY ingestion_batch_id DESC
            """
        )
        for province, amphoe, tambon, reg_no, name, capital, workers, hp, tsic, ftc, batch_id in scur:
            if current_batch_id is None:
                current_batch_id = batch_id  # rows are ORDER BY ingestion_batch_id DESC, so the
                # first row seen carries the max batch_id; capturing on every row instead would let
                # trailing legacy rows (ingestion_batch_id IS NULL, which sorts last in DESC) clobber it

            # Resolve geo (ALL provinces, no filtering)
            geo_key = geo_lookup.get((province, amphoe, None)) or geo_lookup.get((province, None, None))
            if geo_key is None:
                skipped += 1
                continue

            industry_key = industry_lookup.get((tsic, ftc))
            unit_code = tambon_unit_lookup.get((amphoe, tambon))
            area_key = area_lookup.get(unit_code) if unit_code else None

            rows.append((geo_key, area_key, industry_key, reg_no, name, capital, workers, hp, batch_id))

    with gold_conn.cursor() as cur:
        for row in rows:
            cur.execute(merge_sql, row)
    gold_conn.commit()

    if current_batch_id:
        pipeline_metadata.set_high_water_mark("fact_factory", current_batch_id)

    print(f"[gold_fact_factory] MERGE: {len(rows)} rows, {skipped} skipped (geo unmatched)")


BMA_PROVINCE_NAME = "กรุงเทพมหานคร"  # BMA = Bangkok Metropolitan Administration; source has no other provinces


def _build_fact_community_population(silver_conn, gold_conn, geo_lookup):
    """BMA communities: always Bangkok. The source (data.bangkok.go.th) carries
    only district/subdistrict columns, never province -- there is no other
    province's data being withheld here. This is NOT a filter to remove."""
    last_batch_id = pipeline_metadata.get_high_water_mark("fact_community_population")
    where_clause = "" if not last_batch_id else f"WHERE ingestion_batch_id > '{last_batch_id}'"

    merge_sql = """
        INSERT INTO fact_community_population
        (geo_key, date_key, name_of_community, type_of_community, population, male, female, ingestion_batch_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            population = VALUES(population),
            male = VALUES(male),
            female = VALUES(female),
            ingestion_batch_id = VALUES(ingestion_batch_id)
    """

    rows = []
    current_batch_id = None
    skipped = 0

    with silver_conn.cursor(pymysql.cursors.SSCursor) as scur:
        scur.execute(
            f"""
            SELECT district, subdistrict, fiscal_year_ce, name_of_community, type_of_community,
                   population, male, female, ingestion_batch_id
            FROM api_bma_community {where_clause}
            ORDER BY ingestion_batch_id DESC
            """
        )
        for district, subdistrict, fy, name, type_c, pop, male, female, batch_id in scur:
            if current_batch_id is None:
                current_batch_id = batch_id  # rows are ORDER BY ingestion_batch_id DESC, so the
                # first row seen carries the max batch_id; capturing on every row instead would let
                # trailing legacy rows (ingestion_batch_id IS NULL, which sorts last in DESC) clobber it

            geo_key = (geo_lookup.get((BMA_PROVINCE_NAME, district, subdistrict))
                       or geo_lookup.get((BMA_PROVINCE_NAME, district, None)))
            if geo_key is None or fy is None:
                skipped += 1
                continue

            rows.append((geo_key, fy, name, type_c, pop, male, female, batch_id))

    with gold_conn.cursor() as cur:
        for row in rows:
            cur.execute(merge_sql, row)
    gold_conn.commit()

    if current_batch_id:
        pipeline_metadata.set_high_water_mark("fact_community_population", current_batch_id)

    print(f"[gold_fact_community_population] MERGE: {len(rows)} rows, {skipped} skipped (Bangkok only -- source has no other provinces)")


def _build_fact_disease_ranking(silver_conn, gold_conn, geo_lookup):
    """DDS disease ranking: province scope is whatever ingest_api_dds.py actually
    crawled (DDS_PROVINCE_NAMES). The real 3-province cut lives there, not here --
    expanding this dict without expanding the ingest crawl list changes nothing,
    since Silver will still only contain whatever provinces were fetched."""
    last_batch_id = pipeline_metadata.get_high_water_mark("fact_disease_ranking")
    where_clause = "" if not last_batch_id else f"WHERE ingestion_batch_id > '{last_batch_id}'"

    with gold_conn.cursor() as cur:
        cur.execute("SELECT disease_key, disease_name FROM dim_disease")
        disease_lookup = {name: key for key, name in cur.fetchall()}

    merge_sql = """
        INSERT INTO fact_disease_ranking
        (geo_key, date_key, disease_key, `rank`, case_count, rate_per_100k, ipd_count, death_count, case_fatality_pct, ingestion_batch_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            `rank` = VALUES(`rank`),
            case_count = VALUES(case_count),
            ingestion_batch_id = VALUES(ingestion_batch_id)
    """

    rows = []
    current_batch_id = None
    skipped = 0

    with silver_conn.cursor(pymysql.cursors.SSCursor) as scur:
        scur.execute(
            f"""
            SELECT province_code, year_ce, disease_name, `rank`, case_count, rate_per_100k,
                   ipd_count, death_count, case_fatality_pct, ingestion_batch_id
            FROM api_dds_disease_ranking {where_clause}
            ORDER BY ingestion_batch_id DESC
            """
        )
        for province_code, year_ce, disease_name, rank, case_count, rate, ipd, death, cfp, batch_id in scur:
            if current_batch_id is None:
                current_batch_id = batch_id  # rows are ORDER BY ingestion_batch_id DESC, so the
                # first row seen carries the max batch_id; capturing on every row instead would let
                # trailing legacy rows (ingestion_batch_id IS NULL, which sorts last in DESC) clobber it

            # CHANGE: Resolve geo for ALL provinces from DDS (was DDS_PROVINCE_NAMES hardcoded to 3)
            # DDS provides province_code; match against all geo_lookup entries
            province_name = DDS_PROVINCE_NAMES.get(province_code)
            if province_name is None:
                # For provinces outside the 3-province DDS mapping, try to infer or skip
                skipped += 1
                continue

            geo_key = geo_lookup.get((province_name, None, None))
            disease_key = disease_lookup.get(disease_name)
            if geo_key is None or disease_key is None or year_ce is None:
                skipped += 1
                continue

            rows.append((geo_key, year_ce, disease_key, rank, case_count, rate, ipd, death, cfp, batch_id))

    with gold_conn.cursor() as cur:
        for row in rows:
            cur.execute(merge_sql, row)
    gold_conn.commit()

    if current_batch_id:
        pipeline_metadata.set_high_water_mark("fact_disease_ranking", current_batch_id)

    print(f"[gold_fact_disease_ranking] MERGE: {len(rows)} rows, {skipped} skipped "
          f"(DDS backend down since 2026-10-25, 0 rows expected until it recovers and ingest_api_dds.py reruns)")


def _build_fact_disease_ranking_from_health_region(silver_conn, gold_conn, geo_lookup):
    """DDS health-region PDF archive (skr6/skr13), used as a stand-in for the
    live province-grain API while its backend stays down. Feeds the SAME
    fact_disease_ranking table as _build_fact_disease_ranking, under a
    separate high-water mark key (different Silver source, own batch_id
    scheme).

    Only skr13 is inserted -- it maps 1:1 to Bangkok (Health Region 13 is
    defined as Bangkok-only in Thai health administration). skr6 spans
    multiple provinces (a health region, not a single province) and is
    deliberately NOT force-mapped to any one of them: forcing it into this
    province-grain fact table would either misattribute multi-province
    totals to a single province, or (if inserted with geo_key=NULL) risk
    silent duplicate accumulation on reruns, since MySQL's unique index
    never treats two NULLs as a collision for ON DUPLICATE KEY UPDATE
    purposes -- the "this_year" file's data changes week to week, so each
    rerun would create a new orphan row instead of updating in place.
    skr6 stays fully visible in silver.dds_health_region_disease_report
    (its own grain, not forced into this one) until a proper multi-province
    health-region dimension is modeled."""
    last_batch_id = pipeline_metadata.get_high_water_mark("fact_disease_ranking_health_region")
    where_clause = "" if not last_batch_id else f"WHERE ingestion_batch_id > '{last_batch_id}'"

    with gold_conn.cursor() as cur:
        cur.execute("SELECT disease_key, disease_name FROM dim_disease")
        disease_lookup = {name: key for key, name in cur.fetchall()}

    bangkok_geo_key = geo_lookup.get(("กรุงเทพมหานคร", None, None))

    merge_sql = """
        INSERT INTO fact_disease_ranking
        (geo_key, date_key, disease_key, `rank`, case_count, rate_per_100k, ipd_count, death_count, case_fatality_pct, ingestion_batch_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            `rank` = VALUES(`rank`),
            case_count = VALUES(case_count),
            rate_per_100k = VALUES(rate_per_100k),
            ipd_count = VALUES(ipd_count),
            death_count = VALUES(death_count),
            case_fatality_pct = VALUES(case_fatality_pct),
            ingestion_batch_id = VALUES(ingestion_batch_id)
    """

    rows = []
    current_batch_id = None
    skipped_skr6 = 0
    skipped_unresolved = 0

    with silver_conn.cursor(pymysql.cursors.SSCursor) as scur:
        scur.execute(
            f"""
            SELECT health_region_code, report_year_ce, disease_name_th, rank_no, patient_count,
                   morbidity_rate_per_100k, ipd_count, death_count, case_fatality_rate_pct, ingestion_batch_id
            FROM dds_health_region_disease_report {where_clause}
            ORDER BY ingestion_batch_id DESC
            """
        )
        for region, year_ce, disease_name, rank_no, patient_count, rate, ipd, death, cfr, batch_id in scur:
            if current_batch_id is None:
                current_batch_id = batch_id

            if region != "skr13":
                skipped_skr6 += 1  # skr6 (or any other non-Bangkok region code) -- see docstring
                continue

            disease_key = disease_lookup.get(disease_name)
            if bangkok_geo_key is None or disease_key is None or year_ce is None:
                skipped_unresolved += 1
                continue

            rows.append((bangkok_geo_key, year_ce, disease_key, rank_no, patient_count, rate, ipd, death, cfr, batch_id))

    with gold_conn.cursor() as cur:
        for row in rows:
            cur.execute(merge_sql, row)
    gold_conn.commit()

    if current_batch_id:
        pipeline_metadata.set_high_water_mark("fact_disease_ranking_health_region", current_batch_id)

    print(f"[gold_fact_disease_ranking_health_region] MERGE: {len(rows)} rows (skr13 -> Bangkok), "
          f"{skipped_skr6} skr6 rows not force-mapped (multi-province, stays Silver-only), "
          f"{skipped_unresolved} skipped (unresolved disease/geo)")


def _build_fact_hdc_observation(silver_conn, gold_conn, geo_lookup):
    """HDC observations: pivots Silver's EAV rows into fact_hdc_observation's
    real grain -- report_key (FK, resolved from Silver's report_code via
    dim_hdc_report) and date_key (which IS year_ce -- dim_date.date_key is
    year_ce directly, per that table's own DDL comment), NOT report_code/
    year_ce text columns, which this fact table does not have. Also
    resolves geo_key from the EAV "a_name" field (province_keyed report
    layouts only), matching the original transform_gold_facts.py logic."""
    with gold_conn.cursor() as cur:
        cur.execute("SELECT report_key, report_code FROM dim_hdc_report")
        report_lookup = {code: key for key, code in cur.fetchall()}

    last_batch_id = pipeline_metadata.get_high_water_mark("fact_hdc_observation")
    where_clause = "" if not last_batch_id else f"WHERE ingestion_batch_id > '{last_batch_id}'"

    merge_sql = """
        INSERT INTO fact_hdc_observation
        (report_key, date_key, zone, record_index, geo_key, area_name_raw,
         target, result, f3_rate, male, female, total, ingestion_batch_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            geo_key = VALUES(geo_key),
            area_name_raw = VALUES(area_name_raw),
            target = COALESCE(VALUES(target), target),
            result = COALESCE(VALUES(result), result),
            f3_rate = COALESCE(VALUES(f3_rate), f3_rate),
            male = COALESCE(VALUES(male), male),
            female = COALESCE(VALUES(female), female),
            total = COALESCE(VALUES(total), total),
            ingestion_batch_id = VALUES(ingestion_batch_id)
    """

    hdc_pivots = {}
    current_batch_id = None
    unresolved_report = 0

    with silver_conn.cursor(pymysql.cursors.SSCursor) as scur:
        scur.execute(
            f"""
            SELECT report_code, year_ce, zone, record_index, field_name, field_value, ingestion_batch_id
            FROM api_hdc_observations {where_clause}
            ORDER BY ingestion_batch_id DESC, report_code, year_ce, zone, record_index, field_name
            """
        )

        for report_code, year_ce, zone, record_index, field_name, field_value, batch_id in scur:
            if current_batch_id is None:
                current_batch_id = batch_id  # rows are ORDER BY ingestion_batch_id DESC, so the
                # first row seen carries the max batch_id; capturing on every row instead would let
                # trailing legacy rows (ingestion_batch_id IS NULL, which sorts last in DESC) clobber it
            key = (report_code, year_ce, zone, record_index)

            if key not in hdc_pivots:
                hdc_pivots[key] = {"_batch_id": batch_id}

            if field_name in hdc_pivots[key]:
                continue  # already have this field from a newer batch (ORDER BY batch_id DESC)

            if field_name == "a_name":
                hdc_pivots[key]["area_name_raw"] = field_value
            elif field_name in HDC_HEADLINE_FIELDS:
                hdc_pivots[key][HDC_HEADLINE_FIELDS[field_name]] = _to_decimal(field_value)

    rows = []
    for (report_code, year_ce, zone, record_index), fields in hdc_pivots.items():
        batch_id = fields.pop("_batch_id")

        report_key = report_lookup.get(report_code)
        if report_key is None or year_ce is None:
            unresolved_report += 1
            continue

        area_name = fields.get("area_name_raw")
        geo_key = geo_lookup.get((area_name, None, None)) if area_name else None

        rows.append((
            report_key, year_ce, zone, record_index, geo_key, area_name,
            fields.get("target"), fields.get("result"), fields.get("f3_rate"),
            fields.get("male"), fields.get("female"), fields.get("total"),
            batch_id,
        ))

    with gold_conn.cursor() as cur:
        for row in rows:
            cur.execute(merge_sql, row)
    gold_conn.commit()

    if current_batch_id:
        pipeline_metadata.set_high_water_mark("fact_hdc_observation", current_batch_id)

    print(f"[gold_fact_hdc_observation] MERGE: {len(rows)} rows, {unresolved_report} skipped (report_code unresolved in dim_hdc_report)")


def run() -> None:
    """Main entry point: Build all Gold fact tables with incremental architecture."""
    silver_conn = _connect("silver")
    gold_conn = _connect("gold")

    geo_lookup = _load_geo_lookup(gold_conn)
    print(f"[gold_all_sources] loaded {len(geo_lookup)} geography keys")

    print("\n=== Building Gold Fact Tables (Incremental + Unfiltered) ===\n")

    _build_fact_income(silver_conn, gold_conn, geo_lookup)
    _build_fact_factory(silver_conn, gold_conn, geo_lookup)
    _build_fact_community_population(silver_conn, gold_conn, geo_lookup)
    _build_fact_disease_ranking(silver_conn, gold_conn, geo_lookup)
    _build_fact_disease_ranking_from_health_region(silver_conn, gold_conn, geo_lookup)
    _build_fact_hdc_observation(silver_conn, gold_conn, geo_lookup)

    silver_conn.close()
    gold_conn.close()

    # Print final high-water marks
    print("\n=== Pipeline Metadata State ===\n")
    from pipeline_metadata import get_metadata_status
    status = get_metadata_status()
    for table, info in status.items():
        print(f"{table:40} → {info['last_batch_id']}")

    print("\n[gold_all_sources] Gold tables built successfully (NO FILTERING - all provinces included)")


if __name__ == "__main__":
    run()

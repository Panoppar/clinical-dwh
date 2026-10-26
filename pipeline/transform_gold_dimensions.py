"""Builds gold's 6 dimension tables from the live-API Silver/Bronze
sources. dim_geography is built purely from these sources' own text
labels (NSO/BMA/DIW all use plain geographic names) -- confirmed by direct
inspection that BMA's `district` and DIW's `amphoe` match exactly for
every Bangkok area checked, so a straight text union/match is safe here,
unlike the earlier DOPA-vs-kongvut mismatch this project hit before.

dim_area (kmch-ml input-parity gap 1) is a separate catchment-area
dimension, built from silver.geo_boundary_{subdistrict,district} --
see sql/gold/04_create_gold_area_dimension.sql for the full design note."""

import math
import os

import pymysql


def _connect(database):
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"], port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"], password=os.environ["DWH_DB_PASSWORD"],
        database=database, charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def _build_dim_date(silver_conn, gold_conn):
    years = set()
    with silver_conn.cursor() as cur:
        cur.execute("SELECT DISTINCT year_ce FROM api_nso_income")
        years |= {y for (y,) in cur.fetchall()}
        cur.execute("SELECT DISTINCT fiscal_year_ce FROM api_bma_community")
        years |= {y for (y,) in cur.fetchall()}
        cur.execute("SELECT DISTINCT year_ce FROM api_dds_disease_ranking")
        years |= {y for (y,) in cur.fetchall()}
        cur.execute("SELECT DISTINCT year_ce FROM api_hdc_observations")
        years |= {y for (y,) in cur.fetchall()}
    years.discard(None)

    with gold_conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO dim_date (date_key, year_ce, year_be) VALUES (%s,%s,%s)",
            [(y, y, y + 543) for y in sorted(years)],
        )
    gold_conn.commit()
    print(f"[gold_dim] dim_date: {len(years)} years ({min(years)}-{max(years)})")


def _admin_types(province: str) -> tuple[str, str]:
    """-> (district_type, subdistrict_type). Bangkok uses เขต/แขวง; every
    other province uses อำเภอ/ตำบล. Not readable off any source's raw text
    (BMA/DIW/NSO all carry bare names, confirmed by direct inspection) --
    derived from this well-known, fixed fact about Thai public
    administration, not inferred from the data."""
    if province == "กรุงเทพมหานคร":
        return "เขต", "แขวง"
    return "อำเภอ", "ตำบล"


def _build_dim_geography(silver_conn, gold_conn):
    province_key = {}   # province_name -> geo_key
    district_key = {}   # (province_name, district_name) -> geo_key

    def _get_or_create_province(cur, name, sources):
        if name in province_key:
            return province_key[name]
        cur.execute(
            "INSERT INTO dim_geography (admin_level, province_name, source_systems) VALUES ('province', %s, %s)",
            (name, sources),
        )
        province_key[name] = cur.lastrowid
        return province_key[name]

    def _get_or_create_district(cur, province, district, sources):
        k = (province, district)
        if k in district_key:
            return district_key[k]
        parent = province_key[province]
        district_type, _ = _admin_types(province)
        cur.execute(
            "INSERT INTO dim_geography (admin_level, province_name, district_name, district_type, "
            "parent_geo_key, source_systems) VALUES ('district', %s, %s, %s, %s, %s)",
            (province, district, district_type, parent, sources),
        )
        district_key[k] = cur.lastrowid
        return district_key[k]

    with gold_conn.cursor() as cur:
        # 1. Provinces: NSO (all 77) ∪ DIW (3) ∪ BMA (implicitly Bangkok only)
        with silver_conn.cursor() as scur:
            scur.execute("SELECT DISTINCT province FROM api_nso_income WHERE province IS NOT NULL AND province != ''")
            nso_provinces = {p for (p,) in scur.fetchall()}
            scur.execute("SELECT DISTINCT province FROM api_diw_factory WHERE province IS NOT NULL AND province != ''")
            diw_provinces = {p for (p,) in scur.fetchall()}
        for p in sorted(nso_provinces | diw_provinces | {"กรุงเทพมหานคร"}):
            sources = ",".join(s for s, has in [("NSO", p in nso_provinces), ("DIW", p in diw_provinces),
                                                  ("BMA", p == "กรุงเทพมหานคร")] if has)
            _get_or_create_province(cur, p, sources)

        # 2. Districts: BMA.district (province=Bangkok) ∪ DIW.(province, amphoe)
        with silver_conn.cursor() as scur:
            scur.execute("SELECT DISTINCT district FROM api_bma_community WHERE district IS NOT NULL AND district != ''")
            bma_districts = {d for (d,) in scur.fetchall()}
            scur.execute("SELECT DISTINCT province, amphoe FROM api_diw_factory WHERE amphoe IS NOT NULL AND amphoe != ''")
            diw_districts = {(p, d) for p, d in scur.fetchall()}
        for d in sorted(bma_districts):
            is_also_diw = ("กรุงเทพมหานคร", d) in diw_districts
            sources = "BMA,DIW" if is_also_diw else "BMA"
            _get_or_create_district(cur, "กรุงเทพมหานคร", d, sources)
        for p, d in sorted(diw_districts):
            if (p, d) not in district_key:
                _get_or_create_district(cur, p, d, "DIW")

        # 3. Subdistricts: BMA.(district, subdistrict) ∪ DIW.(province, amphoe, tambon)
        with silver_conn.cursor() as scur:
            scur.execute(
                "SELECT DISTINCT district, subdistrict FROM api_bma_community "
                "WHERE subdistrict IS NOT NULL AND subdistrict != ''"
            )
            bma_subdistricts = {(d, s) for d, s in scur.fetchall()}
            scur.execute(
                "SELECT DISTINCT province, amphoe, tambon FROM api_diw_factory "
                "WHERE tambon IS NOT NULL AND tambon != ''"
            )
            diw_subdistricts = {(p, a, t) for p, a, t in scur.fetchall()}

        subdistrict_seen = set()
        for district, subdistrict in sorted(bma_subdistricts):
            k = ("กรุงเทพมหานคร", district, subdistrict)
            parent = district_key.get(("กรุงเทพมหานคร", district))
            if parent is None:
                continue
            is_also_diw = ("กรุงเทพมหานคร", district, subdistrict) in diw_subdistricts
            sources = "BMA,DIW" if is_also_diw else "BMA"
            district_type, subdistrict_type = _admin_types("กรุงเทพมหานคร")
            cur.execute(
                "INSERT INTO dim_geography (admin_level, province_name, district_name, district_type, "
                "subdistrict_name, subdistrict_type, parent_geo_key, source_systems) "
                "VALUES ('subdistrict', %s, %s, %s, %s, %s, %s, %s)",
                ("กรุงเทพมหานคร", district, district_type, subdistrict, subdistrict_type, parent, sources),
            )
            subdistrict_seen.add(k)
        for province, amphoe, tambon in sorted(diw_subdistricts):
            k = (province, amphoe, tambon)
            if k in subdistrict_seen:
                continue
            parent = district_key.get((province, amphoe))
            if parent is None:
                continue
            district_type, subdistrict_type = _admin_types(province)
            cur.execute(
                "INSERT INTO dim_geography (admin_level, province_name, district_name, district_type, "
                "subdistrict_name, subdistrict_type, parent_geo_key, source_systems) "
                "VALUES ('subdistrict', %s, %s, %s, %s, %s, %s, 'DIW')",
                (province, amphoe, district_type, tambon, subdistrict_type, parent),
            )
            subdistrict_seen.add(k)

    gold_conn.commit()
    print(f"[gold_dim] dim_geography: {len(province_key)} provinces, {len(district_key)} districts, "
          f"{len(subdistrict_seen)} subdistricts")
    return province_key, district_key


def _build_dim_industry(silver_conn, gold_conn):
    with silver_conn.cursor() as scur:
        scur.execute(
            "SELECT DISTINCT tsic, factory_type_code FROM api_diw_factory "
            "WHERE tsic IS NOT NULL OR factory_type_code IS NOT NULL"
        )
        rows = scur.fetchall()
    with gold_conn.cursor() as cur:
        cur.executemany(
            "INSERT IGNORE INTO dim_industry (tsic_code, factory_type_code) VALUES (%s,%s)", rows,
        )
    gold_conn.commit()
    print(f"[gold_dim] dim_industry: {len(rows)} distinct (tsic, factory_type) combinations")


def _build_dim_hdc_report(bronze_conn, gold_conn):
    with bronze_conn.cursor() as bcur:
        bcur.execute(
            "SELECT raw_report_code, raw_report_name, raw_subcatalog_name, raw_byear_list FROM api_hdc_report_catalog"
        )
        rows = bcur.fetchall()
    with gold_conn.cursor() as cur:
        cur.executemany(
            "INSERT IGNORE INTO dim_hdc_report (report_code, report_name, subcatalog_name, years_available) "
            "VALUES (%s,%s,%s,%s)", rows,
        )
    gold_conn.commit()
    print(f"[gold_dim] dim_hdc_report: {len(rows)} reports")


def _build_dim_disease(silver_conn, gold_conn):
    with silver_conn.cursor() as scur:
        scur.execute("SELECT DISTINCT disease_name FROM api_dds_disease_ranking WHERE disease_name IS NOT NULL")
        rows = scur.fetchall()
    with gold_conn.cursor() as cur:
        cur.executemany("INSERT IGNORE INTO dim_disease (disease_name) VALUES (%s)", rows)
    gold_conn.commit()
    print(f"[gold_dim] dim_disease: {len(rows)} diseases" + (" (0 expected -- DDS backend down)" if not rows else ""))


# kmch-ml's own hospital coordinate (Google Maps-verified, confirmed from
# kmch-ml's config.py) -- this warehouse's catchment work is specifically
# being built toward kmch-ml input parity, so reusing the exact constant
# is intentional, not a hardcoded guess.
KMCH_LAT, KMCH_LON = 13.732307519058327, 100.78967253963812
CATCHMENT_PROVINCE_NAMES = {"10": "กรุงเทพมหานคร", "11": "สมุทรปราการ", "24": "ฉะเชิงเทรา"}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088  # mean Earth radius, km
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _catchment_tier(dist_km: float, province_code: str) -> tuple[str, bool]:
    if dist_km <= 10:
        return "core", True
    if dist_km <= 20:
        return "primary", True
    if dist_km <= 30:
        return "extended", True
    return ("bkk_other" if province_code == "10" else "province_other"), False


def _build_dim_area(silver_conn, gold_conn):
    """Grain: one row per catchment unit, normally a subdistrict. Bangkok's
    13 post-2019 khwaeng splits have no centroid in this snapshot (no
    matching polygon was generalized for them) -- those fall back to their
    parent district as a single coarser unit (kmch-ml's own documented
    handling: 13 splits -> 7 parent districts), flagged via
    is_district_level_fallback rather than silently dropped or guessed."""
    with silver_conn.cursor() as scur:
        scur.execute(
            "SELECT subdistrict_code, district_code, province_code, name_th, centroid_lat, centroid_lon "
            "FROM geo_boundary_subdistrict WHERE province_code IN ('10','11','24')"
        )
        subdistricts = scur.fetchall()
        scur.execute(
            "SELECT district_code, province_code, name_th, centroid_lat, centroid_lon "
            "FROM geo_boundary_district WHERE province_code IN ('10','11','24')"
        )
        district_by_code = {d[0]: d for d in scur.fetchall()}

    units = []  # (unit_code, unit_th, is_fallback, province_code, district_code, lat, lon)
    missing_by_district: dict[str, list] = {}
    for code, dcode, pcode, name_th, lat, lon in subdistricts:
        if lat is None or lon is None:
            missing_by_district.setdefault(dcode, []).append((code, name_th))
            continue
        units.append((code, name_th, False, pcode, dcode, float(lat), float(lon)))

    for dcode, missing in missing_by_district.items():
        d = district_by_code.get(dcode)
        if d is None or d[3] is None or d[4] is None:
            print(f"[gold_dim] WARNING: dim_area: district {dcode} has {len(missing)} subdistricts "
                  f"missing centroid data, and the district itself also lacks centroid data -- "
                  f"skipped entirely: {missing}")
            continue
        _, pcode, dname_th, dlat, dlon = d
        units.append((dcode, dname_th, True, pcode, dcode, float(dlat), float(dlon)))

    rows = []
    for unit_code, unit_th, is_fallback, pcode, dcode, lat, lon in units:
        d = district_by_code.get(dcode)
        amphoe_th = d[2] if d else unit_th
        dist = _haversine_km(lat, lon, KMCH_LAT, KMCH_LON)
        tier, is_catchment = _catchment_tier(dist, pcode)
        province_th = CATCHMENT_PROVINCE_NAMES.get(pcode, pcode)
        rows.append((unit_code, unit_th, int(is_fallback), pcode, province_th, dcode, amphoe_th,
                     lat, lon, round(dist, 3), tier, int(is_catchment)))

    insert_sql = (
        "INSERT INTO dim_area (unit_code, unit_th, is_district_level_fallback, province_code, province_th, "
        "amphoe_code, amphoe_th, centroid_lat, centroid_lon, dist_to_kmch_km, catchment_tier, is_catchment) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    with gold_conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    gold_conn.commit()

    tier_counts: dict[str, int] = {}
    for r in rows:
        tier_counts[r[10]] = tier_counts.get(r[10], 0) + 1
    fallback_count = sum(1 for r in rows if r[2])
    print(f"[gold_dim] dim_area: {len(rows)} units ({fallback_count} district-level fallback) -- tiers: {tier_counts}")


def _build_dim_facility(silver_conn, gold_conn):
    """Always seeds the fixed KMCH coordinate as destination_id='KMCH',
    regardless of whether OSM facility discovery has landed anything --
    see sql/gold/06 for why."""
    with gold_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO dim_facility (destination_id, name, lat, lon, is_kmch) VALUES ('KMCH', %s, %s, %s, 1)",
            ("KMCH (fixed hub coordinate)", KMCH_LAT, KMCH_LON),
        )
    with silver_conn.cursor() as scur:
        scur.execute("SELECT osm_type, osm_id, name, lat, lon FROM geo_hospital_facility")
        rows = [(f"{t}_{i}", name, lat, lon, 0) for t, i, name, lat, lon in scur.fetchall()]
    with gold_conn.cursor() as cur:
        cur.executemany(
            "INSERT IGNORE INTO dim_facility (destination_id, name, lat, lon, is_kmch) VALUES (%s,%s,%s,%s,%s)",
            rows,
        )
    gold_conn.commit()
    print(f"[gold_dim] dim_facility: 1 KMCH + {len(rows)} OSM-discovered facilities")


def run() -> None:
    silver_conn = _connect("silver")
    bronze_conn = _connect("bronze")
    gold_conn = _connect("gold")

    _build_dim_date(silver_conn, gold_conn)
    _build_dim_geography(silver_conn, gold_conn)
    _build_dim_industry(silver_conn, gold_conn)
    _build_dim_hdc_report(bronze_conn, gold_conn)
    _build_dim_disease(silver_conn, gold_conn)
    _build_dim_area(silver_conn, gold_conn)
    _build_dim_facility(silver_conn, gold_conn)

    silver_conn.close()
    bronze_conn.close()
    gold_conn.close()


if __name__ == "__main__":
    run()

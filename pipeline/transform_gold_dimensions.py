"""Builds gold's 5 dimension tables from the 5 live-API Silver/Bronze
sources. dim_geography is built purely from these sources' own text
labels (NSO/BMA/DIW all use plain geographic names) -- confirmed by direct
inspection that BMA's `district` and DIW's `amphoe` match exactly for
every Bangkok area checked, so a straight text union/match is safe here,
unlike the earlier DOPA-vs-kongvut mismatch this project hit before."""

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


def run() -> None:
    silver_conn = _connect("silver")
    bronze_conn = _connect("bronze")
    gold_conn = _connect("gold")

    _build_dim_date(silver_conn, gold_conn)
    _build_dim_geography(silver_conn, gold_conn)
    _build_dim_industry(silver_conn, gold_conn)
    _build_dim_hdc_report(bronze_conn, gold_conn)
    _build_dim_disease(silver_conn, gold_conn)

    silver_conn.close()
    bronze_conn.close()
    gold_conn.close()


if __name__ == "__main__":
    run()

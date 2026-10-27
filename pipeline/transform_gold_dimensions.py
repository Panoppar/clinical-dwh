"""Builds gold's 6 dimension tables from the live-API Silver/Bronze
sources. dim_geography is built purely from these sources' own text
labels (NSO/BMA/DIW all use plain geographic names) -- confirmed by direct
inspection that BMA's `district` and DIW's `amphoe` match exactly for
every Bangkok area checked, so a straight text union/match is safe here,
unlike the earlier DOPA-vs-kongvut mismatch this project hit before.

dim_area (kmch-ml input-parity gap 1) is a separate catchment-area
dimension, built from silver.geo_boundary_{subdistrict,district} --
see sql/gold/04_create_gold_area_dimension.sql for the full design note."""

import json
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
        cur.execute("SELECT DISTINCT year_ce FROM dopa_population_by_unit_year")
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


_EARTH_RADIUS_KM = 6371.0088  # same mean-Earth-radius constant as _haversine_km


def _point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    """Standard ray-casting point-in-polygon test, one GeoJSON ring
    (list of [lon, lat] pairs)."""
    inside = False
    n = len(ring)
    xj, yj = ring[-1][0], ring[-1][1]
    for xi, yi in ((pt[0], pt[1]) for pt in ring):
        if (yi > lat) != (yj > lat):
            x_at_lat = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < x_at_lat:
                inside = not inside
        xj, yj = xi, yi
    return inside


def _point_in_polygon_rings(lon: float, lat: float, rings: list) -> bool:
    """rings[0] is the exterior boundary, rings[1:] are holes (GeoJSON
    Polygon convention) -- inside the exterior AND not inside any hole."""
    if not rings or not _point_in_ring(lon, lat, rings[0]):
        return False
    return not any(_point_in_ring(lon, lat, hole) for hole in rings[1:])


def _point_in_geometry(lon: float, lat: float, geometry: dict) -> bool:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if gtype == "Polygon":
        return _point_in_polygon_rings(lon, lat, coords)
    if gtype == "MultiPolygon":
        return any(_point_in_polygon_rings(lon, lat, poly) for poly in coords)
    return False


def _ring_area_km2(ring: list[list[float]]) -> float:
    """Chamberlain & Duquette (JPL) spherical-polygon-area formula -- same
    spherical-Earth model as _haversine_km, so area and distance are
    derived consistently rather than mixing a planar area with a
    great-circle distance."""
    n = len(ring)
    if n < 3:
        return 0.0
    total = 0.0
    for i in range(n):
        lon_prev = ring[i - 1][0]
        lon_next = ring[(i + 1) % n][0]
        lat_i = ring[i][1]
        total += math.radians(lon_next - lon_prev) * math.sin(math.radians(lat_i))
    return abs(total) * _EARTH_RADIUS_KM ** 2 / 2.0


def _polygon_rings_area_km2(rings: list) -> float:
    if not rings:
        return 0.0
    area = _ring_area_km2(rings[0])
    for hole in rings[1:]:
        area -= _ring_area_km2(hole)
    return area


def _geometry_area_km2(geometry: dict) -> float:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if gtype == "Polygon":
        return _polygon_rings_area_km2(coords)
    if gtype == "MultiPolygon":
        return sum(_polygon_rings_area_km2(poly) for poly in coords)
    return 0.0


def _ring_centroid(ring: list[list[float]]) -> tuple[tuple[float, float] | None, float]:
    """Standard planar polygon-centroid (center of mass) formula --
    exterior ring only, same simplification already validated against a
    real feature (TH100905) to match this project's existing Silver
    centroid value to 5 decimal places. -> ((lon, lat), signed_area), or
    (None, 0.0) for a degenerate ring."""
    n = len(ring)
    a2 = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(n):
        x0, y0 = ring[i][0], ring[i][1]
        x1, y1 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        cross = x0 * y1 - x1 * y0
        a2 += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area = a2 / 2.0
    if area == 0:
        return None, 0.0
    return (cx / (6 * area), cy / (6 * area)), area


def _geometry_centroid(geometry: dict) -> tuple[float, float]:
    """-> (lon, lat), area-weighted across MultiPolygon parts. Holes are
    ignored here (unlike _geometry_area_km2, which subtracts them) --
    immaterial at subdistrict scale, and this project's polygons are
    simple exterior-only shapes in practice."""
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    parts = [coords[0]] if gtype == "Polygon" else [poly[0] for poly in coords] if gtype == "MultiPolygon" else []

    total_area = 0.0
    wx = 0.0
    wy = 0.0
    for ring in parts:
        c, area = _ring_centroid(ring)
        if c is None:
            continue
        a = abs(area)
        total_area += a
        wx += c[0] * a
        wy += c[1] * a
    if total_area == 0:
        raise ValueError("_geometry_centroid: no usable ring found")
    return wx / total_area, wy / total_area


def _load_boundary_polygons(bronze_conn) -> tuple[dict, dict]:
    """-> (polygons_by_subdistrict_code, polygons_by_district_code), both
    keyed by the bare TIS-1099 code (ADM_PCODE with its leading 'TH'
    stripped). bronze.geo_boundary_polygon is nationwide and unfiltered --
    see docs/06_kmch_ml_gap_closure_plan.md's Gap 6 note: this is the exact
    same file kmch-ml's own training export carries, already landed here,
    not a separate source."""
    with bronze_conn.cursor() as bcur:
        bcur.execute(
            "SELECT raw_adm3_pcode, raw_adm2_pcode, raw_geometry_geojson FROM geo_boundary_polygon"
        )
        rows = bcur.fetchall()

    by_subdistrict: dict[str, dict] = {}
    by_district: dict[str, list] = {}
    for adm3_pcode, adm2_pcode, geom_text in rows:
        if not geom_text:
            continue
        geometry = json.loads(geom_text)
        bare3 = (adm3_pcode or "").removeprefix("TH")
        bare2 = (adm2_pcode or "").removeprefix("TH")
        if bare3:
            by_subdistrict[bare3] = geometry
        if bare2:
            by_district.setdefault(bare2, []).append(geometry)
    return by_subdistrict, by_district


def _build_dim_area(bronze_conn, silver_conn, gold_conn):
    """Grain: one row per catchment unit. Units are grouped by
    bronze.tambon_xwalk's own unit_code (kmch-ml's authoritative mapping,
    see docs/06_kmch_ml_gap_closure_plan.md Gap 4) rather than a
    NULL-centroid heuristic -- an earlier version of this function
    approximated the grouping from missing centroid data alone, which
    wrongly left 5 of the 7 Bangkok post-2019 khwaeng-split groups'
    "anchor" tambon (e.g. 100905) as its own standalone unit instead of
    merged with its split sibling (100910), inflating the total from
    kmch-ml's documented 312 to 317. Confirmed fixed: every unit_code in
    the 3 catchment provinces resolves to exactly one polygon in
    bronze.geo_boundary_polygon (that source pre-dates the 2019 splits, so
    a merged group's polygon is simply its pre-split ancestor's own
    unsplit geometry -- there is never more than one polygon per group).

    centroid_lat/lon, area_km2, and contains_kmch_point are all derived
    from that single polygon via a consistent, unified method for every
    row (merged or not) -- not a mix of "Silver's stored point" for
    ordinary units and "something else" for merged ones."""
    polygons_by_subdistrict, _ = _load_boundary_polygons(bronze_conn)

    with bronze_conn.cursor() as bcur:
        bcur.execute(
            "SELECT raw_tambon_code, raw_unit_code, raw_amphoe_code, raw_amphoe_th, raw_province_code "
            "FROM tambon_xwalk WHERE raw_province_code IN ('10','11','24')"
        )
        xwalk_rows = bcur.fetchall()

    with silver_conn.cursor() as scur:
        scur.execute(
            "SELECT district_code, province_code, name_th, name_en FROM geo_boundary_district "
            "WHERE province_code IN ('10','11','24')"
        )
        district_by_code = {d[0]: d for d in scur.fetchall()}
        scur.execute("SELECT subdistrict_code, name_th FROM geo_boundary_subdistrict")
        tambon_name_by_code = dict(scur.fetchall())

    groups: dict[str, dict] = {}
    for tambon_code, unit_code, amphoe_code, amphoe_th, province_code in xwalk_rows:
        g = groups.setdefault(unit_code, {
            "members": [], "amphoe_code": amphoe_code, "amphoe_th": amphoe_th, "province_code": province_code,
        })
        g["members"].append(tambon_code)

    rows = []
    skipped = []
    for unit_code, g in groups.items():
        geometry = polygons_by_subdistrict.get(unit_code)
        if geometry is None:
            skipped.append(unit_code)
            continue

        members = g["members"]
        n_member = len(members)
        pcode = g["province_code"]
        amphoe_code = g["amphoe_code"]
        amphoe_th = g["amphoe_th"]
        d = district_by_code.get(amphoe_code)
        amphoe_en = d[3] if d else None

        lon, lat = _geometry_centroid(geometry)
        area_km2 = round(_geometry_area_km2(geometry), 3)
        contains_kmch_point = _point_in_geometry(KMCH_LON, KMCH_LAT, geometry)

        is_fallback = n_member > 1
        if is_fallback:
            unit_th = f"{amphoe_th} (รวม {n_member} แขวง)"
        else:
            unit_th = tambon_name_by_code.get(unit_code, amphoe_th)

        dist = _haversine_km(lat, lon, KMCH_LAT, KMCH_LON)
        tier, is_catchment = _catchment_tier(dist, pcode)
        province_th = CATCHMENT_PROVINCE_NAMES.get(pcode, pcode)

        rows.append((unit_code, unit_th, int(is_fallback), pcode, province_th, amphoe_code, amphoe_th, amphoe_en,
                     lat, lon, round(dist, 3), tier, int(is_catchment), area_km2, int(contains_kmch_point),
                     n_member, "|".join(members)))

    if skipped:
        print(f"[gold_dim] WARNING: dim_area: {len(skipped)} unit(s) have no matching polygon, skipped: {skipped}")

    insert_sql = (
        "INSERT INTO dim_area (unit_code, unit_th, is_district_level_fallback, province_code, province_th, "
        "amphoe_code, amphoe_th, amphoe_en, centroid_lat, centroid_lon, dist_to_kmch_km, catchment_tier, "
        "is_catchment, area_km2, contains_kmch_point, n_member, member_codes) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    with gold_conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    gold_conn.commit()

    tier_counts: dict[str, int] = {}
    for r in rows:
        tier_counts[r[11]] = tier_counts.get(r[11], 0) + 1
    fallback_count = sum(1 for r in rows if r[2])
    n_with_point = sum(1 for r in rows if r[14])
    print(f"[gold_dim] dim_area: {len(rows)} units ({fallback_count} merged multi-tambon groups) -- tiers: {tier_counts}")
    print(f"[gold_dim] dim_area: {n_with_point} unit(s) contain the KMCH point "
          f"(expect exactly 1 -- unit 101104 per kmch-ml's own reference export)")


def _build_dim_tambon_unit_xwalk(bronze_conn, gold_conn):
    """Grain: one row per original TIS-1099 tambon code -- finer than
    dim_area's merged-unit grain. Must run after _build_dim_area() (FK
    dependency on dim_area.unit_code)."""
    with bronze_conn.cursor() as bcur:
        bcur.execute(
            "SELECT raw_tambon_code, raw_tambon_th, raw_tambon_en, raw_amphoe_code, raw_amphoe_th, "
            "raw_postal_code, raw_unit_code, raw_is_split FROM tambon_xwalk "
            "WHERE raw_province_code IN ('10','11','24')"
        )
        rows = [
            (tambon_code, tambon_th, tambon_en, amphoe_code, amphoe_th, postal_code,
             f"TH{tambon_code}", unit_code, int(is_split == "True"))
            for tambon_code, tambon_th, tambon_en, amphoe_code, amphoe_th, postal_code, unit_code, is_split
            in bcur.fetchall()
        ]

    insert_sql = (
        "INSERT INTO dim_tambon_unit_xwalk "
        "(tambon_code, tambon_th, tambon_en, amphoe_code, amphoe_th, postal_code, adm3_pcode, unit_code, is_split) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    with gold_conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    gold_conn.commit()

    n_split = sum(1 for r in rows if r[8])
    print(f"[gold_dim] dim_tambon_unit_xwalk: {len(rows)} tambons ({n_split} post-2019 split siblings)")


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


def _build_dim_bma_zone(bronze_conn, gold_conn):
    """kmch-ml input-parity gap 2. Reads zone_id + the district-name list
    straight from bronze.bma_migrant_general (not hardcoded) -- 10 zones,
    skipping the grand-total row (zone label is empty there)."""
    with bronze_conn.cursor() as bcur:
        bcur.execute("SELECT raw_zone_label, raw_zone_districts_or_label FROM bma_migrant_general")
        raw_rows = bcur.fetchall()

    zones = []  # (zone_id, zone_label, [district names])
    for label, districts in raw_rows:
        label = (label or "").strip()
        if not label.startswith("พื้นที่"):
            continue  # grand-total row
        zone_id = int(label.replace("พื้นที่", "").strip())
        district_names = [d.strip() for d in (districts or "").split(",") if d.strip()]
        zones.append((zone_id, label, district_names))

    with gold_conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO dim_bma_zone (zone_id, zone_name_th) VALUES (%s,%s)",
            [(zid, label) for zid, label, _ in zones],
        )
        cur.execute("SELECT zone_key, zone_id FROM dim_bma_zone")
        zone_key_by_id = {zid: zkey for zkey, zid in cur.fetchall()}
        cur.execute("SELECT geo_key, district_name FROM dim_geography WHERE district_name IS NOT NULL")
        geo_key_by_district = {name: key for key, name in cur.fetchall()}

    bridge_rows = []
    unmatched = []
    for zone_id, _label, district_names in zones:
        zone_key = zone_key_by_id[zone_id]
        for d in district_names:
            geo_key = geo_key_by_district.get(d)
            if geo_key is None:
                unmatched.append((zone_id, d))
            bridge_rows.append((zone_key, d, geo_key))

    with gold_conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO bridge_bma_zone_district (zone_key, district_name, geo_key) VALUES (%s,%s,%s)",
            bridge_rows,
        )
    gold_conn.commit()

    print(f"[gold_dim] dim_bma_zone: {len(zones)} zones, {len(bridge_rows)} zone-district links "
          f"({len(unmatched)} unmatched district names)")
    if unmatched:
        print(f"[gold_dim] WARNING: dim_bma_zone: unmatched districts: {unmatched}")


def run() -> None:
    silver_conn = _connect("silver")
    bronze_conn = _connect("bronze")
    gold_conn = _connect("gold")

    _build_dim_date(silver_conn, gold_conn)
    _build_dim_geography(silver_conn, gold_conn)
    _build_dim_industry(silver_conn, gold_conn)
    _build_dim_hdc_report(bronze_conn, gold_conn)
    _build_dim_disease(silver_conn, gold_conn)
    _build_dim_area(bronze_conn, silver_conn, gold_conn)
    _build_dim_tambon_unit_xwalk(bronze_conn, gold_conn)
    _build_dim_facility(silver_conn, gold_conn)
    _build_dim_bma_zone(bronze_conn, gold_conn)

    silver_conn.close()
    bronze_conn.close()
    gold_conn.close()


if __name__ == "__main__":
    run()

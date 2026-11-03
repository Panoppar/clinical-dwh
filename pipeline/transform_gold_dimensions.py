"""Builds gold's 6 dimension tables from the live-API Silver/Bronze
sources. dim_geography is built purely from these sources' own text
labels (NSO/BMA/DIW all use plain geographic names) -- confirmed by direct
inspection that BMA's `district` and DIW's `amphoe` match exactly for
every Bangkok area checked, so a straight text union/match is safe here,
unlike the earlier DOPA-vs-kongvut mismatch this project hit before.

dim_area (kmch-ml input-parity gap 1) is a separate catchment-area
dimension, built from silver.geo_boundary_{subdistrict,district} --
see sql/gold/04_create_gold_area_dimension.sql for the full design note."""

import hashlib
import json
import math
import os

import pymysql
from shapely.affinity import scale as _affine_scale
from shapely.geometry import shape as _shapely_shape
from shapely.ops import unary_union


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
        # INSERT IGNORE, not plain INSERT: dim_date's DDL is now CREATE TABLE
        # IF NOT EXISTS (incremental migration), so this table is no longer
        # dropped+recreated every run -- a plain INSERT would hit a
        # duplicate PRIMARY KEY (date_key) error on every year already seen.
        cur.executemany(
            "INSERT IGNORE INTO dim_date (date_key, year_ce, year_be) VALUES (%s,%s,%s)",
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
    """dim_geography's DDL is CREATE TABLE IF NOT EXISTS (incremental
    migration), so this table is no longer dropped+recreated every run --
    existing provinces/districts/subdistricts must keep their existing
    geo_key across runs (facts reference it via FK, and incrementally
    preserved facts from a prior run would silently point to the wrong
    place otherwise). province_key/district_key/subdistrict_seen are
    preloaded from whatever's already in the table before any insert
    decision is made, so already-seen entities are recognized and reused
    instead of re-inserted with a new surrogate key."""
    province_key = {}   # province_name -> geo_key
    district_key = {}   # (province_name, district_name) -> geo_key
    subdistrict_seen = set()  # (province_name, district_name, subdistrict_name)

    with gold_conn.cursor() as cur:
        cur.execute(
            "SELECT geo_key, admin_level, province_name, district_name, subdistrict_name FROM dim_geography"
        )
        for geo_key, admin_level, province, district, subdistrict in cur.fetchall():
            if admin_level == "province":
                province_key[province] = geo_key
            elif admin_level == "district":
                district_key[(province, district)] = geo_key
            elif admin_level == "subdistrict":
                subdistrict_seen.add((province, district, subdistrict))

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

        for district, subdistrict in sorted(bma_subdistricts):
            k = ("กรุงเทพมหานคร", district, subdistrict)
            if k in subdistrict_seen:
                continue
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
    """Sourced from both DDS endpoints -- the live province-grain API
    (api_dds_disease_ranking, empty while DDS's backend stays down since
    2026-10-25) and the health-region-grain PDF archive
    (dds_health_region_disease_report, used as a stand-in while the live
    API is down). Same underlying government disease-name vocabulary, so
    both resolve into the same dim_disease rows via INSERT IGNORE's unique
    key on disease_name -- no separate dimension needed."""
    with silver_conn.cursor() as scur:
        scur.execute("SELECT DISTINCT disease_name FROM api_dds_disease_ranking WHERE disease_name IS NOT NULL")
        rows = list(scur.fetchall())
        scur.execute("SELECT DISTINCT disease_name_th FROM dds_health_region_disease_report WHERE disease_name_th IS NOT NULL")
        rows.extend(scur.fetchall())
    with gold_conn.cursor() as cur:
        cur.executemany("INSERT IGNORE INTO dim_disease (disease_name) VALUES (%s)", rows)
    gold_conn.commit()
    print(f"[gold_dim] dim_disease: {len(rows)} source rows (live DDS + health-region PDFs, deduplicated by name)")


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
    """-> (polygons_by_subdistrict_code, polygons_by_district_code). The
    subdistrict dict is keyed by the bare TIS-1099 code (ADM3_PCODE with
    its leading 'TH' stripped) -> {"geometry", "name_th", "name_en"}. The
    district dict is keyed by the bare ADM2 code -> list of those same
    entries, one per polygon found under that district (used to detect
    and resolve Bangkok's post-2019 khwaeng-split merge groups -- see
    _build_dim_area). bronze.geo_boundary_polygon is nationwide and
    unfiltered -- see docs/06_kmch_ml_gap_closure_plan.md's Gap 6 note:
    this is the exact same file kmch-ml's own training export carries,
    already landed here, not a separate source."""
    with bronze_conn.cursor() as bcur:
        bcur.execute(
            "SELECT raw_adm3_pcode, raw_adm3_en, raw_adm3_th, raw_adm2_pcode, raw_geometry_geojson "
            "FROM geo_boundary_polygon"
        )
        rows = bcur.fetchall()

    by_subdistrict: dict[str, dict] = {}
    by_district: dict[str, list] = {}
    for adm3_pcode, adm3_en, adm3_th, adm2_pcode, geom_text in rows:
        if not geom_text:
            continue
        geometry = json.loads(geom_text)
        bare3 = (adm3_pcode or "").removeprefix("TH")
        bare2 = (adm2_pcode or "").removeprefix("TH")
        entry = {"geometry": geometry, "adm3_code": bare3, "name_th": adm3_th, "name_en": adm3_en}
        if bare3:
            by_subdistrict[bare3] = entry
        if bare2:
            by_district.setdefault(bare2, []).append(entry)
    return by_subdistrict, by_district


def _build_dim_area(bronze_conn, silver_conn, gold_conn):
    """Grain: one row per catchment unit. Units are grouped by matching
    each tambon in silver.geo_boundary_subdistrict against
    bronze.geo_boundary_polygon: if a tambon has its own polygon
    (ADM3_PCODE match), it's its own unit; if not, it merges into
    whichever single polygon exists under its parent district (ADM2_PCODE
    match).

    This replaces an earlier version that read an externally-supplied
    xwalk_tambon_unit.csv (kmch-ml's own file) for this grouping. Removed
    2026-11-03: confirmed by direct query that every tambon this file ever
    needed to merge is exactly the set of tambons with no own polygon AND
    whose district has exactly one polygon total -- scoped to provinces
    10/11/24, this pattern occurs for precisely the known 7 Bangkok
    post-2019 khwaeng-split districts and nowhere else, so it's fully
    derivable from data already fetched live (geo_boundary_subdistrict +
    geo_boundary_polygon, both from the same canonical GitHub dataset) --
    no externally-supplied file needed. An even earlier version tried a
    NULL-centroid-only heuristic and got this wrong (5 of 7 groups left
    unmerged, inflating 312 to 317) because "has no centroid" alone can't
    tell you which other tambon to merge with -- the district-polygon-
    count check here is what actually answers that.

    centroid_lat/lon, area_km2, and contains_kmch_point are all derived
    from that single polygon via a consistent, unified method for every
    row (merged or not) -- not a mix of "Silver's stored point" for
    ordinary units and "something else" for merged ones."""
    polygons_by_subdistrict, polygons_by_district = _load_boundary_polygons(bronze_conn)

    with silver_conn.cursor() as scur:
        scur.execute(
            "SELECT subdistrict_code, district_code, province_code FROM geo_boundary_subdistrict "
            "WHERE province_code IN ('10','11','24')"
        )
        tambon_rows = scur.fetchall()
        scur.execute(
            "SELECT district_code, province_code, name_th, name_en FROM geo_boundary_district "
            "WHERE province_code IN ('10','11','24')"
        )
        district_by_code = {d[0]: d for d in scur.fetchall()}

    groups: dict[str, dict] = {}
    ambiguous: list[str] = []
    for tambon_code, district_code, province_code in tambon_rows:
        if tambon_code in polygons_by_subdistrict:
            unit_code = tambon_code
        else:
            district_polys = polygons_by_district.get(district_code, [])
            if len(district_polys) != 1:
                ambiguous.append(tambon_code)  # genuine data gap, not a resolvable split-merge -- skip
                continue
            unit_code = district_polys[0]["adm3_code"]

        d = district_by_code.get(district_code)
        amphoe_th = d[2] if d else None
        g = groups.setdefault(unit_code, {
            "members": [], "amphoe_code": district_code, "amphoe_th": amphoe_th, "province_code": province_code,
        })
        g["members"].append(tambon_code)

    if ambiguous:
        print(f"[gold_dim] WARNING: dim_area: {len(ambiguous)} tambon(s) have no own polygon and their "
              f"district doesn't resolve to exactly one fallback polygon, skipped: {ambiguous}")

    rows = []
    skipped = []
    for unit_code, g in groups.items():
        geometry_entry = polygons_by_subdistrict.get(unit_code)
        if geometry_entry is None:
            skipped.append(unit_code)
            continue
        geometry = geometry_entry["geometry"]

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
            unit_th = geometry_entry.get("name_th") or amphoe_th

        dist = _haversine_km(lat, lon, KMCH_LAT, KMCH_LON)
        tier, is_catchment = _catchment_tier(dist, pcode)
        province_th = CATCHMENT_PROVINCE_NAMES.get(pcode, pcode)

        rows.append((unit_code, unit_th, int(is_fallback), pcode, province_th, amphoe_code, amphoe_th, amphoe_en,
                     lat, lon, round(dist, 3), tier, int(is_catchment), area_km2, int(contains_kmch_point),
                     n_member, "|".join(members)))

    if skipped:
        print(f"[gold_dim] WARNING: dim_area: {len(skipped)} unit(s) have no matching polygon, skipped: {skipped}")

    # INSERT IGNORE, not plain INSERT: dim_area's DDL is CREATE TABLE IF NOT
    # EXISTS (incremental migration), so this table is no longer dropped+
    # recreated every run -- a plain INSERT would hit dim_area's own UNIQUE
    # KEY on unit_code on every unit already seen. IGNORE also keeps each
    # existing unit's area_key stable, which fact_factory.area_key (and
    # fact_hospital_access.area_key) depend on across incrementally
    # preserved fact rows.
    insert_sql = (
        "INSERT IGNORE INTO dim_area (unit_code, unit_th, is_district_level_fallback, province_code, province_th, "
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


def _build_dim_tambon_unit_xwalk(bronze_conn, silver_conn, gold_conn):
    """Grain: one row per original TIS-1099 tambon code (within provinces
    10/11/24) -- finer than dim_area's merged-unit grain. Must run after
    _build_dim_area() (FK dependency on dim_area.unit_code).

    Derives the same (tambon_code -> unit_code, is_split) mapping
    _build_dim_area computes, straight from geo_boundary_subdistrict +
    geo_boundary_polygon -- see that function's docstring for why an
    externally-supplied xwalk file is no longer needed here."""
    polygons_by_subdistrict, polygons_by_district = _load_boundary_polygons(bronze_conn)

    with silver_conn.cursor() as scur:
        scur.execute(
            "SELECT subdistrict_code, district_code, province_code, name_th, name_en, postal_code "
            "FROM geo_boundary_subdistrict WHERE province_code IN ('10','11','24')"
        )
        tambon_rows = scur.fetchall()
        scur.execute(
            "SELECT district_code, name_th FROM geo_boundary_district WHERE province_code IN ('10','11','24')"
        )
        amphoe_th_by_code = dict(scur.fetchall())

    rows = []
    for tambon_code, district_code, province_code, tambon_th, tambon_en, postal_code in tambon_rows:
        if tambon_code in polygons_by_subdistrict:
            unit_code, is_split = tambon_code, 0
        else:
            district_polys = polygons_by_district.get(district_code, [])
            if len(district_polys) != 1:
                continue  # same ambiguous-skip as _build_dim_area
            unit_code, is_split = district_polys[0]["adm3_code"], 1

        amphoe_th = amphoe_th_by_code.get(district_code)
        rows.append((
            tambon_code, tambon_th, tambon_en, district_code, amphoe_th, postal_code,
            f"TH{tambon_code}", unit_code, is_split,
        ))

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


_ADJ_BUFFER_M = 5  # same micro-gap tolerance kmch-ml's own notebook documents needing for this exact polygon source
_ADJ_ROOK_MIN_M = 10  # shared-boundary length above which a touch counts as "rook" (DEGURBA centre tier) not just "queen" (corner touch)
_ADJ_REF_LAT = 13.7  # Bangkok-area reference latitude for the local equirectangular meters approximation below -- same spherical-Earth constant as _haversine_km, just reused as a linear (not great-circle) scale since the tolerances here are a few meters, not kilometers


def _local_meters_scale(lat_deg: float = _ADJ_REF_LAT) -> tuple[float, float]:
    """-> (meters_per_degree_lon, meters_per_degree_lat), a local linear
    approximation (not a true projection) -- good enough at a few-meter
    tolerance across this project's 3-province extent, same spirit as
    _haversine_km's spherical approximation elsewhere in this file."""
    lat_rad = math.radians(lat_deg)
    m_per_deg_lat = (math.pi / 180.0) * _EARTH_RADIUS_KM * 1000.0
    return m_per_deg_lat * math.cos(lat_rad), m_per_deg_lat


def _build_bridge_area_adjacency(bronze_conn, gold_conn):
    """kmch-ml input-parity: precomputes the polygon-contiguity graph
    (rook/queen) that CL-G1 (DEGURBA urban/cluster/rural) needs, so the
    separate ML project never has to carry GIS dependencies or recompute
    unchanging geometry on every scheduled run. Must run after
    _build_dim_area()/_build_dim_tambon_unit_xwalk() (reads both).

    Adjacency is checked at the tambon (polygon) grain -- a unit's member
    tambons' own geometries, not a true dissolved union -- since "does unit
    A touch unit B" only needs "does any tambon of A touch any tambon of
    B", which is cheaper and avoids a real unary_union per unit. Shared
    boundary length is still summed across all touching tambon-pairs so a
    merged unit's total shared-boundary-with-a-neighbour is correct.

    Algorithm matches kmch-ml's own notebook exactly (captured from its
    live source during this integration): buffer by 5m to absorb the same
    small polygon gaps their own ADJ_BUFFER_M fallback documents, and
    shared-boundary length = buffer(1m).intersection(other.boundary).length,
    rook if that exceeds 10m."""
    polygons_by_subdistrict, _ = _load_boundary_polygons(bronze_conn)

    with gold_conn.cursor() as cur:
        cur.execute("SELECT tambon_code, unit_code FROM dim_tambon_unit_xwalk")
        unit_by_tambon = dict(cur.fetchall())
        cur.execute("SELECT unit_code, area_key FROM dim_area")
        area_key_by_unit = dict(cur.fetchall())

    mx, my = _local_meters_scale()

    # One scaled shapely geometry per tambon that both has a polygon and
    # resolves to a unit that made it into dim_area.
    tambon_geoms: dict[str, object] = {}
    tambon_unit: dict[str, str] = {}
    for tambon_code, unit_code in unit_by_tambon.items():
        if unit_code not in area_key_by_unit:
            continue
        entry = polygons_by_subdistrict.get(tambon_code)
        if entry is None:
            continue
        geom = _shapely_shape(entry["geometry"])
        tambon_geoms[tambon_code] = _affine_scale(geom, xfact=mx, yfact=my, origin=(0, 0))
        tambon_unit[tambon_code] = unit_code

    codes = list(tambon_geoms)
    bounds = {c: tambon_geoms[c].bounds for c in codes}  # (minx, miny, maxx, maxy), already in meters

    pair_shared_m: dict[tuple[str, str], float] = {}
    for i, ca in enumerate(codes):
        ax0, ay0, ax1, ay1 = bounds[ca]
        geom_a = tambon_geoms[ca]
        buf_a_touch = geom_a.buffer(_ADJ_BUFFER_M)
        buf_a_shared = geom_a.buffer(1)
        for cb in codes[i + 1:]:
            unit_a, unit_b = tambon_unit[ca], tambon_unit[cb]
            if unit_a == unit_b:
                continue  # siblings within the same merged unit -- not a cross-unit adjacency
            bx0, by0, bx1, by1 = bounds[cb]
            # AABB pre-filter, padded by the buffer tolerance -- skip the
            # expensive shapely ops for pairs that can't possibly touch.
            if ax0 - _ADJ_BUFFER_M > bx1 or bx0 - _ADJ_BUFFER_M > ax1:
                continue
            if ay0 - _ADJ_BUFFER_M > by1 or by0 - _ADJ_BUFFER_M > ay1:
                continue
            geom_b = tambon_geoms[cb]
            if not buf_a_touch.intersects(geom_b):
                continue
            shared_len = buf_a_shared.intersection(geom_b.boundary).length
            key = tuple(sorted((unit_a, unit_b)))
            pair_shared_m[key] = pair_shared_m.get(key, 0.0) + shared_len

    rows = []
    for (unit_a, unit_b), shared_m in pair_shared_m.items():
        area_key_a, area_key_b = sorted((area_key_by_unit[unit_a], area_key_by_unit[unit_b]))
        rows.append((area_key_a, area_key_b, round(shared_m, 2), int(shared_m > _ADJ_ROOK_MIN_M)))

    insert_sql = (
        "INSERT INTO bridge_area_adjacency (area_key_a, area_key_b, shared_boundary_m, is_rook) "
        "VALUES (%s,%s,%s,%s)"
    )
    with gold_conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    gold_conn.commit()

    n_rook = sum(1 for r in rows if r[3])
    print(f"[gold_dim] bridge_area_adjacency: {len(rows)} pairs ({n_rook} rook)")


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
    """kmch-ml input-parity gap 2. Reads the zone_id -> district-name
    mapping from bronze.bma_zone_districts (not hardcoded) -- 10 zones.
    This is static Thai public-administration geography, not permit-count
    data, so it's sourced independently of whichever source currently
    provides fact_migrant_worker_permit's counts (see sql/bronze/17's
    header for why this was split out on 2026-10-28)."""
    with bronze_conn.cursor() as bcur:
        bcur.execute("SELECT raw_zone_id, raw_zone_name_th, raw_district_name FROM bma_zone_districts")
        raw_rows = bcur.fetchall()

    zones_by_id = {}  # zone_id -> (zone_label, [district names])
    for zone_id_raw, label, district in raw_rows:
        zone_id = int(zone_id_raw)
        entry = zones_by_id.setdefault(zone_id, (label, []))
        entry[1].append(district)
    zones = [(zid, label, districts) for zid, (label, districts) in sorted(zones_by_id.items())]

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


def _build_dim_catchment_place(silver_conn, gold_conn):
    """One row per place from the KMCH catchment places list (file-based,
    kmch_catchment_places.csv). geo_key resolved via exact (province,
    district, subdistrict) text match against dim_geography -- confirmed
    live all 15 distinct location combinations in this source resolve
    cleanly."""
    with gold_conn.cursor() as cur:
        cur.execute("SELECT geo_key, province_name, district_name, subdistrict_name FROM dim_geography")
        geo_lookup = {(p, d, s): k for k, p, d, s in cur.fetchall()}

    with silver_conn.cursor() as scur:
        scur.execute(
            "SELECT category, place_name_th, place_name_en, address, subdistrict, district, province, "
            "avg_distance_km, avg_travel_time_min, market_tier, market_detail FROM kmch_catchment_places"
        )
        silver_rows = scur.fetchall()

    rows = []
    unmatched = 0
    for (category, name_th, name_en, address, subdistrict, district, province,
         dist, travel_time, tier, detail) in silver_rows:
        geo_key = geo_lookup.get((province, district, subdistrict))
        if geo_key is None:
            unmatched += 1
        place_hash = hashlib.sha256(f"{name_th}|{address}".encode()).hexdigest()[:16]
        rows.append((category, name_th, name_en, address, geo_key, dist, travel_time, tier, detail, place_hash))

    insert_sql = (
        "INSERT INTO dim_catchment_place "
        "(category, place_name_th, place_name_en, address, geo_key, avg_distance_km, avg_travel_time_min, "
        "market_tier, market_detail, place_hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    with gold_conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    gold_conn.commit()

    print(f"[gold_dim] dim_catchment_place: {len(rows)} places ({unmatched} unmatched geo)")


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
    _build_dim_tambon_unit_xwalk(bronze_conn, silver_conn, gold_conn)
    _build_bridge_area_adjacency(bronze_conn, gold_conn)
    _build_dim_facility(silver_conn, gold_conn)
    _build_dim_bma_zone(bronze_conn, gold_conn)
    _build_dim_catchment_place(silver_conn, gold_conn)

    silver_conn.close()
    bronze_conn.close()
    gold_conn.close()


if __name__ == "__main__":
    run()

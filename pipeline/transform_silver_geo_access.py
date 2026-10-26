"""Silver transform for bronze.geo_hospital_facility / geo_travel_matrix.
Casts coordinates/duration/distance to DECIMAL; trims text. Skips facility
rows with no resolvable lat/lon (a handful of OSM relations/ways can lack
a computed center) -- dropped, not guessed.

Split into two entry points (run_facility / run_travel_matrix) because
they run at different pipeline stages: facility has no dependency and
runs in the normal Silver phase; travel_matrix only has Bronze data once
ingest_api_osrm.py has run, which itself needs gold.dim_area to already
exist -- see run_pipeline.py's mid-Gold OSRM stage."""

import os

import pymysql


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
        return float(s)
    except ValueError:
        return None


def run_facility() -> None:
    read_conn = _connect("bronze")
    write_conn = _connect("silver")

    with read_conn.cursor() as rcur:
        rcur.execute("SELECT raw_osm_type, raw_osm_id, raw_name, raw_lat, raw_lon, raw_tags_json FROM geo_hospital_facility")
        rows = []
        for osm_type, osm_id, name, lat, lon, tags in rcur:
            lat_d, lon_d = _to_decimal(lat), _to_decimal(lon)
            if osm_type is None or osm_id is None or lat_d is None or lon_d is None:
                continue
            rows.append((osm_type, osm_id, (name or "").strip() or None, lat_d, lon_d, tags))
    with write_conn.cursor() as wcur:
        wcur.executemany(
            "INSERT IGNORE INTO geo_hospital_facility (osm_type, osm_id, name, lat, lon, tags_json) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            rows,
        )
    write_conn.commit()
    print(f"[silver_geo_access] geo_hospital_facility: loaded {len(rows)} rows")
    read_conn.close()
    write_conn.close()


def run_travel_matrix() -> None:
    read_conn = _connect("bronze")
    write_conn = _connect("silver")

    with read_conn.cursor() as rcur:
        rcur.execute(
            "SELECT raw_source_unit_code, raw_destination_id, raw_duration_s, raw_distance_m, "
            "raw_source_snap_m, raw_destination_snap_m FROM geo_travel_matrix"
        )
        rows = []
        for unit_code, dest_id, duration, distance, src_snap, dest_snap in rcur:
            if not unit_code or not dest_id:
                continue
            rows.append((unit_code, dest_id, _to_decimal(duration), _to_decimal(distance),
                         _to_decimal(src_snap), _to_decimal(dest_snap)))
    with write_conn.cursor() as wcur:
        wcur.executemany(
            "INSERT INTO geo_travel_matrix (source_unit_code, destination_id, duration_s, distance_m, "
            "source_snap_m, destination_snap_m) VALUES (%s,%s,%s,%s,%s,%s)",
            rows,
        )
    write_conn.commit()
    print(f"[silver_geo_access] geo_travel_matrix: loaded {len(rows)} rows")
    read_conn.close()
    write_conn.close()


def run() -> None:
    run_facility()
    run_travel_matrix()


if __name__ == "__main__":
    run()

"""Loads bronze.geo_hospital_facility from the Overpass response
ingest_api_osm.py landed in the landing zone. Straight 1:1 field mapping.
0 rows while Overpass stays blocked (see sql/bronze/12) -- this is a
normal "nothing landed yet" skip, not an error.
"""

import hashlib
import json
import os
from datetime import datetime, timezone

import pymysql

import landing_store

BATCH_SIZE = 2000


def _connect():
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"], port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"], password=os.environ["DWH_DB_PASSWORD"],
        database="bronze", charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def run() -> None:
    key = landing_store.latest_version("geo_access", "osm_hospitals", "json")
    if key is None:
        print("[extract_load_api_osm] no landed OSM object found, skipping (run ingest_api_osm first)")
        return
    content = landing_store.read_bytes(key)
    file_hash = hashlib.sha256(content).hexdigest()
    body = json.loads(content)
    elements = body.get("elements", [])

    loaded_at = datetime.now(timezone.utc)
    batch_id = f"api_osm_load_{loaded_at:%Y%m%dT%H%M%S}"
    insert_sql = (
        "INSERT INTO geo_hospital_facility "
        "(source_folder, source_file_name, source_row_number, file_hash, ingestion_batch_id, "
        "raw_osm_type, raw_osm_id, raw_lat, raw_lon, raw_name, raw_tags_json) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    rows = []
    for i, el in enumerate(elements, start=1):
        tags = el.get("tags", {})
        if "lat" in el and "lon" in el:
            lat, lon = el["lat"], el["lon"]
        else:
            center = el.get("center", {})
            lat, lon = center.get("lat"), center.get("lon")
        rows.append((
            "geo_access", key, i, file_hash, batch_id,
            el.get("type"), el.get("id"), lat, lon, tags.get("name"), json.dumps(tags),
        ))

    conn = _connect()
    with conn.cursor() as cur:
        for i in range(0, len(rows), BATCH_SIZE):
            cur.executemany(insert_sql, rows[i:i + BATCH_SIZE])
    conn.commit()
    conn.close()
    print(f"[extract_load_api_osm] geo_hospital_facility: loaded {len(rows)} rows from {key}")


if __name__ == "__main__":
    run()

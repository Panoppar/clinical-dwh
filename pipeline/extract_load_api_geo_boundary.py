"""Loads bronze.geo_boundary_{subdistrict,district,polygon} from the files
ingest_api_geo_boundary.py landed in the landing zone. Straight 1:1 field
mapping, no transformation -- Bangkok's 13 post-2019 khwaeng-split
fallback and the Gold-level unit_code/distance/tier derivation happen in
transform_gold_dimensions.py, not here.
"""

import csv
import hashlib
import io
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


def _insert_batch(cur, insert_sql, rows):
    row_count = 0
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) >= BATCH_SIZE:
            cur.executemany(insert_sql, batch)
            row_count += len(batch)
            batch.clear()
    if batch:
        cur.executemany(insert_sql, batch)
        row_count += len(batch)
    return row_count


def _load_and_hash(prefix: str, stem: str, ext: str) -> tuple[bytes, str, str]:
    key = landing_store.latest_version(prefix, stem, ext)
    if key is None:
        return b"", "", ""
    content = landing_store.read_bytes(key)
    return content, key, hashlib.sha256(content).hexdigest()


def _load_subdistrict(conn, batch_id: str) -> int:
    content, key, file_hash = _load_and_hash("geo_boundary", "subdistrict", "csv")
    if not content:
        print("[extract_load_api_geo_boundary] no landed subdistrict CSV found, skipping")
        return 0
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    insert_sql = (
        "INSERT INTO geo_boundary_subdistrict "
        "(source_folder, source_file_name, source_row_number, file_hash, ingestion_batch_id, "
        "raw_tis1099_subdistrict_code, raw_parent_district_tis1099_code, raw_parent_province_tis1099_code, "
        "raw_name_en, raw_name_th, raw_centroid_lat, raw_centroid_lon, raw_postal_code) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    rows = [
        ("geo_boundary", key, i, file_hash, batch_id,
         r["tis1099_subdistrict_code"], r["parent_district_tis1099_code"], r["parent_province_tis1099_code"],
         r["name_en"], r["name_th"], r["centroid_lat"] or None, r["centroid_lon"] or None, r["postal_code"])
        for i, r in enumerate(reader, start=1)
    ]
    with conn.cursor() as cur:
        n = _insert_batch(cur, insert_sql, rows)
    conn.commit()
    print(f"[extract_load_api_geo_boundary] geo_boundary_subdistrict: loaded {n} rows")
    return n


def _load_district(conn, batch_id: str) -> int:
    content, key, file_hash = _load_and_hash("geo_boundary", "district", "csv")
    if not content:
        print("[extract_load_api_geo_boundary] no landed district CSV found, skipping")
        return 0
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    insert_sql = (
        "INSERT INTO geo_boundary_district "
        "(source_folder, source_file_name, source_row_number, file_hash, ingestion_batch_id, "
        "raw_tis1099_district_code, raw_parent_province_tis1099_code, raw_name_en, raw_name_th, "
        "raw_centroid_lat, raw_centroid_lon, raw_area_km2, raw_bbox_minlat, raw_bbox_minlon, "
        "raw_bbox_maxlat, raw_bbox_maxlon, raw_num_tambon, raw_postal_code_prefixes, raw_notes) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    rows = [
        ("geo_boundary", key, i, file_hash, batch_id,
         r["tis1099_district_code"], r["parent_province_tis1099_code"], r["name_en"], r["name_th"],
         r["centroid_lat"] or None, r["centroid_lon"] or None, r["area_km2"] or None,
         r["bbox_minlat"] or None, r["bbox_minlon"] or None, r["bbox_maxlat"] or None, r["bbox_maxlon"] or None,
         r["num_tambon"] or None, r["postal_code_prefixes"] or None, r["notes"] or None)
        for i, r in enumerate(reader, start=1)
    ]
    with conn.cursor() as cur:
        n = _insert_batch(cur, insert_sql, rows)
    conn.commit()
    print(f"[extract_load_api_geo_boundary] geo_boundary_district: loaded {n} rows")
    return n


def _load_polygon(conn, batch_id: str) -> int:
    content, key, file_hash = _load_and_hash("geo_boundary", "polygon", "geojson")
    if not content:
        print("[extract_load_api_geo_boundary] no landed polygon GeoJSON found, skipping")
        return 0
    body = json.loads(content)
    features = body.get("features", [])
    insert_sql = (
        "INSERT INTO geo_boundary_polygon "
        "(source_folder, source_file_name, source_row_number, file_hash, ingestion_batch_id, "
        "raw_adm3_pcode, raw_adm3_en, raw_adm3_th, raw_adm2_pcode, raw_adm1_pcode, raw_geometry_geojson) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    rows = []
    for i, feat in enumerate(features, start=1):
        props = feat.get("properties", {})
        rows.append((
            "geo_boundary", key, i, file_hash, batch_id,
            props.get("ADM3_PCODE"), props.get("ADM3_EN"), props.get("ADM3_TH"),
            props.get("ADM2_PCODE"), props.get("ADM1_PCODE"),
            json.dumps(feat.get("geometry")),
        ))
    with conn.cursor() as cur:
        n = _insert_batch(cur, insert_sql, rows)
    conn.commit()
    print(f"[extract_load_api_geo_boundary] geo_boundary_polygon: loaded {n} rows")
    return n


def run() -> None:
    conn = _connect()
    loaded_at = datetime.now(timezone.utc)
    batch_id = f"geo_boundary_load_{loaded_at:%Y%m%dT%H%M%S}"
    try:
        _load_subdistrict(conn, batch_id)
        _load_district(conn, batch_id)
        _load_polygon(conn, batch_id)
    finally:
        conn.close()


if __name__ == "__main__":
    run()

"""Loads bronze.geo_travel_matrix from the OSRM table-API tiles
ingest_api_osrm.py landed. OSRM's response only carries numeric row/column
indices into the sources/destinations lists, not labels -- re-derives the
exact same tiling ingest_api_osrm.py used (same deterministic SQL order,
same tile-size constants) to recover unit_code/destination_id per cell,
rather than landing redundant label metadata per tile.
"""

import hashlib
import json
import os
from datetime import datetime, timezone

import pymysql

import ingest_api_osrm
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
    sources = ingest_api_osrm._load_sources()
    destinations = ingest_api_osrm._load_destinations()
    if not sources:
        print("[extract_load_api_osrm] gold.dim_area has no rows, skipping")
        return

    loaded_at = datetime.now(timezone.utc)
    batch_id = f"api_osrm_load_{loaded_at:%Y%m%dT%H%M%S}"
    insert_sql = (
        "INSERT INTO geo_travel_matrix "
        "(source_folder, source_file_name, source_row_number, file_hash, ingestion_batch_id, "
        "raw_source_unit_code, raw_destination_id, raw_duration_s, raw_distance_m, "
        "raw_source_snap_m, raw_destination_snap_m) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    conn = _connect()
    total = 0
    row_counter = 0
    tiles_found = 0
    for s_start in range(0, len(sources), ingest_api_osrm.MAX_SOURCES_PER_TILE):
        source_tile = sources[s_start:s_start + ingest_api_osrm.MAX_SOURCES_PER_TILE]
        for d_start in range(0, len(destinations), ingest_api_osrm.MAX_DESTINATIONS_PER_TILE):
            dest_tile = destinations[d_start:d_start + ingest_api_osrm.MAX_DESTINATIONS_PER_TILE]
            stem = f"osrm_tile_{s_start // ingest_api_osrm.MAX_SOURCES_PER_TILE}_{d_start // ingest_api_osrm.MAX_DESTINATIONS_PER_TILE}"
            key = landing_store.latest_version("geo_access", stem, "json")
            if key is None:
                continue
            tiles_found += 1
            content = landing_store.read_bytes(key)
            file_hash = hashlib.sha256(content).hexdigest()
            body = json.loads(content)
            if body.get("code") != "Ok":
                print(f"[extract_load_api_osrm] WARNING: tile {stem} returned code={body.get('code')!r}, skipping")
                continue

            durations = body.get("durations", [])
            distances = body.get("distances", [])
            sources_resp = body.get("sources", [])
            destinations_resp = body.get("destinations", [])

            rows = []
            for i, (unit_code, _, _) in enumerate(source_tile):
                src_snap = sources_resp[i].get("distance") if i < len(sources_resp) else None
                for j, (dest_id, _, _) in enumerate(dest_tile):
                    dest_snap = destinations_resp[j].get("distance") if j < len(destinations_resp) else None
                    duration = durations[i][j] if i < len(durations) and j < len(durations[i]) else None
                    distance = distances[i][j] if i < len(distances) and j < len(distances[i]) else None
                    row_counter += 1
                    rows.append((
                        "geo_access", key, row_counter, file_hash, batch_id,
                        unit_code, dest_id, duration, distance, src_snap, dest_snap,
                    ))

            with conn.cursor() as cur:
                for i in range(0, len(rows), BATCH_SIZE):
                    cur.executemany(insert_sql, rows[i:i + BATCH_SIZE])
            conn.commit()
            total += len(rows)

    conn.close()
    print(f"[extract_load_api_osrm] geo_travel_matrix: loaded {total} rows across {tiles_found} tiles")


if __name__ == "__main__":
    run()

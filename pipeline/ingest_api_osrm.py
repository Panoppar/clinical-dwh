"""Computes a travel-time/distance matrix from every gold.dim_area unit
centroid to KMCH (always) and to every OSM-discovered facility (if any
landed -- see ingest_api_osm.py), via OSRM's public demo server table API.
Lands each tile's raw JSON response in the landing zone. Does not parse --
that's extract_load_api_osrm.py's job.

Reads from gold.dim_area (not just Bronze/an external API) by design --
this source has a real, explicit dependency on Gap 1's unit centroids
already existing, confirmed in the project plan. Run this after
transform_gold_dimensions.py, not before.

Public demo server (router.project-osrm.org), confirmed reachable and
working 2026-10-26 -- no self-hosted OSRM needed. Tiled at kmch-ml's own
confirmed limits (25 sources x 75 destinations per request, 1.2s pause
between tiles) -- a real rate-limit constraint on a shared public server,
not an arbitrary choice.
"""

import os
import time

import pymysql
import requests

import landing_store

KMCH_LAT, KMCH_LON = 13.732307519058327, 100.78967253963812
OSRM_TABLE_URL = "https://router.project-osrm.org/table/v1/driving"
MAX_SOURCES_PER_TILE = 25
MAX_DESTINATIONS_PER_TILE = 75
MIN_DELAY_S = 1.2


class _Throttle:
    def __init__(self, min_delay: float):
        self.min_delay = min_delay
        self.last = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self.last
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last = time.monotonic()


def _connect(database):
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"], port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"], password=os.environ["DWH_DB_PASSWORD"],
        database=database, charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def _load_sources() -> list[tuple[str, float, float]]:
    conn = _connect("gold")
    with conn.cursor() as cur:
        cur.execute("SELECT unit_code, centroid_lat, centroid_lon FROM dim_area")
        rows = [(code, float(lat), float(lon)) for code, lat, lon in cur.fetchall()]
    conn.close()
    return rows


def _load_destinations() -> list[tuple[str, float, float]]:
    """-> [(destination_id, lat, lon), ...]. KMCH itself is always first and
    guaranteed present, regardless of whether OSM discovery has landed
    anything -- this is the single most important destination for this
    project, not something that should depend on Overpass being reachable."""
    destinations = [("KMCH", KMCH_LAT, KMCH_LON)]
    try:
        conn = _connect("bronze")
        with conn.cursor() as cur:
            cur.execute(
                "SELECT raw_osm_type, raw_osm_id, raw_lat, raw_lon FROM geo_hospital_facility "
                "WHERE raw_lat IS NOT NULL AND raw_lon IS NOT NULL"
            )
            for osm_type, osm_id, lat, lon in cur.fetchall():
                destinations.append((f"{osm_type}_{osm_id}", float(lat), float(lon)))
        conn.close()
    except Exception as exc:  # noqa: BLE001
        print(f"[ingest_api_osrm] WARNING: could not load OSM facilities, using KMCH-only destination list: {exc}")
    return destinations


def run() -> None:
    sources = _load_sources()
    destinations = _load_destinations()
    if not sources:
        raise RuntimeError("ingest_api_osrm: gold.dim_area has no rows -- run transform_gold_dimensions.run() first")
    print(f"[ingest_api_osrm] {len(sources)} source units x {len(destinations)} destinations "
          f"({'KMCH only' if len(destinations) == 1 else 'KMCH + OSM-discovered facilities'})")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 clinical-dwh-geo-access/1.0"})
    throttle = _Throttle(MIN_DELAY_S)

    tile_index = 0
    for s_start in range(0, len(sources), MAX_SOURCES_PER_TILE):
        source_tile = sources[s_start:s_start + MAX_SOURCES_PER_TILE]
        for d_start in range(0, len(destinations), MAX_DESTINATIONS_PER_TILE):
            dest_tile = destinations[d_start:d_start + MAX_DESTINATIONS_PER_TILE]
            tile_index += 1

            coords = source_tile + dest_tile
            coord_str = ";".join(f"{lon},{lat}" for _, lat, lon in coords)
            source_idx = ";".join(str(i) for i in range(len(source_tile)))
            dest_idx = ";".join(str(i) for i in range(len(source_tile), len(coords)))

            throttle.wait()
            resp = session.get(
                f"{OSRM_TABLE_URL}/{coord_str}",
                params={"sources": source_idx, "destinations": dest_idx, "annotations": "duration,distance"},
                timeout=60,
            )
            resp.raise_for_status()

            stem = f"tile_{s_start // MAX_SOURCES_PER_TILE}_{d_start // MAX_DESTINATIONS_PER_TILE}"
            key, is_new = landing_store.save_version("geo_access", f"osrm_{stem}", "json", resp.content)
            status = "landed new version" if is_new else "unchanged"
            print(f"[ingest_api_osrm] tile {tile_index} ({len(source_tile)} sources x {len(dest_tile)} dest): {status}: {key}")


if __name__ == "__main__":
    run()

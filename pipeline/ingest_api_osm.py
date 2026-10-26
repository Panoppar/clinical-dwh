"""Fetches hospital/healthcare facilities near KMCH from OpenStreetMap's
Overpass API and lands the raw JSON response in the landing zone. Does
not parse -- that's extract_load_api_osm.py's job.

NOT YET LIVE-VERIFIED in this build: the public overpass-api.de instance
(and its lz4 mirror) returned HTTP 406 on every request tested on
2026-10-26, confirmed from both this container and the host machine
directly (not a Docker networking issue) -- a block on this network
origin by Overpass's own infrastructure, unrelated to this code. Same
class of issue as DDS's backend outage: code-complete, wrapped in
run_pipeline.run_live_source() so it fails gracefully, worth retrying
later rather than giving up on. ingest_api_osrm.py does not hard-depend
on this succeeding -- it always computes distance to the fixed KMCH
coordinate regardless of whether OSM discovery has run.
"""

import math

import requests

import landing_store

KMCH_LAT, KMCH_LON = 13.732307519058327, 100.78967253963812
SEARCH_RADIUS_KM = 50  # matches kmch-ml's own confirmed radius pattern
OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def _bbox(lat: float, lon: float, radius_km: float) -> tuple[float, float, float, float]:
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * math.cos(math.radians(lat)))
    return (lat - dlat, lon - dlon, lat + dlat, lon + dlon)


def run() -> None:
    south, west, north, east = _bbox(KMCH_LAT, KMCH_LON, SEARCH_RADIUS_KM)
    query = (
        f"[out:json][timeout:60];"
        f"("
        f"nwr[amenity=hospital]({south},{west},{north},{east});"
        f"nwr[healthcare=hospital]({south},{west},{north},{east});"
        f");"
        f"out center tags;"
    )
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 clinical-dwh-geo-access/1.0"})
    resp = session.post(OVERPASS_URL, data={"data": query}, timeout=90)
    resp.raise_for_status()

    key, is_new = landing_store.save_version("geo_access", "osm_hospitals", "json", resp.content)
    status = "landed new version" if is_new else "unchanged, already landed"
    print(f"[ingest_api_osm] {status}: {key}")


if __name__ == "__main__":
    run()

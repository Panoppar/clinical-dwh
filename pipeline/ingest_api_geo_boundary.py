"""Fetches Thailand's canonical administrative-boundary reference data
(subdistrict/district CSVs with centroid coordinates, plus the full ADM3
polygon GeoJSON) and lands each raw file in the landing zone. Does not
parse -- that's extract_load_api_geo_boundary.py's job.

Source: DevelopedbyWill/thailand-canonical-admin-names (GitHub, public,
CC BY 4.0) -- this is the same canonical public dataset kmch-ml's own
kmch_phase1_dim_area module pulls from, fetched independently here rather
than reading kmch-ml's own repo (matches every other source in this
project: self-contained ingestion, no cross-repo coupling).
"""

import requests

import landing_store

GEO_BOUNDARY_BASE = "https://raw.githubusercontent.com/DevelopedbyWill/thailand-canonical-admin-names/main/data/v1.0.0"
GEO_BOUNDARY_FILES = {
    "subdistrict": ("thailand-adm3-subdistricts-v1.0.0.csv", "csv"),
    "district": ("thailand-adm2-districts-v1.0.0.csv", "csv"),
    "polygon": ("thailand-adm3-polygons-v1.0.0.geojson", "geojson"),
}


def run() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 clinical-dwh-geo-boundary/1.0"})
    for stem, (filename, ext) in GEO_BOUNDARY_FILES.items():
        resp = session.get(f"{GEO_BOUNDARY_BASE}/{filename}", timeout=60)
        resp.raise_for_status()
        key, is_new = landing_store.save_version("geo_boundary", stem, ext, resp.content)
        status = "landed new version" if is_new else "unchanged, already landed"
        print(f"[ingest_api_geo_boundary] {filename}: {status}: {key}")


if __name__ == "__main__":
    run()

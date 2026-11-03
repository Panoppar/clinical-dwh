"""Lands a user-supplied copy of thailand-adm3-polygons-v1.0.0.geojson into
the landing zone, under the SAME prefix/stem ("geo_boundary"/"polygon")
that ingest_api_geo_boundary.py's live GitHub fetch already uses. File-based,
not a live API -- a manual override of that one file, same pattern as
ingest_file_bma_zone_districts.py.

landing_store's content-hash dedup means this is safe to run regardless of
whether the live fetch has already landed the same bytes: if identical,
nothing changes (is_new=False); if different, this becomes the new latest
version that extract_load_api_geo_boundary.py's _load_polygon() picks up
on its next run -- no Bronze/Silver/Gold code change needed, since those
already read via landing_store.latest_version("geo_boundary", "polygon", "geojson").

Source file lives at external-inputs/thailand-adm3-polygons-v1.0.0.geojson
(bind-mounted, read-only -- update the file in place to refresh without
rebuilding the elt-runner image).
"""

import os

import landing_store

SOURCE_PATH = "/app/external-inputs/thailand-adm3-polygons-v1.0.0.geojson"


def run() -> None:
    with open(SOURCE_PATH, "rb") as f:
        content = f.read()
    key, is_new = landing_store.save_version("geo_boundary", "polygon", "geojson", content)
    status = "landed new version" if is_new else "unchanged, already landed (identical to the live-fetched copy)"
    print(f"[ingest_file_geo_boundary_polygon] {os.path.basename(SOURCE_PATH)}: {status}: {key}")


if __name__ == "__main__":
    run()

"""Lands kmch_catchment_places.csv into the landing zone. File-based, not a
live API -- a user-supplied list of places (housing estates, schools,
industrial sites, markets, etc.) near KMCH with distance/travel-time and a
market-potential label, same pattern as ingest_file_bma_zone_districts.py.

Landing only for now -- no Bronze/Silver/Gold shred yet.

Source file lives at external-inputs/kmch_catchment_places.csv
(bind-mounted, read-only -- update the file in place to refresh without
rebuilding the elt-runner image).
"""

import os

import landing_store

SOURCE_PATH = "/app/external-inputs/kmch_catchment_places.csv"


def run() -> None:
    with open(SOURCE_PATH, "rb") as f:
        content = f.read()
    key, is_new = landing_store.save_version("kmch_catchment_places", "kmch_catchment_places", "csv", content)
    status = "landed new version" if is_new else "unchanged, already landed"
    print(f"[ingest_file_kmch_catchment_places] {os.path.basename(SOURCE_PATH)}: {status}: {key}")


if __name__ == "__main__":
    run()

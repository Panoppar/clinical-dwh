"""Lands the BMA zone-district mapping into the landing zone. File-based,
not a live API -- a deliberate, scoped exception, same pattern as
bronze.tambon_xwalk (see sql/bronze/17's header for why).
"""

import os

import landing_store

PATH = "/app/external-inputs/bma_zone_districts.csv"


def run() -> None:
    with open(PATH, "rb") as f:
        content = f.read()
    key, is_new = landing_store.save_version("bma_zone_districts", "zone_districts", "csv", content)
    status = "landed new version" if is_new else "unchanged, already landed"
    print(f"[ingest_file_bma_zone_districts] {os.path.basename(PATH)}: {status}: {key}")


if __name__ == "__main__":
    run()

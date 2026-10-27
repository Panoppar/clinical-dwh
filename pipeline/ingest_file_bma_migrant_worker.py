"""Lands the BMA migrant-worker-permit file into the landing zone.
File-based, not a live API -- a deliberate, scoped exception (kmch-ml
input-parity gap 2, see docs/06_kmch_ml_gap_closure_plan.md).

Source file lives at external-inputs/bma_migrant_worker_2568.csv
(bind-mounted, read-only, same pattern sql/ already uses). Original
filename was "ข้อมูลแรงงานต่างด้าว.xlsx - 2568.csv" -- renamed for a
pipeline-friendly path, same content.
"""

import os

import landing_store

SOURCE_PATH = "/app/external-inputs/bma_migrant_worker_2568.csv"


def run() -> None:
    with open(SOURCE_PATH, "rb") as f:
        content = f.read()
    key, is_new = landing_store.save_version("bma_migrant_worker", "bma_migrant_worker_2568", "csv", content)
    status = "landed new version" if is_new else "unchanged, already landed"
    print(f"[ingest_file_bma_migrant_worker] {os.path.basename(SOURCE_PATH)}: {status}: {key}")


if __name__ == "__main__":
    run()

"""Lands the DDS health-region weekly disease ranking PDFs (skr6/skr13,
2022-2026) into the landing zone. File-based, not a live API -- a stand-in
for api_dds_disease_ranking while DDS's own province-grain backend stays
down (confirmed outage since 2026-10-25, see ingest_api_dds.py). Does not
parse -- that's extract_load_file_dds_health_region.py's job.

These are the exact files a prior version of this project's Bronze/Silver
layer ingested as pre-converted CSVs (see git history at commit 22ab956^,
sql/bronze/06_create_bronze_dds_health_region_tables.sql) before being
pruned when this project switched to the live DDS API. Re-introduced here
parsing the RAW PDFs directly (no manual CSV conversion step), since that's
what's actually available now.

Source files live at external-inputs/dds_health_region/*.pdf (bind-mounted,
read-only -- add/update files in place to refresh without rebuilding the
elt-runner image).
"""

import os

import landing_store

SOURCE_DIR = "/app/external-inputs/dds_health_region"


def run() -> None:
    if not os.path.isdir(SOURCE_DIR):
        print(f"[ingest_file_dds_health_region] {SOURCE_DIR} not found, skipping")
        return

    filenames = sorted(f for f in os.listdir(SOURCE_DIR) if f.endswith(".pdf"))
    if not filenames:
        print(f"[ingest_file_dds_health_region] no PDFs found in {SOURCE_DIR}, skipping")
        return

    for filename in filenames:
        stem = filename.removesuffix(".pdf")
        path = os.path.join(SOURCE_DIR, filename)
        with open(path, "rb") as f:
            content = f.read()
        key, is_new = landing_store.save_version("dds_health_region", stem, "pdf", content)
        status = "landed new version" if is_new else "unchanged, already landed"
        print(f"[ingest_file_dds_health_region] {filename}: {status}: {key}")


if __name__ == "__main__":
    run()

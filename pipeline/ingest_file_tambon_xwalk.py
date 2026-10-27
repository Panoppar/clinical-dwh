"""Lands xwalk_tambon_unit.csv into the landing zone. File-based, not a
live API -- a deliberate, scoped exception to this project's live-API-only
scope (see docs/06_kmch_ml_gap_closure_plan.md, Gap 4). This is kmch-ml's
own authoritative tambon-to-merged-unit mapping (which original TIS-1099
subdistrict codes collapse into which gold.dim_area unit_code, including
the 7 Bangkok post-2019 khwaeng-split groups) -- not derivable from
anything already landed from a live source, so it's supplied as a file.

Source file lives at external-inputs/xwalk_tambon_unit.csv (bind-mounted,
read-only, same pattern sql/ already uses -- update the file in place to
refresh without rebuilding the elt-runner image).
"""

import os

import landing_store

SOURCE_PATH = "/app/external-inputs/xwalk_tambon_unit.csv"


def run() -> None:
    with open(SOURCE_PATH, "rb") as f:
        content = f.read()
    key, is_new = landing_store.save_version("tambon_xwalk", "xwalk_tambon_unit", "csv", content)
    status = "landed new version" if is_new else "unchanged, already landed"
    print(f"[ingest_file_tambon_xwalk] {os.path.basename(SOURCE_PATH)}: {status}: {key}")


if __name__ == "__main__":
    run()

"""Lands DOPA population files into the landing zone. File-based, not a
live API -- a deliberate, scoped exception to this project's live-API-only
scope (see docs/06_kmch_ml_gap_closure_plan.md, Gap 1). This is the
previously-deferred "DOPA population" gap, now built from files supplied
directly rather than a live crawl.

Two files, landed under the same "dopa_population" prefix:
  dim_population_year.csv: fine/coarse age-sex bands, 9 years, all 312
    dim_area units (Bangkok already complete for 2560-2568).
  pop_total_supplement_2560_2564.csv: pop_total only, backfills the 5
    years (2560-2564) missing from the main file for Samut Prakan/
    Chachoengsao units specifically -- confirmed a clean, non-overlapping
    union with the main file before this was built, not a conflict.

Both bind-mounted at external-inputs/, read-only, same pattern sql/
already uses -- update either file in place to refresh without rebuilding
the elt-runner image.
"""

import os

import landing_store

YEAR_PATH = "/app/external-inputs/dim_population_year.csv"
SUPPLEMENT_PATH = "/app/external-inputs/pop_total_supplement_2560_2564.csv"


def run() -> None:
    for stem, path in (("year", YEAR_PATH), ("supplement", SUPPLEMENT_PATH)):
        with open(path, "rb") as f:
            content = f.read()
        key, is_new = landing_store.save_version("dopa_population", stem, "csv", content)
        status = "landed new version" if is_new else "unchanged, already landed"
        print(f"[ingest_file_dopa_population] {os.path.basename(path)}: {status}: {key}")


if __name__ == "__main__":
    run()

"""Lands the DOPA population supplement file into the landing zone.
File-based, not a live API -- a deliberate, scoped exception (same
category as the tambon-unit crosswalk), kept permanently because it's a
historical backfill DOPA's own site has no live equivalent for.

pop_total_supplement_2560_2564.csv: pop_total only, backfills the 5 years
(2560-2564) missing from the main series for Samut Prakan/Chachoengsao
units specifically -- confirmed a clean, non-overlapping union with the
main series before this was built, not a conflict.

The main series itself (fine/coarse age-sex bands, current year) moved to
a live source on 2026-10-28 -- see ingest_api_dopa_population.py and
docs/06_kmch_ml_gap_closure_plan.md (kmch-ml input-parity gap 1).

Bind-mounted at external-inputs/, read-only, same pattern sql/ already
uses -- update the file in place to refresh without rebuilding the
elt-runner image.
"""

import os

import landing_store

SUPPLEMENT_PATH = "/app/external-inputs/pop_total_supplement_2560_2564.csv"


def run() -> None:
    with open(SUPPLEMENT_PATH, "rb") as f:
        content = f.read()
    key, is_new = landing_store.save_version("dopa_population", "supplement", "csv", content)
    status = "landed new version" if is_new else "unchanged, already landed"
    print(f"[ingest_file_dopa_population] {os.path.basename(SUPPLEMENT_PATH)}: {status}: {key}")


if __name__ == "__main__":
    run()

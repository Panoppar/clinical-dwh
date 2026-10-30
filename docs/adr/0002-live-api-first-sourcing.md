# 0002 — Live-API-first sourcing, file-based as a scoped exception

## Status
Accepted

## Context
An earlier phase of this project was built around a shared Drive folder of
static files (DOPA population, HDC/DDS manual exports, Lat Krabang district
data, factory lists, and more). That approach meant every refresh required
someone to manually re-export and re-upload a file — the warehouse was only
ever as current as the last manual export, and had no way to detect that a
source had actually changed.

Later, two more sources (BMA migrant worker permits, DOPA population) were
re-closed as one-time file snapshots during active gap-closure work, under
time pressure, with the explicit understanding that a live equivalent would
be investigated afterward if one existed.

## Decision
Default every new source to a live API call this pipeline makes itself,
discovered and verified by hand (direct `requests` calls, browser network
inspection when a WAF blocks generic clients) before writing ingest code —
never assumed from a source's public-facing website alone. File-based
ingestion is kept only as a **deliberate, scoped exception** for data that
is genuinely unavailable any other way:
- `tambon_xwalk` — a specific, one-time crosswalk export from kmch-ml's own
  prior work, not a publication with a fetchable endpoint.
- `dopa_population_supplement` — backfills 5 historical years for 2
  provinces that DOPA's own live download portal only ever publishes the
  *current* year for; there's no live endpoint for that history.

Both of the time-pressured file-based sources above (DOPA population, BMA
migrant worker permits) were converted to live sources once the pipeline's
other gaps were closed, after confirming live endpoints existed via direct
testing (see [docs/06](../06_kmch_ml_gap_closure_plan.md)'s "Post-closure"
section for the investigation).

## Consequences
- Every live source needed its own hand-verified discovery pass — several
  required a browser-like `User-Agent` to clear a WAF (NSO, DOE, DOPA), one
  required reverse-engineering a PDF's font-level text encoding (DOE), and
  one required testing a chained, undocumented JSON API before abandoning
  it for a simpler static-file download (DOPA — see
  [docs/06](../06_kmch_ml_gap_closure_plan.md)).
- A pipeline run now reflects whatever is live *right now* — no stale
  manual export silently going unnoticed.
- Two sources (DDS, OSM/Overpass) are currently blocked at the source
  (confirmed server-side/network-level, not this code) and simply log a
  warning and skip each run — accepted as the cost of depending on
  external infrastructure not under this project's control, rather than
  reverting to a file-based fallback for sources that *should* be live.
- The 2 remaining file-based exceptions are intentionally permanent, not a
  backlog item — there is no live equivalent to convert them to.

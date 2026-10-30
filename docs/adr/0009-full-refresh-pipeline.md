# 0009 — Full-refresh pipeline (drop + recreate every run)

## Status
Accepted

## Context
A pipeline that incrementally upserts needs to track what's already been
loaded, handle out-of-order or re-sent source data, and reconcile schema
changes against existing rows — real complexity, and a real source of
subtle bugs if any one source's incremental logic has an edge case. This
project's actual data volumes are small (largest Bronze/Silver/Gold table
around 163K rows) and most sources either publish one full snapshot per
run (DOE's monthly PDF, DOPA's population file) or are cheap enough to
re-fetch in full every time.

A surgical, standalone rebuild of just one table was tried mid-project
(rebuilding `dim_area` alone, without the full pipeline) and caused a real
bug: `fact_hospital_access`'s FK-referenced surrogate keys silently ended
up pointing at reshuffled rows after `dim_area`'s own keys changed shape,
because nothing re-ran to re-resolve that downstream dependency.

## Decision
Every layer's SQL script does `DROP TABLE IF EXISTS` + `CREATE TABLE` for
its own tables, every run. `docker compose run --rm elt-runner` is fully
idempotent — re-running it is always safe, and is the normal way to pick
up anything new, not a special "reset" operation. There is no incremental
load path at all.

## Consequences
- No incremental-load state to debug — "did this row already load" is
  never a question, because every table is empty immediately before its
  own load step runs.
- A full run costs real time (15-25 minutes, dominated by HDC's throttled
  ~1,100-request crawl) — accepted as the cost of simplicity at this data
  volume; would need revisiting if either the source count or per-source
  volume grew by an order of magnitude.
- Any ad-hoc, single-table rebuild (skipping the full pipeline) is a known
  foot-gun, not a supported shortcut — confirmed by the `dim_area` incident
  above. The documented lesson: check `information_schema` for anything
  with an FK into a table before assuming a surgical rebuild of just that
  table is complete; when in doubt, re-run the full pipeline instead.
- Content-addressed landing-zone versioning (see
  [0004](0004-content-addressed-landing-versioning.md)) is what keeps a
  full-refresh-every-run pipeline from being wasteful on the *fetch* side,
  even though every *load* is from scratch.

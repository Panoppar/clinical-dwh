# 0001 — Medallion architecture (Bronze / Silver / Gold)

## Status
Accepted

## Context
This warehouse ingests from a dozen heterogeneous external sources (government
JSON/XLS APIs, scraped PDFs, static reference files) with wildly different raw
shapes — pipe-delimited government exports, Excel sheets with stacked
multi-section tables, PDF text with font-level encoding quirks. Those raw
shapes don't match the clean, normalized star schema that Metabase dashboards
and kmch-ml's feature pulls actually need. Something has to sit between "what
a source gives us" and "what a consumer wants to query."

## Decision
Three MySQL schemas, each a distinct layer with a specific contract:

- **`bronze`** — near-raw, 1:1 with the source. Every column is `raw_*`,
  typically `VARCHAR`, with lineage columns (`source_file_name`,
  `ingestion_batch_id`, `file_hash`, `ingested_at`) on every row. No
  casting, no joins, no business logic. If a source's PDF spells a number
  with a stray embedded space, Bronze still has that stray space — fixing
  it is Silver's job, not Bronze's.
- **`silver`** — cleansed and conformed. Text cast to real types, codes
  resolved, duplicate/derivable rows dropped (e.g. grand-total rows that are
  exactly the sum of their own breakdown). Still close to source grain, not
  yet joined into the star schema.
- **`gold`** — the star schema: dimensions and facts, built for query. This
  is the *only* layer any consumer (Metabase, kmch-ml) is allowed to touch.

Every layer is a **full refresh** on each pipeline run (see
[0009](0009-full-refresh-pipeline.md)) — each layer's own SQL script drops
and recreates its own tables, so there's no incremental-load state machine
to get wrong.

## Consequences
- A source's own format quirks (embedded whitespace, decomposed Thai
  vowels, PUA-remapped tone marks) are debugged once, in one Silver
  transform, instead of leaking into every downstream query.
- Lineage is never lost — any Gold row's provenance can be traced back
  through Silver to the exact Bronze row, source file, and ingestion batch
  that produced it.
- Three schemas to migrate/reason about instead of one — more DDL files,
  more layers to keep in sync when a source's shape changes (see
  [0005](0005-eav-grain-for-volatile-schemas.md) for how volatile source
  shapes are handled without rippling that cost through all three layers).
- A bug discovered in Gold often means re-running Silver, not just patching
  Gold directly — intentional, since patching Gold directly would make it
  diverge from what a full pipeline re-run produces.

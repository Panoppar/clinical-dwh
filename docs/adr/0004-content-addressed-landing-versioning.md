# 0004 — Content-addressed versioning for landed raw data

## Status
Accepted

## Context
Running the pipeline repeatedly (daily cron, or manual re-runs while
iterating) means calling the same live endpoints over and over. Most of the
time a source's answer hasn't actually changed since the last run. Landing
a fresh, identically-named object every single run would make the landing
zone grow unboundedly even when nothing changed, and would make it hard to
tell *which* landed object actually corresponds to a real change versus
just another identical re-fetch.

## Decision
`landing_store.save_version()` hashes the content (SHA-256) before writing.
If an object with that exact hash already exists under the given
prefix/stem, nothing new is written — the existing key is returned with
`is_new=False`. A new version is only ever written when the source's actual
answer changed. Keys encode `<stem>__<date>_<hash short>.<ext>` so the
history under one prefix is both human-browsable (by date) and
content-verifiable (by hash) without needing a separate manifest.

This pattern was adapted from kmch-ml's own prior `raw_store.py`
(`Paiiyahh/kmch-ml`, private repo) — same append-only, content-addressed
contract, backed by SeaweedFS's S3 API instead of local files.

## Consequences
- Re-running the pipeline against an unchanged source is cheap in storage —
  the common case (nothing changed) adds nothing to the landing zone.
- A genuine change is unambiguous: a new key with a new hash appears,
  distinguishable from "ran again, same answer" entries.
- Extract/load scripts always need an explicit "find the latest version"
  step (`latest_version()`, or listing-and-sorting by the date suffix for
  sources with a variable stem like DOE's monthly report) rather than
  assuming a single well-known key — a small but consistent extra piece of
  logic every extract_load script carries.
- The landing zone is a secondary artifact, not the source of truth — the
  warehouse itself (via `ingestion_batch_id`/`source_file_name` lineage
  columns) is what actually matters for provenance; the landing zone backs
  that up but is treated as re-derivable (confirmed explicitly in the
  runbook's backup-priority guidance) for every live source.

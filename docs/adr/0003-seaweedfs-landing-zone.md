# 0003 — SeaweedFS as the S3-compatible landing zone

## Status
Accepted

## Context
Every live-API and file-based Bronze source needs somewhere to land its raw
response *before* Bronze shreds it into relational tables — both so Bronze
loading can be re-run without re-fetching the source, and so there's an
inspectable raw artifact for debugging when a source's shape changes
unexpectedly. An S3-compatible object store was the natural fit (simple
put/get/list semantics, versioning, no schema to manage). MinIO was the
original choice.

MinIO's free container distribution was discontinued across every registry
checked (Docker Hub, quay.io, direct binary download) as of this build,
confirmed by direct testing — not available to pull at all, not a licensing
change that could be worked around.

## Decision
Use SeaweedFS instead, in its all-in-one mode (`server -s3`), exposing both
the S3 API (port 8333) and its own Filer web UI (port 8888) as a free,
actively-maintained alternative with the same S3-compatible semantics
`pipeline/landing_store.py` needs.

## Consequences
- `landing_store.py` only talks to the backend via the S3 API (`boto3`), so
  swapping backends again later (back to MinIO, or to real AWS S3) needs no
  code change — only a `docker-compose.yml`/`.env` change.
- Gained SeaweedFS's own Filer web UI "for free" (folders by source,
  file download/preview) — not originally planned for, but useful for
  manually inspecting what a source actually landed without a separate S3
  client.
- Authentication is a separate config file (`seaweedfs_s3_config.json`,
  not env-templated) read directly by the SeaweedFS binary, which must be
  kept in sync with `.env`'s `LANDING_ACCESS_KEY`/`LANDING_SECRET_KEY` by
  hand — a minor rough edge from the backend swap, since MinIO's own
  config style differed.

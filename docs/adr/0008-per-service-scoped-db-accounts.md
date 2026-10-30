# 0008 — Per-service MySQL accounts with schema-scoped grants

## Status
Accepted

## Context
Multiple distinct consumers need database access for different purposes:
the pipeline itself needs full read/write across all three layers;
Metabase needs read-only access to Gold only (see
[0006](0006-metabase-gold-only-access.md)); kmch-ml's training pipeline
also needs read-only Gold access, as a separate consumer from Metabase.
Handing every consumer the same root-equivalent credential would make it
impossible to reason about (or audit) what any one consumer is actually
capable of doing.

## Decision
Every consumer gets its own MySQL account, scoped to exactly what it
needs, created in `sql/00_init_schemas_and_grants.sql`:

- `dwh_elt` — `ALL PRIVILEGES` on `bronze`/`silver`/`gold`. Used only by
  `elt-runner`, never handed to any read-facing tool.
- `metabase_ro` — `SELECT` on `gold.*` only.
- `kmch_ml_ro` — `SELECT` on `gold.*` only, same model as `metabase_ro`,
  a distinct account rather than sharing `metabase_ro`'s credential so
  each consumer's access can be rotated or revoked independently.

Passwords are environment-templated (`.env`) for the services docker-compose
manages directly, but the grants themselves are plain SQL — this file only
runs once, on first container boot, so a password change here requires
updating both `.env` and this file to match, documented inline at each
account's definition.

## Consequences
- A compromised or misconfigured read-only consumer (Metabase, kmch-ml)
  cannot write to or read from bronze/silver even in the worst case.
- Adding a new consumer is a well-worn, two-line pattern (`CREATE USER` +
  one `GRANT`) rather than a design decision each time.
- Because the init script only fires on a schema's *first* boot, adding a
  new account to an already-initialized database (as happened when
  `kmch_ml_ro` was added) requires running the same `CREATE USER`/`GRANT`
  statements by hand against the live database too — a manual step to
  remember on any environment that was seeded before the account was added
  to the init script.

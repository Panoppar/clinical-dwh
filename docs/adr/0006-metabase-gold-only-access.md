# 0006 — Metabase restricted to gold-schema-only via a dedicated account

## Status
Accepted

## Context
Metabase is the BI tool end users interact with directly, building their
own ad-hoc questions and dashboards against whatever database connection
it's given. Bronze and Silver carry intermediate, not-yet-conformed data —
raw text columns, pre-join grain, duplicate/derivable rows deliberately
excluded further downstream. A user building a dashboard against Bronze or
Silver by mistake (or by not understanding the layer distinction) would
get numbers that don't match Gold's own aggregates, with no indication
anything was wrong.

## Decision
Metabase connects through a dedicated MySQL account (`metabase_ro`) granted
`SELECT` on `gold.*` only — no grant on `bronze.*` or `silver.*` at all.
This is enforced at the database-credential level, not just by convention
or UI configuration: even if someone adds a second Metabase database
connection pointed at bronze or silver by mistake, those credentials
physically cannot read anything outside gold.

## Consequences
- The "BI tool only ever sees Gold" rule can't be silently violated by a
  configuration mistake — the enforcement lives in the grant, not in
  anyone remembering a convention.
- Any new consumer that needs read access to the warehouse gets the same
  treatment rather than being handed the full `dwh_elt` credential — see
  [0008](0008-per-service-scoped-db-accounts.md), which generalizes this
  pattern (the `kmch_ml_ro` account follows it exactly).
- Metabase cannot be used to debug a Bronze/Silver data-quality issue
  directly — that still requires the `dwh_elt` credential via a direct
  `mysql` client, which is an intentional friction, not an oversight.

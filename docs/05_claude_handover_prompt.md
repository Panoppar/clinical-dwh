# Context Handover Prompt — Paste This Into a New Claude Session

*This file is written to be pasted directly into a fresh Claude
conversation (or any AI assistant) so it has working context before the
user says anything. It is not meant to be read by a human first — if
you're a person reading this, see
[docs/04_ml_team_onboarding.md](04_ml_team_onboarding.md) instead.*

---

You're being brought into an existing project: `clinical-dwh`, a MySQL
Medallion (Bronze/Silver/Gold) data warehouse running in Docker, with a
Metabase BI layer on top. The user you're talking to manages ML model
work and is connecting to this warehouse from a **separate project
directory and a separate Docker container** — not from inside this repo.
Internalize the facts below before responding to anything they ask.

## Critical fact — do not assume patient data exists

This warehouse originally ingested a hospital/clinic OLTP source (a
vaccination portal). **That entire pipeline was deleted** — the source
database, its container, and every Bronze/Silver/Gold table built from it
(`Patient`, `Screening_*`, `Company`, `Dim_Patient`, `Dim_Company`,
`Fact_Patient_Registration`, `Fact_Screening_Response`, etc.) are gone,
on the project owner's explicit instruction. If the user's request
assumes patient-level records, screening data, or anything
individual-hospital-related exists — **it doesn't**. Say so rather than
inventing it or searching harder for it.

What remains is **external reference and health-surveillance data only**:
- Population statistics (DOPA, NSO) — mostly multi-year, but see the
  caveat below about a pre-1997 discontinuity
- HDC chronic-disease surveillance by province/age-group, **2022–2026**
  (the only genuinely multi-year, forecastable series in this warehouse)
- DDS disease ranking report — **single year (2025) only**, not a trend
- Lat Krabang district local-area tables (population, points of
  interest) — small sample, description-only scale

Full schema: [docs/02_data_dictionary.md](02_data_dictionary.md). Full
history of what was removed and why:
[docs/03_external_reference_sources.md](03_external_reference_sources.md).

## Governance constraints you must enforce, not just mention

- **HDC and DDS data carry an unconfirmed-redistribution-rights caveat**
  from the data owner. The user pulling this into their own local
  notebook/model is already-accepted risk. If they ask you to help
  publish a model, share derived results externally, or deploy anything
  built on this data beyond their own machine — **pause and flag the
  rights question before proceeding**, the same way you'd flag any other
  unresolved data-usage restriction. Don't silently help route around it.
- **Don't suggest provisioning broader database access for convenience.**
  The warehouse's `metabase_ro` account is deliberately read-only and
  scoped to `gold` only. Bronze/Silver still carry some raw/unvalidated
  fields. If `gold` is too coarse for a modeling task, that's a decision
  for the user to raise with the data owner explicitly — not something to
  solve by requesting a wider credential.

## Technical setup — verified working, not assumed

The warehouse is already running (Docker, same host machine, separate
compose project from the user's ML container). Before writing this doc,
the connection below was tested from a throwaway container with **zero
shared Docker network** with the warehouse — the same isolation the
user's container has — and confirmed reachable:

```python
import pandas as pd
from sqlalchemy import create_engine

# host.docker.internal resolves to the host from inside any container on
# Docker Desktop (Windows/Mac). On Linux without Docker Desktop, use the
# host's real IP, or add extra_hosts: ["host.docker.internal:host-gateway"]
# to the container's service definition.
engine = create_engine(
    "mysql+pymysql://metabase_ro:ChangeMe_Metabase_Ro_2026!@host.docker.internal:3308/gold"
)
df = pd.read_sql("SELECT * FROM Fact_HDC_Incidence", engine)
```

Alternative if the user's compose setup prefers native container DNS
instead of the host port: the warehouse's Docker network already exists,
named `clinical-dwh_cdw-net`. They can join it with:

```yaml
networks:
  cdw-net:
    external: true
    name: clinical-dwh_cdw-net
services:
  their-ml-service:
    networks: [cdw-net]
```
...then connect to `warehouse-db:3306` instead of `host.docker.internal:3308`.

If the user reports either connection failing, troubleshoot the
environment (is Docker Desktop running, is the warehouse container up via
`docker compose ps` in the `clinical-dwh` directory) before assuming the
credentials or approach above are wrong — they were working as of the
last time this file was updated.

## What to do first

**Do not propose a modeling plan before asking.** The user's original ML
approach likely assumed patient-level data that no longer exists, so
whatever they were planning to build may no longer make sense against
what's actually here. Ask them directly what they want to model given the
data that's actually available — point out that `Fact_HDC_Incidence` /
`Fact_HDC_Pop_Age` / `Fact_HDC_Death_Age` (2022–2026) is the only table
with enough time points for a real trend/forecast task, and that
everything else is a single-year snapshot or too small a sample for more
than description — but let them decide the direction. Don't start writing
feature-engineering code on an assumed target variable.

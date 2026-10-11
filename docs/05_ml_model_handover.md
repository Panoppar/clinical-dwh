# Handover — Data Warehouse for ML Model Work

Hi! You already have the `clinical-dwh` repo, but a lot changed since you
last looked. This doc gets you caught up and connected without you having
to redo any of the setup — everything below is already running and
already tested from a container outside this project, the same situation
yours is in.

## ⚠️ Read this part first

**The clinic/patient data is gone.** If you were expecting patient
records, screening responses, or anything resembling individual-level
hospital data — it doesn't exist anymore. That entire pipeline (source
database, container, and every table built from it) was deleted on
purpose. What's left is **external reference and health-surveillance
data only**: population statistics (DOPA/NSO), chronic-disease
surveillance by province/age-group (HDC), a disease ranking report (DDS),
and local-area tables for Lat Krabang district. See
[docs/03_external_reference_sources.md](03_external_reference_sources.md)
for the full record of what happened and why.

**Two of those data sources (HDC, DDS) carry a usage-rights caveat** — the
data owner hasn't confirmed redistribution rights. You can pull this data
into your own local work (that's the same use the warehouse owner already
accepted the risk for), but if you're thinking about publishing a model or
sharing derived results outside your own machine, raise that with
whoever owns this data first. Full detail in
[docs/04_ml_team_onboarding.md §5](04_ml_team_onboarding.md).

## 1. Get caught up

```powershell
cd <your-clone-of-clinical-dwh>
git pull
git log --oneline -1
# should show a6f145e or later: "Remove clinic/patient pipeline entirely..."
```

If you're more than a couple commits behind, skim the commit messages
(`git log --oneline -15`) — several of them document real bugs that got
caught and fixed (ambiguous SQL joins that silently produced zero rows,
a pre-summed "total" row that would have doubled a population count).
Worth knowing before you build on top of this data.

## 2. The warehouse is already running — you don't need to build it

The warehouse (`warehouse-db` + `metabase`, both in Docker on this same
machine) is already up, already loaded, and already validated. You do
**not** need to run `docker compose up` or `docker compose run elt-runner`
yourself unless you specifically want to rebuild it. Just connect to it.

## 3. Connecting from your separate container (tested, not theoretical)

Since your ML project is its own directory and its own container, not
part of this repo's Docker network, I tested the exact scenario you're
in: a throwaway container with **no connection to this project's Docker
network** reaching the warehouse purely through the host-mapped port.
It works:

```python
import pandas as pd
from sqlalchemy import create_engine

# host.docker.internal resolves to the host machine from inside any
# Docker container on Docker Desktop (Windows/Mac). If your ML container
# runs on Linux without Docker Desktop, use the host's actual IP instead,
# or add `extra_hosts: ["host.docker.internal:host-gateway"]` to your
# container's service definition.
engine = create_engine(
    "mysql+pymysql://metabase_ro:ChangeMe_Metabase_Ro_2026!@host.docker.internal:3308/gold"
)

population = pd.read_sql("SELECT * FROM Dim_District_Population", engine)
hdc_incidence = pd.read_sql("SELECT * FROM Fact_HDC_Incidence", engine)
```

This account (`metabase_ro`) is read-only and scoped to the `gold` schema
only — it physically cannot see raw/intermediate tables, so you can't
accidentally pull something half-cleaned. If `gold` turns out to be too
coarse for what you need, that's a real conversation to have (not a
credential to quietly work around) — see
[docs/04_ml_team_onboarding.md §3](04_ml_team_onboarding.md).

**If you'd rather join the warehouse's own Docker network** instead of
going through the host port (e.g. your compose setup prefers native
container-to-container DNS), the network is named
`clinical-dwh_cdw-net` and already exists. Add this to your own
`docker-compose.yml`:

```yaml
networks:
  cdw-net:
    external: true
    name: clinical-dwh_cdw-net

services:
  your-ml-service:
    networks:
      - cdw-net
```

Then connect to `warehouse-db:3306` instead of `host.docker.internal:3308`.
Either approach works — the host-port one above needs zero changes to
your compose file, so start there unless you have a reason not to.

## 4. What's actually in there for you to model

Full column-level detail is in
[docs/02_data_dictionary.md](02_data_dictionary.md). Short version: the
**only genuinely multi-year table** is `Fact_HDC_Incidence` /
`Fact_HDC_Pop_Age` / `Fact_HDC_Death_Age` (2022–2026, chronic disease
surveillance for Samut Prakan and Chachoengsao). Everything else is a
single-year snapshot or too small a sample for anything beyond
description — `docs/04_ml_team_onboarding.md §6` has the specific gotchas
(undocumented age-group boundaries, a pre-1997 data discontinuity in the
population series, etc.) worth reading before you pick a target variable.

## Your call — what's next?

Given the clinic data is gone and what's left is population/surveillance
data instead, the ML use case has probably changed from whatever you were
originally planning. Before you put real time into feature engineering:
what do you actually want to model with this? A couple of directions that
fit the data as it stands — disease-incidence forecasting from the HDC
time series, or a province/district-level risk profile from the
population + disease data — but I don't want to guess at your priorities.
Let's talk it through before you build on an assumption.

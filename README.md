# Regional Health & Population Data Warehouse

A local, Dockerized Medallion (Bronze/Silver/Gold) ELT pipeline built
entirely from externally-sourced reference data: DOPA/NSO population
statistics, HDC/DDS health-facility surveillance, and Lat Krabang/KMCH
local-area tables, shared via a Google Drive folder. **No clinic/patient
source system feeds this warehouse** — an earlier phase of this project
did ingest a hospital portal's data, but that entire pipeline was removed
on explicit instruction; see
[docs/03_external_reference_sources.md](docs/03_external_reference_sources.md)
for the record of that.

```
external-sources/ (flat files from the shared Drive folder)
  --[elt-runner]--> warehouse-db.bronze
                  -> warehouse-db.silver
                  -> warehouse-db.gold --> Metabase
```

See [docs/01_architecture_c4.md](docs/01_architecture_c4.md) for the C4
context diagram, [docs/02_data_dictionary.md](docs/02_data_dictionary.md)
for the full Gold-layer data dictionary, and
[docs/03_external_reference_sources.md](docs/03_external_reference_sources.md)
for provenance — including a usage-rights caveat that applies to part of
this data (HDC/DDS health surveillance).

## Prerequisites

- Docker Desktop (with Compose v2)
- Several source files are gitignored (too large for git, or carrying a
  usage-rights caveat — see docs/03) and must be manually re-obtained from
  the shared Drive folder before the first pipeline run:
  `external-sources/dopa/stat_t.txt`, and everything under
  `external-sources/hdc_by_age/`, `hdc_occupational/`, `dds_extracted/`,
  `dds_pdf_inventory/`, `lat_krabang/`. Missing files cause only their own
  load step to fail — everything else still loads.

## 1. Configure environment

```powershell
Copy-Item .env.example .env
# Edit .env and change all ChangeMe_* passwords before any real use.
```

## 2. Start the warehouse and Metabase

```powershell
docker compose up -d warehouse-db metabase
```

Wait for the database to report healthy:

```powershell
docker compose ps
```

`warehouse-db` seeds itself from `sql/00_init_schemas_and_grants.sql`,
creating the `bronze` / `silver` / `gold` schemas and two accounts:

| Account | Scope | Used by |
|---|---|---|
| `dwh_elt` | full DML/DDL on bronze, silver, gold | elt-runner (pipeline runs as `root` locally for simplicity — see note below) |
| `metabase_ro` | `SELECT` on `gold.*` only | Metabase connection, and the ML onboarding doc's Python examples |

> **Note:** `docker-compose.yml` runs the `elt-runner` as the MySQL `root`
> user for local-dev simplicity (no extra credential wiring). The
> `dwh_elt` / `metabase_ro` least-privilege accounts are still created and
> are what you should actually enter into Metabase and any future
> non-root pipeline runner.

## 3. Run the ELT pipeline

The pipeline is a one-shot batch job (not a long-running daemon). Run it
whenever the source files change:

```powershell
docker compose run --rm elt-runner
```

This executes, in order:

1. **Bronze**: creates raw-replica tables, then loads every flat file
   under `external-sources/` (`pipeline/extract_load_external_reference.py`
   for DOPA/NSO/Thai-geo, `pipeline/extract_load_phase2.py` for
   HDC/DDS/Lat Krabang/KMCH/other-health).
2. **Silver**: creates cleansed/conformed tables and runs the
   standardization/deduplication transforms (`sql/silver/`).
3. **Gold**: creates the dimensional tables and populates them with
   `INSERT INTO ... SELECT` loads joining across Silver (`sql/gold/`).

It prints a row-count summary of every Bronze/Silver/Gold table on
success. The whole run is idempotent — rerun it any time without manual
cleanup.

## 4. Connect Metabase to the Gold schema

1. Open http://localhost:3000 (or your `METABASE_HOST_PORT`) and complete
   the first-run setup wizard.
2. Add a database connection:
   - **Database type**: MySQL
   - **Host**: `warehouse-db` (container network name — Metabase runs
     inside the same Docker network)
   - **Port**: `3306`
   - **Database name**: `gold`
   - **Username**: `metabase_ro`
   - **Password**: value of `DWH_METABASE_RO_PASSWORD` in your `.env`
3. Save. Metabase can now only see `gold.*` — `bronze`/`silver` are not
   reachable with this account, so "BI connects strictly to the Gold tier"
   is enforced by MySQL grants, not just dashboard discipline.
4. Build questions/dashboards against the Gold tables listed in
   [docs/02_data_dictionary.md](docs/02_data_dictionary.md). Four
   dashboards already exist (built via the Metabase API): Regional
   Population & Geography, HDC Chronic Disease Surveillance, DDS Disease
   Ranking, and Lat Krabang Local Area Profile. The HDC and DDS ones carry
   the usage-rights caveat directly in their dashboard description.

If you're here to pull data into Python/pandas for model development
instead of Metabase, see
[docs/04_ml_team_onboarding.md](docs/04_ml_team_onboarding.md).

## Project layout

```
clinical-dwh/
├── docker-compose.yml
├── .env.example
├── external-sources/          # flat-file reference data (DOPA/NSO, Thai geo, HDC/DDS, Lat Krabang, KMCH, other health)
├── sql/
│   ├── 00_init_schemas_and_grants.sql   # warehouse bootstrap (runs once)
│   ├── bronze/                # raw replica DDL for each source file group
│   ├── silver/                # cleanse/conform DDL + transforms
│   └── gold/                  # dimensional table DDL + dimension/fact loads
├── pipeline/                  # Python ELT orchestrator (elt-runner image)
└── docs/
    ├── 01_architecture_c4.md             # C4 context diagram (Mermaid)
    ├── 02_data_dictionary.md             # Gold layer data dictionary
    ├── 03_external_reference_sources.md  # provenance, scope decisions, governance trail
    └── 04_ml_team_onboarding.md          # clone-and-run guide for model development
```

## Rerunning / resetting

- **Rerun the pipeline** (e.g. after new files land in `external-sources/`):
  `docker compose run --rm elt-runner`
- **Full reset** (wipe all containers + volumes and start over):
  ```powershell
  docker compose down -v
  docker compose up -d warehouse-db metabase
  docker compose run --rm elt-runner
  ```

## Scaling beyond this prototype

This design optimizes for local-dev clarity on a dataset downloaded once
from a shared Drive folder, not for a live-feed production warehouse. If
that changes:

- **Automated refresh**: there is currently no scheduler — the pipeline
  runs only when someone manually triggers `docker compose run elt-runner`
  after re-downloading files. Add cron/Airflow/Dagster if the Drive folder
  starts getting real updates on a cadence.
- **Least-privilege credentials**: switch `elt-runner` from `root` to the
  `dwh_elt` account.
- **Usage-rights resolution**: the HDC/DDS data's redistribution status is
  still unconfirmed with its owner (see docs/03). Resolve that before this
  warehouse or its dashboards go anywhere beyond the person who accepted
  that risk.

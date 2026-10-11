# VaccineWork — Medallion Data Warehouse

A local, Dockerized Medallion (Bronze/Silver/Gold) ELT pipeline that ingests
the VaccineWork healthcare portal's MySQL dump and builds a dimensional Star
Schema for an executive Metabase dashboard.

```
source-db (OLTP replica) --[elt-runner]--> warehouse-db.bronze
                                         --> warehouse-db.silver
                                         --> warehouse-db.gold --> Metabase
```

See [docs/01_architecture_c4.md](docs/01_architecture_c4.md) for the C4
context diagram and [docs/02_data_dictionary.md](docs/02_data_dictionary.md)
for the full Star Schema design and data dictionary.

## Prerequisites

- Docker Desktop (with Compose v2) running on Windows
- The source dump `dump-vaccinework-202610022042.sql` already copied into
  `source-db/init/01-vaccinework-dump.sql` (done — it auto-seeds `source-db`
  on first boot)

## 1. Configure environment

```powershell
Copy-Item .env.example .env
# Edit .env and change all ChangeMe_* passwords before any real use.
```

## 2. Start the databases and Metabase

```powershell
docker compose up -d source-db warehouse-db metabase
```

Wait for both databases to report healthy:

```powershell
docker compose ps
```

`source-db` seeds itself from the mounted dump on first boot.
`warehouse-db` seeds itself from `sql/00_init_schemas_and_grants.sql`,
creating the `bronze` / `silver` / `gold` schemas and two accounts:

| Account | Scope | Used by |
|---|---|---|
| `dwh_elt` | full DML/DDL on bronze, silver, gold | elt-runner (pipeline runs as `root` locally for simplicity — see note below) |
| `metabase_ro` | `SELECT` on `gold.*` only | Metabase connection |

> **Note:** `docker-compose.yml` runs the `elt-runner` as the MySQL `root`
> users of both containers for local-dev simplicity (no extra credential
> wiring). The `dwh_elt` / `metabase_ro` least-privilege accounts are still
> created and are what you should actually enter into Metabase and any
> future non-root pipeline runner.

## 3. Run the ELT pipeline

The pipeline is a one-shot batch job (not a long-running daemon). Run it
whenever the source data changes:

```powershell
docker compose run --rm elt-runner
```

This executes, in order:

1. **Bronze**: creates raw 1:1 replica tables, then extracts every source
   table and batch-loads it (`pipeline/extract_load_bronze.py`).
2. **Silver**: creates cleansed/conformed tables and runs the
   standardization + deduplication transforms (`sql/silver/`).
3. **Gold**: creates the Star Schema (`Dim_*` / `Fact_*`) and populates it
   with `INSERT INTO ... SELECT` loads joining across Silver (`sql/gold/`).

It prints a row-count summary of every Gold table on success. The whole run
is idempotent — rerun it any time without manual cleanup.

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
4. Build questions/dashboards against `Fact_Patient_Registration`,
   `Fact_Screening_Response`, and `Fact_Vaccination` joined to their `Dim_*`
   tables — see example KPI queries in
   [docs/02_data_dictionary.md](docs/02_data_dictionary.md#5-example-executive-kpi-queries-metabase-ready).

## Project layout

```
VaccineWork-DWH/
├── docker-compose.yml
├── .env.example
├── source-db/init/            # auto-seeds the OLTP source replica
├── sql/
│   ├── 00_init_schemas_and_grants.sql   # warehouse bootstrap (runs once)
│   ├── bronze/                # raw 1:1 replica DDL
│   ├── silver/                # cleanse/conform DDL + transforms
│   └── gold/                  # star schema DDL + dimension/fact loads
├── pipeline/                  # Python ELT orchestrator (elt-runner image)
└── docs/
    ├── 01_architecture_c4.md  # C4 context diagram (Mermaid)
    └── 02_data_dictionary.md  # star schema design + data dictionary
```

## Rerunning / resetting

- **Rerun the pipeline** (e.g. after new data lands in `source-db`):
  `docker compose run --rm elt-runner`
- **Full reset** (wipe all containers + volumes and start over):
  ```powershell
  docker compose down -v
  docker compose up -d source-db warehouse-db metabase
  docker compose run --rm elt-runner
  ```

## Scaling beyond this prototype

This design optimizes for local-dev clarity at ~400-patient scale. If the
source system grows, the first things to revisit:

- **Incremental loads**: Bronze currently does a full `TRUNCATE`+reload
  every run. At higher volume, switch to extracting only rows where
  `updated_at > last_watermark` (all source tables already carry
  `created_at`/`updated_at`, so this is a filter change, not a schema
  change).
- **Orchestration**: swap the single `docker compose run` trigger for a
  scheduler (cron, Airflow, Dagster) if the pipeline needs to run on a
  fixed cadence rather than on demand.
- **Least-privilege credentials**: switch `elt-runner` from `root` to the
  `dwh_elt` account (source side) plus a dedicated read-only replication
  user on `source-db`.

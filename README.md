# Regional Health & Population Data Warehouse

A local, Dockerized Medallion (Bronze/Silver) ELT pipeline built from 5
live Thai government APIs — no flat files, no manual exports. Raw API
responses land in a versioned, content-hashed S3-compatible store
(SeaweedFS) before Bronze shreds them into tables; the `elt-runner`
container never writes raw bytes to its own filesystem.

```
API (NSO/BMA/DIW/DDS/HDC)
  --[ingest_api_*.py]--> landing-zone (SeaweedFS, versioned)
  --[extract_load_api_*.py]--> warehouse-db.bronze
  --[transform_silver_api_*.py]--> warehouse-db.silver
  --[transform_gold_*.py]--> warehouse-db.gold --> Metabase
```

See [docs/01_architecture.html](docs/01_architecture.html) for the full
data-flow diagram, [docs/02_data_dictionary.html](docs/02_data_dictionary.html)
for every Bronze/Silver/Gold table and column,
[docs/04_gold_layer_and_kpi_guide.html](docs/04_gold_layer_and_kpi_guide.html)
for the KPI pyramid + dashboard design,
[docs/05_runbook.html](docs/05_runbook.html) for how to deploy this from
zero (first-time setup, Metabase bootstrap, troubleshooting, reset), and
[docs/03_external_reference_sources.md](docs/03_external_reference_sources.md)
for provenance and known issues per source.

## Sources

| Source | Bronze table(s) | Status |
|---|---|---|
| NSO household income | `api_nso_income` | verified (15,400 rows) |
| BMA community registry | `api_bma_community` | verified (6,027 rows) |
| DIW factory registry | `api_diw_factory` | verified (13,683 rows) — PII (`operator_name`/`phone`) deliberately excluded |
| DDS disease ranking | `api_dds_disease_ranking` | code-complete, **blocked**: DDS's own backend has returned a server-side DB-driver error since 2026-10-25 |
| HDC health-status reports | `api_hdc_report_catalog`, `api_hdc_observations` | verified (116 reports, 163,219 EAV rows) |

## Gold layer

Built bottom-up from a KPI tree (`Excel\KPI_Tree_and_Dashboard_Design.xlsx`)
designed from the available Silver data, feeding 4 dashboards built
manually in Metabase: Executive Overview, Economic & Industrial
Development, Population & Community, Public Health Surveillance.

| Type | Tables |
|---|---|
| Dimensions | `dim_date`, `dim_geography`, `dim_industry`, `dim_hdc_report`, `dim_disease` |
| Facts | `fact_income`, `fact_factory`, `fact_community_population`, `fact_disease_ranking`, `fact_hdc_observation` |
| Aggregates | `agg_economic_by_province_year`, `agg_population_by_district_year`, `agg_health_kpi_by_province_year` |
| Composite | `obt_regional_composite_index` (the 3 Level-3 strategic KPIs, 0-100 normalized) |

`dim_geography` is built purely from the 5 sources' own plain-text
geographic labels (not DOPA codes) — see
[docs/04_gold_layer_and_kpi_guide.html](docs/04_gold_layer_and_kpi_guide.html)
for the full KPI-to-table mapping.

## Prerequisites

- Docker Desktop (with Compose v2)

## 1. Configure environment

```powershell
Copy-Item .env.example .env
Copy-Item seaweedfs_s3_config.json.example seaweedfs_s3_config.json
# Edit both and change all ChangeMe_* passwords before any real use --
# the access/secret key pair must match between the two files.
```

## 2. Start the warehouse and landing zone

```powershell
docker compose up -d warehouse-db landing-zone metabase
```

Wait for both to report healthy:

```powershell
docker compose ps
```

`warehouse-db` seeds itself from `sql/00_init_schemas_and_grants.sql`,
creating the `bronze` / `silver` / `gold` schemas and two accounts:

| Account | Scope | Used by |
|---|---|---|
| `dwh_elt` | full DML/DDL on bronze, silver, gold | elt-runner (pipeline runs as `root` locally for simplicity — see note below) |
| `metabase_ro` | `SELECT` on `gold.*` only | Metabase connection |

> **Note:** `docker-compose.yml` runs `elt-runner` as the MySQL `root`
> user for local-dev simplicity. `dwh_elt` is still created and is what
> you should enter into any future non-root pipeline runner.

## 3. Run the ELT pipeline

One-shot batch job, not a daemon. Run it any time:

```powershell
docker compose run --rm elt-runner
```

For each of the 5 sources: ingests from the live API, lands the raw
response in the SeaweedFS landing zone, shreds into Bronze, then cleanses
into Silver. A source that's temporarily down (see DDS above) logs a
warning and the run continues with every other source — see
`run_pipeline.run_live_source()`.

Then builds Gold: dimensions (incl. the text-matched `dim_geography`),
facts (including pivoting HDC's EAV Silver rows into named measure
columns), and the aggregate/composite-index tables that feed the 4
Metabase dashboards.

Prints a row-count summary of every Bronze/Silver/Gold table on success.
The whole run is idempotent: the landing zone skips re-storing identical
bytes, and each layer's DDL drops/recreates its own tables every run.

## Project layout

```
clinical-dwh/
├── docker-compose.yml
├── .env.example
├── seaweedfs_s3_config.json.example   # SeaweedFS S3 gateway identity (copy + edit alongside .env)
├── Excel\KPI_Tree_and_Dashboard_Design.xlsx   # (outside the repo folder) KPI pyramid + dashboard design
├── sql/
│   ├── 00_init_schemas_and_grants.sql       # warehouse bootstrap (runs once)
│   ├── bronze/10_create_bronze_api_sources.sql
│   ├── silver/18_create_silver_api_sources.sql
│   └── gold/01-03_create_gold_*.sql          # dimensions, facts, aggregates/composite-index
├── pipeline/                          # Python ELT orchestrator (elt-runner image)
│   ├── landing_store.py               # versioned S3 landing-zone client
│   ├── ingest_api_*.py                # one per source: fetch -> land raw bytes
│   ├── extract_load_api_*.py          # one per source: land -> Bronze shred
│   ├── transform_silver_api_*.py      # one per source: Bronze -> Silver cleanse
│   └── transform_gold_{dimensions,facts,agg}.py   # Silver -> Gold dims/facts/aggregates
└── docs/
    ├── 01_architecture.html                  # data flow, services, known issues
    ├── 02_data_dictionary.html                # every bronze/silver/gold table + column
    ├── 03_external_reference_sources.md       # provenance, verification history
    ├── 04_gold_layer_and_kpi_guide.html       # KPI pyramid + dashboard-to-table mapping
    ├── 05_runbook.html                        # how to deploy: setup, verify, Metabase bootstrap, troubleshooting, reset
    └── build_html_docs.py                     # regenerates 01/02/04/05 from the live schema
```

## Rerunning / resetting

- **Rerun the pipeline**: `docker compose run --rm elt-runner`
- **Full reset** (wipe all containers + volumes, including landed objects):
  ```powershell
  docker compose down -v
  docker compose up -d warehouse-db landing-zone metabase
  docker compose run --rm elt-runner
  ```

## Connect Metabase

Fresh instance as of 2026-10-26 (the prior one, built for the removed
file-based warehouse, was dropped entirely). Open http://localhost:3000
and log in with the admin account created during setup. The `gold`
database connection is pre-configured via the read-only `metabase_ro`
account — bronze/silver are not reachable from Metabase. All 14 Gold
tables are synced. Dashboards are built manually in the UI; see
[docs/04_gold_layer_and_kpi_guide.html](docs/04_gold_layer_and_kpi_guide.html)
for the suggested KPI-to-visualization mapping per dashboard.

## Next steps

- **DDS**: re-run `docker compose run --rm elt-runner` (or just
  `ingest_api_dds.run()`) once DDS's own backend recovers. `fact_disease_ranking`
  and `dim_disease` are structurally ready, just empty until then.
- **Documentation**: `docs/build_html_docs.py` regenerates
  `01_architecture.html`, `02_data_dictionary.html`,
  `04_gold_layer_and_kpi_guide.html`, and `05_runbook.html`. The first
  three read the live schema (`%TEMP%\schema_dump.tsv` / `row_counts.tsv`,
  dumped from `information_schema` — see the script for the exact dump
  queries); the runbook is static. Re-run after any schema change so the
  docs don't drift.

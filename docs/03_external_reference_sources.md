# External Reference Data — Provenance & Scope

**As of 2026-10-26, this warehouse is built entirely from 5 live Thai
government APIs** (NSO, BMA, DIW, DDS, HDC) — see below. An earlier phase
of this project built a much larger Bronze/Silver/Gold pipeline from a
shared Drive folder of static files (DOPA population, HDC/DDS manual
exports, Lat Krabang, KMCH, factory lists, and more) plus a short-lived
clinic/patient OLTP source. All of that — every non-API Bronze/Silver
table, the entire Gold layer, the raw input files, and the docs describing
them — was removed on explicit instruction to keep the warehouse scoped
to the 5 live-API sources only. This file's history of that earlier phase
was trimmed along with it; only the live-API work remains documented below.

## Live-API Bronze sources, landed via SeaweedFS (2026-10-25/26)

Five new Bronze sources, adapted from `Paiiyahh/kmch-ml`'s (private repo,
user is a collaborator) existing API-backed ingestion, on explicit
instruction to pull from live government APIs instead of static files —
with no raw file ever written to `elt-runner`'s own container disk.

**Architecture**: `API → landing zone (SeaweedFS, versioned, content-hashed) → Bronze shred (Python, no local disk) → bronze.api_*`.
MinIO was the original choice (matching kmch-ml's own local `raw_store.py`
pattern, just backed by S3 instead of a filename) but its free container
distribution was discontinued across every registry checked (Docker Hub,
quay.io, direct binary download) as of this build, confirmed by direct
testing — switched to SeaweedFS (`chrislusf/seaweedfs`), same S3 API via
`boto3`, no code difference beyond `landing_store.py`'s endpoint config.
See `pipeline/landing_store.py` for the versioning contract (identical
bytes are never stored twice; `written-ns` object metadata, not the
backend's own `LastModified`, decides "latest" — SeaweedFS's timestamp is
only second-precision, too coarse for DIW's rapid amphoe-by-amphoe crawl).

| Source | Bronze table | Verified row count | Notes |
|---|---|---|---|
| NSO household income (`SFD_SPB0802_66`, `catalogapi.nso.go.th`) | `api_nso_income` | 15,400 | Sits behind a WAF that blocks the default requests/curl User-Agent (HTTP 418 block page) — needs a browser-like UA, confirmed by direct testing. |
| BMA community registry (CKAN `soc_626755a649135`, `data.bangkok.go.th`) | `api_bma_community` | 6,027 (2,017 FY2565 + 2,007 FY2566 + 2,003 FY2567) | One CSV resource per fiscal year, walked dynamically via `package_show` — a future fiscal year lands with no code change. FY2567's 2,003 matches kmch-ml's own documented figure exactly. |
| DIW factory registry (3 provinces: Bangkok/Samut Prakan/Chachoengsao, `userdb.diw.go.th`) | `api_diw_factory` | 13,683 (exact match to kmch-ml's own documented total) | Amphoe-by-amphoe crawl (67 amphoe total), each a legacy `.xls` (BIFF, cp874-encoded) response via `xlrd==1.2.0` (last version supporting the old binary format). **PII exclusion**: the source sheet also carries `operator_name` (factory owner's personal name) and `phone` — kmch-ml's own documented rule for this exact source is that these "stay local… never add them, never print them in outputs." Both columns are read off the sheet (to keep every other column's position aligned) and dropped in `extract_load_api_diw.py` before any row is built, logged, or inserted — they never reach this table or any output. |
| DDS notifiable-disease ranking (`doe.moph.go.th/dds-report`) | `api_dds_disease_ranking` | **0 — not yet verified live** | Code is a faithful adaptation of kmch-ml's already-proven token/year/week-range-probing flow, but DDS's own backend has been returning a server-side error on every request since 2026-10-25 (`"could not find driver (Connection: pgsql…)"` — a missing/misconfigured PostgreSQL PHP driver on their end, confirmed by repeated direct testing, unrelated to this code). Re-run `ingest_api_dds.run()` once DDS recovers; the landing zone exists specifically because DDS "keeps no archive: a finished year it stops serving cannot be fetched again," so this source is worth retrying rather than giving up on. |
| HDC health-status reports (4 subcatalogs, `api-center-hdc.moph.go.th` / `api-hdc.moph.go.th`) | `api_hdc_report_catalog` (116 rows), `api_hdc_observations` (163,219 rows, 113 distinct report codes) | 116 reports discovered (119 minus 3 confirmed server-side-crashing codes, excluded per kmch-ml's own finding), ~1,100 throttled requests for a full crawl | Shredded as a **generic EAV table** (one row per report × year × zone × record × field) rather than one table per report shape — live HDC reports vary their column layout per report (confirmed: `province_keyed` / `disease_ranking` / `unsupported` layouts). |

**Resilience**: all 5 live-API sources are wrapped in `run_pipeline.run_live_source()`,
which logs a failure and continues rather than aborting the whole
Bronze→Silver run — confirmed necessary in practice (DDS's outage above
would otherwise have blocked every other source on every pipeline run
until DDS's own team fixes their server). Verified end-to-end on
2026-10-25/26: a full `docker compose run --rm elt-runner` completed
successfully with DDS skipped and every other source loaded through Silver.

**Silver (2026-10-26)**: each of the 5 Bronze tables above has a matching
`silver.api_*` table (`sql/silver/18_create_silver_api_sources.sql`,
`pipeline/transform_silver_api_{nso,bma,diw,dds,hdc}.py`) casting Bronze's
raw text columns to real types and normalizing BE→CE fiscal years (NSO/
BMA/HDC source their years in Buddhist era; DDS's own year scheme is
already Christian era, confirmed by its token-probing logic). Row counts
match Bronze exactly (15,400 / 6,027 / 13,683 / 0 / 163,219) — no rows
silently dropped by a failed cast. `api_hdc_observations` keeps
`field_value` as text rather than casting per report (~116 reports mix
counts/rates/percentages under the same generic column) — per-report
typing and dimension resolution are Gold concerns, and no Gold layer has
been built yet for these sources.

## Scope reduction (2026-10-26)

On explicit instruction, everything not related to the 5 live-API sources
was removed: all 9 file-based Bronze sources (DOPA, HDC manual exports,
Lat Krabang, KMCH, factory_list, DDS health region, the old file-based
NSO, HDC region6_13, other_health) and their Silver tables, the entire
Gold layer (all 36 SQL files — 100% of Gold depended on the removed
sources, none of it was API-sourced), the `external-sources/` raw input
folders, the orphaned aggregate-row audit tool (`tools/`, scanned tables
that no longer exist), and the docs that described all of it
(`01_architecture_c4.md`, `02_data_dictionary.md`, `04_ml_team_onboarding.md`,
`05_claude_handover_prompt.md`, `06_gold_layer_documentation.html`,
`Documentation.html`). The corresponding tables were also dropped from the
live `warehouse-db` (97 explicit `DROP TABLE` statements for bronze/silver,
plus the entire `gold` schema dropped and recreated empty). `README.md`
was rewritten to describe the reduced, API-only scope.

# External Reference Data — Provenance & Scope

## Source inventory (2026-10-28) — by origin type

**12 distinct sources, 2 origin types.** Every source lands through the
same SeaweedFS landing zone (versioned, content-hashed) regardless of
type — the only difference is *how* bytes get there: an HTTP call this
pipeline makes itself ("Live API"), or a file supplied directly and
bind-mounted at `external-inputs/` ("File-based"). Both are first-class,
not a tiered hierarchy — file-based sources exist because the data isn't
available any other way (a one-time government publication, a GitHub
repo's community-maintained reference list), not because they're a
fallback.

Two sources moved from file-based to live on 2026-10-28 (DOPA population,
BMA/DOE migrant worker permits) — see
`docs/06_kmch_ml_gap_closure_plan.md`'s "Post-closure: converting Gap 1
and Gap 2 to live sources" section for the full investigation and
implementation notes.

### Live API (10 sources — HTTP call on every pipeline run)

| # | Source | Endpoint | Status | Bronze table(s) | Verified rows |
|---|---|---|---|---|---|
| 1 | NSO household income | `catalogapi.nso.go.th` | ✅ Working (WAF needs a browser-like User-Agent) | `api_nso_income` | 15,400 |
| 2 | BMA community registry | `data.bangkok.go.th` (CKAN) | ✅ Working | `api_bma_community` | 6,027 |
| 3 | DIW factory registry | `userdb.diw.go.th` | ✅ Working | `api_diw_factory` | 13,683 |
| 4 | HDC health-status reports | `api-hdc.moph.go.th` / `api-center-hdc.moph.go.th` | ✅ Working | `api_hdc_report_catalog`, `api_hdc_observations` | 116 + 163,233 |
| 5 | Thailand admin-boundary reference | `raw.githubusercontent.com` (`DevelopedbyWill/thailand-canonical-admin-names`) | ✅ Working | `geo_boundary_subdistrict`, `geo_boundary_district`, `geo_boundary_polygon` | 7,436 + 928 + 7,425 |
| 6 | OSRM road routing | `router.project-osrm.org` | ✅ Working | `geo_travel_matrix` | 312 |
| 7 | DDS disease ranking | `doe.moph.go.th/dds-report` | ❌ Blocked — confirmed server-side (missing PostgreSQL driver on DDS's own backend since 2026-10-25), not this code | `api_dds_disease_ranking` | 0 |
| 8 | OSM hospital facilities (Overpass) | `overpass-api.de` | ❌ Blocked — confirmed network-level (HTTP 406 from both the container and the host directly), not this code | `geo_hospital_facility` | 0 |
| 9 | DOPA population by area/year | `stat.bora.dopa.go.th` (two plain files: nationwide codes + per-province age breakdown) | ✅ Working (browser-like User-Agent, no WAF issue) | `dopa_population_year` | 312 (merged-unit grain) |
| 10 | DOE migrant worker permits | `doe.go.th` (monthly PDF publication) | ✅ Working (browser-like User-Agent, no WAF issue) | `doe_migrant_worker_monthly` | 1,518 (EAV) |

### File-based (2 sources — a supplied file, not an HTTP call this pipeline makes)

| # | Source | Original file | Bronze table(s) | Verified rows |
|---|---|---|---|---|
| 11 | Tambon↔unit crosswalk | `xwalk_tambon_unit.csv` | `tambon_xwalk` | 323 |
| 12 | DOPA population supplement (2560-2564 backfill) | `pop_total_supplement_2560_2564.csv` | `dopa_population_supplement` | 715 |

**Why these 2 are file-based, not live**: neither is available via any
API. The crosswalk is a specific, one-time export from kmch-ml's own prior
work, not a publication with a stable fetchable endpoint. The population
supplement backfills 5 historical years (2560-2564) for Samut Prakan/
Chachoengsao that DOPA's own live download portal only ever publishes the
*current* year for — there's no live equivalent to pull that history from.
Each is a **deliberate, scoped exception** to this project's live-API-first
default — not a reversion to the older, larger file-based architecture an
earlier phase of this project removed entirely (see the historical note
below). Both are bind-mounted read-only at `external-inputs/`
(`docker-compose.yml`), the same pattern `sql/` already uses — updating
either later needs no image rebuild.

**Totals**: 8 of 10 live-API sources are currently reachable; both blocked
ones are confirmed external, not a defect here, and the pipeline's
`run_live_source()` wrapper ensures one source's outage never blocks any
other source's refresh. Both file-based sources are fully loaded.

---

## Historical note: this project's scope was reduced once already

As of 2026-10-26, this warehouse was rebuilt from scratch around 5 live
Thai government APIs (NSO, BMA, DIW, DDS, HDC) — see below. An earlier
phase of this project built a much larger Bronze/Silver/Gold pipeline from
a shared Drive folder of static files (DOPA population, HDC/DDS manual
exports, Lat Krabang, KMCH, factory lists, and more) plus a short-lived
clinic/patient OLTP source. All of that — every non-API Bronze/Silver
table, the entire Gold layer, the raw input files, and the docs describing
them — was removed on explicit instruction to keep the warehouse scoped
to the 5 live-API sources only. This file's history of that earlier phase
was trimmed along with it; only the live-API work remained documented
below at that time. The file-based sources added back on 2026-10-27
(table above) are a separate, deliberate decision for specific,
well-understood gaps — not an undoing of that original reduction.

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
match Bronze exactly — no rows silently dropped by a failed cast.
`api_hdc_observations` keeps `field_value` as text rather than casting per
report (~116 reports mix counts/rates/percentages under the same generic
column) — per-report typing and dimension resolution are Gold concerns.
Gold (dimensions/facts/aggregates/composite index, plus the kmch-ml
input-parity additions: `dim_area`, `dim_facility`, weekly HDC,
hospital-access) is live — see `docs/04_gold_layer_and_kpi_guide.html`
for the full table list.

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

## kmch-ml input-parity extension (2026-10-26, extended 2026-10-27)

Additive ingestion only — no existing Gold table/column renamed, dropped,
or redefined (verified against `information_schema` before and after).
Originally closed 3 of the 4 gaps between this warehouse's input surface
and what kmch-ml's analysis pipeline needs; DOPA population (gap 4 in the
planning doc) was deferred pending project-owner sign-off. That sign-off
arrived 2026-10-27 along with the actual source files, closing the 4th gap
— see `docs/06_kmch_ml_gap_closure_plan.md` for the full gap-by-gap plan
and status (this file and that one now cover overlapping ground; this
section stays as the provenance record, that doc as the working plan).

- **`fact_population_by_area`** (DOPA population by unit/year, closes the
  previously-deferred gap 4): file-based, not a live API — a deliberate,
  scoped exception, same pattern as `bronze.tambon_xwalk`. Built from two
  files: `dim_population_year.csv` (fine 5-yr + coarse age-sex bands, 9
  years 2560-2568 BE, already at `dim_area`'s 312-unit merged grain — no
  split-tambon codes present) and `pop_total_supplement_2560_2564.csv`
  (`pop_total` only, 5 years 2560-2564, Samut Prakan/Chachoengsao only).
  Confirmed before building: the two files share **zero** overlapping
  `(unit_code, year_be)` pairs — the supplement is a clean backfill for a
  real gap in the main file (every Samut Prakan/Chachoengsao unit has
  exactly 4 years, 2565-2568, in the main file; Bangkok units have the
  full 9), not a conflicting or redundant source. 2,808 rows total
  (2,093 `full` + 715 `total_only`), verified against both source files
  row-for-row (e.g. unit 100101/2560 and unit 110101/2560 match exactly).
  Also required extending `dim_date` from 5 years (2022-2026) to 10
  (2017-2026) to cover this data's full range.

  **Superseded 2026-10-28**: `dim_population_year.csv`'s role is now
  played by a live source (`stat.bora.dopa.go.th`) — see
  `docs/06_kmch_ml_gap_closure_plan.md`'s "Post-closure" section. The
  supplement file above is unaffected and remains the permanent file-based
  backfill it always was.

- **`fact_factory.area_key` + `dim_industry_division` +
  `agg_industrial_concentration_by_unit(_division)`** (industrial
  location quotient, kmch-ml input-parity gap 3): `area_key` is additive
  to the existing `fact_factory` table, resolved via `(amphoe,tambon)`
  text match against `dim_tambon_unit_xwalk` (97.4% resolved, 13,331 of
  13,683 factories). Methodology reverse-engineered from kmch-ml's own
  reference export before writing any code: LQ is scoped to
  TSIC-2009-5-digit-coded factories only (DIW's legacy/short-coded
  factories excluded), and "region" is confirmed to mean the whole
  3-catchment-province scope, not per-province. Recomputed from
  `fact_factory` on every refresh, not loaded as a static copy of
  kmch-ml's snapshot — verified to match their reference values to within
  the drift expected from a newer DIW crawl. `industrial_concentration`
  is a documented best-effort approximation of kmch-ml's own flag
  (~91% agreement) — their exact rule could not be fully
  reverse-engineered from the data alone.

- **`dim_bma_zone` / `bridge_bma_zone_district` /
  `fact_migrant_worker_permit`** (migrant worker permits, kmch-ml
  input-parity gap 2): file-based (BMA/Dept. of Employment publication,
  2568 BE single snapshot), not a live API. The source is a wide,
  multi-section pivot (4 stacked tables in one sheet) — shredded as 4
  separate Bronze tables matching the file's own section boundaries, not
  normalized until Silver. Verified before building: every section's
  grand-total row exactly equals the sum of its 10 zone rows, in every
  column, confirming `"-"` means literal zero (it coexists row-by-row
  with real nonzero numbers for other nationalities in the same row) —
  and cross-section: 3 of `bma_migrant_general`'s 6 categories have their
  exact totals reproduced by summing the corresponding nationality-level
  section. BMA's own 10-zone grouping is a different grain than
  `dim_geography`/`dim_area` (a zone covers several districts), so the
  zone↔district mapping is a many-to-many bridge table, parsed from the
  source file's own district-name list — all 50 links matched against
  `dim_geography.district_name` with zero unmatched.

  **Superseded 2026-10-28**: the BMA/Dept. of Employment file's role is
  now played by a live source (DOE's own monthly PDF, `doe.go.th`) — see
  `docs/06_kmch_ml_gap_closure_plan.md`'s "Post-closure" section. The old
  file-based Bronze tables (`bma_migrant_general`/`mou_import`/`renewal`/
  `illegal`) are no longer wired into the pipeline, left on disk pending
  an explicit retirement decision.

- **`dim_area`** (catchment-area dimension): built from
  `DevelopedbyWill/thailand-canonical-admin-names` (GitHub, public, CC BY
  4.0 — fetched independently, not read from kmch-ml's own repo).
  **Correction (2026-10-27):** an earlier build of this table had 317
  units, attributed at the time to "snapshot-date drift" against kmch-ml's
  documented 312 — that explanation was wrong. The real cause was a bug:
  this table's original fallback-grouping logic only merged a tambon into
  its parent when that tambon's *own* centroid was `NULL`, so 5 of the 7
  Bangkok post-2019 khwaeng-split groups had one sibling (with a valid
  centroid) wrongly left standing as its own independent unit instead of
  merged with the other. Fixed by grouping against
  `xwalk_tambon_unit.csv` (kmch-ml's own authoritative tambon-to-unit
  mapping, landed as `bronze.tambon_xwalk` — see
  `docs/06_kmch_ml_gap_closure_plan.md`, Gap 4) instead of the centroid
  heuristic. Now **312 units**, exactly matching kmch-ml's documented
  total, with the 7 merge groups verified identical to kmch-ml's reference
  export (unit_code, name, member tambons, and catchment_tier all match
  row-for-row). Bangkok's 13 post-2019 khwaeng splits merge into their 7
  pre-2019-split parent tambons (not parent *districts*, the earlier wrong
  description) — `is_district_level_fallback` is kept as the column name
  for backward compatibility but now means "this unit represents a merged
  pre-split group," not literally district-grain. Distance/catchment-tier
  verified against the hospital's own subdistrict (ลาดกระบัง) correctly
  landing as the closest, "core"-tier unit; point-in-polygon ground truth
  additionally confirms unit 101104 (ลำปลาทิว) — not 101101/ลาดกระบัง,
  which is merely closest by distance — is the one unit that physically
  contains the hospital's coordinate, matching kmch-ml's own reference
  file exactly.
- **`fact_hdc_weekly_observation`** (4 PM2.5-linked weekly disease
  reports): turned out to need *zero* Bronze/Silver changes — these 4
  report codes were already being discovered by the existing HDC
  subcatalog crawl (confirmed live, under "การป่วยด้วยโรคจากมลพิษทางอากาศ"),
  just never pivoted into Gold. ~65k rows normalized into
  (report, year, zone, disease group, week 1-53 or NULL for annual
  totals, metric variant, value) — not a flat `w_01..w_53` wide pivot
  (each week actually carries 4+ variant suffixes, confirmed live: `_m`/
  `_y`/`_z`/`_zy` plus additional `_f`-suffixed and `s` variants, meaning
  undocumented by HDC — carried as-is, not guessed).
- **`dim_facility` / `fact_hospital_access`** (OSM + OSRM travel matrix):
  Overpass's public instance (`overpass-api.de`, including its `lz4`
  mirror) returned HTTP 406 on every request tested 2026-10-26, confirmed
  from both the `elt-runner` container and the host machine directly —
  a block on this network origin, unrelated to this code, same class of
  issue as DDS's backend outage. `ingest_api_osm.py` is code-complete and
  wrapped in `run_pipeline.run_live_source()`, worth retrying once
  reachable. `ingest_api_osrm.py` (public demo server,
  `router.project-osrm.org`, confirmed working) does not hard-depend on
  OSM succeeding — it always computes the travel matrix from every
  `dim_area` unit to the fixed KMCH coordinate, verified: all 312 units
  resolved (re-run 2026-10-27 against the corrected `dim_area`, see
  above), road distance consistently exceeds straight-line distance as
  expected, closest units by straight-line also show the shortest drive
  times. Raw matrix only — no Huff-share/E2SFCA accessibility scoring,
  which is analytical modeling out of scope for this ingestion work.

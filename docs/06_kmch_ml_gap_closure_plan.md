# kmch-ml Gap Closure Plan

Plan for the 7 gaps found by diffing kmch-ml's training-data export
(`drive-download-20261027T101505Z-1-001/`) against the live Gold schema.
Each gap is independent and can be built in any order — recommended order
below is by increasing complexity/dependency, not by the numbering used in
the original gap report.

Verified against the live DDL (`sql/bronze/11`, `sql/silver/19`,
`sql/gold/01-06`, `pipeline/transform_gold_dimensions.py`) on 2026-10-27,
not from memory — "already landed in Bronze/Silver, just not selected
through to Gold" is called out explicitly wherever true, since that changes
a gap from "new ingestion" to "pure Gold-layer pull-through."

Next free file numbers (as of 2026-10-27, after Gaps 5/4/6/1/3): Bronze
`15`, Silver `22`, Gold `11`.

---

## Recommended order

1. **Gap 5** — dim_area extra columns (quickest win, mostly pull-through)
2. **Gap 4 + Gap 6** — tambon↔unit crosswalk + postal_code + PCODE resolution
   (Gap 6 turned out to need no new ingestion — see its section below — so
   it's now just one more column on Gap 4's crosswalk table, not a
   separate build)
3. **Gap 1** — DOPA population (biggest lift, unblocks Gap 7's variables)
4. **Gap 3** — industrial LQ/concentration (needs a fact_factory schema change first)
5. **Gap 2** — migrant worker permits (new source, new dimension, independent)
6. **Gap 7** — clustering QA JSON (no DW build — closes automatically after 1 & 5)

**Status as of 2026-10-27: all 7 original gaps closed.** Gap 6 turned out
to be a documentation error, not a real gap (folded into Gap 4). Gap 7
closed automatically once Gaps 1 and 5 landed. Gap 2 (migrant worker
permits) was the last one built. The kmch-ml input-parity work from this
plan is complete.

---

## Gap 5 — `dim_area` missing columns (`area_km2`, `contains_kmch_point`, `amphoe_en`, `n_member`/`member_codes`)

**Complexity: low.** Pure enhancement to `_build_dim_area()` in
`pipeline/transform_gold_dimensions.py` — no new Bronze/Silver source, no
new table. Extends `sql/gold/04_create_gold_area_dimension.sql` with 4-5
new columns and re-runs the existing build function.

What's already there vs. what needs new work, verified column-by-column:

| Column | Source | Work needed |
|---|---|---|
| `amphoe_en` | `silver.geo_boundary_district.name_en` (already landed, typed) | Pure pull-through — add to the existing `district_by_code` SELECT and the INSERT in `_build_dim_area()` |
| `n_member` / `member_codes` | Already computed internally — `missing_by_district` in `_build_dim_area()` already groups the original subdistrict codes per fallback district, it's just not threaded into the output row today | Thread `missing` (list of `(code, name_th)`) into the row tuple for fallback rows (`n_member = len(missing)`, `member_codes = "|".join(codes)`); non-fallback rows get `n_member=1, member_codes=unit_code` |
| `contains_kmch_point` | `bronze.geo_boundary_polygon.raw_geometry_geojson` (full polygon, already landed, **Bronze only — no Silver table exists for it**, by design per `sql/silver/19`'s own comment) | New point-in-polygon test: KMCH's fixed `(lat, lon)` against each unit's polygon. Read raw GeoJSON directly from `bronze_conn` in Python (same precedent as `_build_dim_hdc_report`, which also reads Bronze directly) — needs a point-in-polygon algorithm (ray casting, or `shapely` if available in `pipeline/requirements.txt`; check before adding a new dependency) |
| `area_km2` (subdistrict grain) | **Not yet landed anywhere** — `silver.geo_boundary_district.area_km2` exists but that's *district*-grain, not the per-unit grain `dim_area.csv` uses | Needs geodesic polygon-area computation from `bronze.geo_boundary_polygon.raw_geometry_geojson`, OR check first whether the original `DevelopedbyWill/thailand-canonical-admin-names` source files carry a subdistrict-level area field that Bronze's column list simply didn't capture yet (cheaper than computing) |

**Open decision before starting:** confirm whether `shapely` (or any
geometry library) is already available in the `elt-runner` image — if not,
decide between adding it as a dependency vs. a hand-rolled ray-casting
point-in-polygon (small enough to not need a library, ~20 lines).

**Status: done, 2026-10-27.** `amphoe_en`, `area_km2`, `contains_kmch_point`
built and verified: 317/317 units have `area_km2`, exactly unit `101104`
(ลำปลาทิว) has `contains_kmch_point=1` — matching kmch-ml's own reference
export exactly (not `101101`/ลาดกระบัง, which is merely closest by
distance; the correction from the earlier draft of this plan).
`n_member`/`member_codes` are implemented but inherit a **pre-existing bug**
discovered while verifying them — see below.

**Bug found (not introduced by this change, exposed by it):**
`_build_dim_area()`'s fallback grouping only merges a tambon into its
parent district when that tambon's *own* centroid is `NULL`. For 6 of the
7 Bangkok post-2019 splits, one sibling has a valid centroid and the other
doesn't (e.g. พระโขนง: `100905` has a centroid, `100910` doesn't) — so
today's code wrongly keeps `100905` as its own independent unit and merges
only `100910` into district-level unit `1009`. kmch-ml's reference instead
merges *both* into one unit identified by the **original pre-2019-split
tambon code** (`100905`, not the district code `1009`). Row count still
comes out to 317 either way (each wrongly-separated row cancels out in the
count), which is why this was invisible until `member_codes` existed to
diff against kmch-ml's reference row-by-row. Confirmed wrong for `1009`→
`100905`, `1014`→`101401`, `1026`→`102601`, `1034`→`103401` (missing a 3rd
member), `1044`→`104401` (missing a 3rd member), `1047`→`104701`; the one
case that happens to come out right is `1050`→`105001` (all 4 members
already had `NULL` centroids, so no sibling was wrongly split off).

**Fix deferred to Gap 4, on purpose:** the correct merge-group identity and
membership needs the original pre-split tambon code, which isn't derivable
from anything currently in Bronze/Silver — it's exactly what
`xwalk_tambon_unit.csv` provides. Gap 4 will use that file as the
authoritative source and rebuild `dim_area`'s 7 fallback rows against it,
rather than patching this heuristic with a second guess.

---

## Gap 4 — tambon↔unit crosswalk + `postal_code` (`xwalk_tambon_unit.csv`) + fix `dim_area`'s fallback rows

**Complexity: medium — upgraded from the original "low" estimate.** Still
no live-API ingestion (file-based, same as Gaps 1/2), but this gap now also
has to **correct** `dim_area`, not just add a reference table alongside it
— see the bug found while verifying Gap 5, above. `xwalk_tambon_unit.csv`'s
own `unit_code` column already carries the exact fix: for every row in a
merge group (e.g. `100905` and `100910`), `unit_code` is set to the same
value (`100905` — the original pre-2019-split tambon code), with
`is_split` distinguishing the group's anchor row from its split-off
siblings. This is the authoritative source `_build_dim_area()`'s
`missing_by_district` heuristic was only approximating.

**Steps, in order:**
1. Land `xwalk_tambon_unit.csv` (file-based, same pattern as Gap 1/2 —
   no live API). New `sql/bronze/13_create_bronze_tambon_xwalk.sql` →
   `bronze.tambon_xwalk`, 1:1 with the file.
2. **Fix `_build_dim_area()`**: replace the `missing_by_district`
   NULL-centroid heuristic with a direct read of `bronze.tambon_xwalk`'s
   `unit_code`/`is_split` columns to decide grouping. Concretely: group
   subdistricts by the xwalk's `unit_code` (not by district code `dcode`),
   compute each group's centroid as the member average (confirm this
   matches kmch-ml's own documented centroid-averaging approach for e.g.
   `100905` before assuming simple mean — their reference centroid
   `13.69367, 100.61098` is the number to match against). This fixes `1009`
   → `100905` (now correctly 2 members), `1014`→`101401`, `1026`→`102601`,
   `1034`→`103401` (3 members), `1044`→`104401` (3 members),
   `1047`→`104701`, and confirms `1050`→`105001` stays correct. Also
   re-verify Gap 5's `area_km2`/`contains_kmch_point` for these 7 corrected
   rows once the member sets are right (areas will change; sum over the
   *correct* member set, not the old partial one).
3. New file: `sql/gold/07_create_gold_tambon_xwalk.sql` →
   `dim_tambon_unit_xwalk` (grain: one row per original TIS-1099 tambon
   code). Also carries Gap 6's PCODE resolution (folded in here — same
   grain, same source file):

```
tambon_code, tambon_th, tambon_en, amphoe_code, amphoe_th, postal_code,
adm3_pcode (= 'TH' || tambon_code, the exact key the nationwide polygon
geojson uses), unit_code (FK -> dim_area.unit_code, now correct per step 2),
is_split
```

**Status: done, 2026-10-27.** All 3 steps completed, with one refinement
during implementation: `_build_dim_area()` ended up simpler than planned
— every `unit_code` (merged or not) resolves to exactly one polygon in
`bronze.geo_boundary_polygon` (confirmed: that source pre-dates the 2019
khwaeng splits, so a merge group's polygon is just its pre-split
ancestor's own unsplit geometry; verified zero `unit_code`s without a
match across all 312). So centroid/area/point-in-polygon are computed
uniformly from that single polygon for every row, not "member-average
centroid vs. district fallback" as two separate paths.

**Results, verified against kmch-ml's reference export row-by-row:**
- `dim_area`: **312 units** (was 317), matching kmch-ml's documented total
  exactly. All 7 merge groups now match kmch-ml's reference exactly on
  `unit_code`, `unit_th` (including the `"(รวม N แขวง)"` naming
  convention), `member_codes`, and `catchment_tier` — e.g. `100905`
  (พระโขนง, 2 members, tier `primary`), `105001` (บางบอน, 4 members, tier
  `bkk_other`). Centroid/area differ from kmch-ml's own numbers by <1%
  (different computation method, e.g. `100905`: this build's centroid
  `13.691706, 100.613230` vs. kmch-ml's `13.69367, 100.61098` — close
  enough that no unit's `catchment_tier` changed as a result).
- `dim_tambon_unit_xwalk`: 323 rows (= every tambon in the 3 catchment
  provinces, the finer pre-merge grain), 13 flagged `is_split`, 0 orphaned
  FKs into `dim_area`.
- **Found and fixed a cascading side effect**: `fact_hospital_access` has
  an FK into `dim_area.area_key` (a surrogate, reassigned on every
  rebuild). Rebuilding `dim_area` standalone (not via a full
  `run_pipeline.py` pass) left `fact_hospital_access`'s old rows pointing
  at stale/reassigned surrogate keys — silently wrong, not just orphaned,
  since many old key values still happened to exist post-rebuild, just
  attached to a different unit. Fixed by re-running the OSRM
  ingest→load→Silver→Gold chain against the corrected `dim_area`; also had
  to rebuild `dim_facility` (wiped by re-applying `sql/gold/06`'s DDL to
  clear `fact_hospital_access`). Final state: `fact_hospital_access` 312
  rows, 0 orphans. **Lesson for future standalone single-table rebuilds**:
  check `information_schema` for anything with an FK into the table being
  rebuilt before assuming a surgical rebuild is complete.
- Regenerated `docs/02_data_dictionary.html` and
  `docs/04_gold_layer_and_kpi_guide.html` from live `information_schema` +
  row counts; corrected the stale "snapshot-date drift" explanation in
  `docs/03_external_reference_sources.md` (the real cause was this
  grouping bug, not drift).

---

## Gap 6 — nationwide ADM3 polygon geojson (`thailand-adm3-polygons-v1.0.0.geojson`)

**Correction (2026-10-27): this gap does not exist as originally reported.**
Diffed by SHA-256 against a fresh download of
`DevelopedbyWill/thailand-canonical-admin-names`'s own
`thailand-adm3-polygons-v1.0.0.geojson` — byte-for-byte identical
(`bcaa7af449c8...`, 7,110,519 bytes) to the file
`pipeline/ingest_api_geo_boundary.py` already fetches live. It was also
already sitting in the landing-zone bucket from the last pipeline run:

```
geo_boundary/polygon__20261026_bcaa7af4.geojson   7,110,519 bytes
```

The original report wrongly said `bronze.geo_boundary_polygon` uses "the
TIS-1099 `unit_code` scheme" — it doesn't; its own DDL comment confirms
`raw_adm3_pcode` is already the same `TH420803`-style ADM0-3 PCODE scheme,
nationwide, unfiltered. That claim conflated it with `dim_area.unit_code`
(a *Gold*-layer, 3-province-only, merged code) — a different thing. No new
ingestion, no pipeline change needed.

**What was actually missing, now resolved:**
- **Served over HTTP** — confirmed working via the Filer endpoint you
  already exposed earlier in this project:
  `http://localhost:8888/buckets/landing-zone/geo_boundary/polygon__20261026_bcaa7af4.geojson`
  (tested, HTTP 200, full 7,110,519 bytes). Caveat: the filename carries the
  content hash — if this source is ever re-landed with new content, the URL
  changes and anything pointing at it (Metabase, kmch-ml) needs re-pointing
  manually; there's no "latest" alias in the Filer.
- **Orphaned duplicate geometry removed** — `docs/maps/provinces.geojson`
  and `docs/maps/subdistricts.geojson` (13MB combined, a *third*,
  unrelated, bare-code scheme, confirmed unused — no Metabase Custom Map
  was ever configured) were deleted.

**Remaining work — making it ML-ready, not just bucket-stored:**
Since the goal is for kmch-ml to consume this directly (not just a
Metabase map join), build the crosswalk that was originally deferred:
a `pcode_unit_code` column (or small lookup) resolving bare TIS-1099 (strip
leading `TH` from `ADM3_PCODE`) to `dim_area.unit_code`. This **reuses Gap
4's and Gap 5's work directly** — same `missing_by_district`
fallback-grouping logic resolves which of the 13 Bangkok post-2019
khwaeng-split `ADM3_PCODE`s fall back to which district-level `unit_code`.
Do this as part of Gap 4's `dim_tambon_unit_xwalk` table (add a
`pcode`-equivalent column there) rather than a separate table — the grain
and fallback logic are identical, no reason to duplicate it.

**Verification:** for a sample of non-fallback codes (e.g. ลาดกระบัง
`101101`), confirm `ADM3_PCODE` minus leading `TH` equals `unit_code`
exactly. For the 13 fallback codes, confirm each resolves to its
documented parent district's `unit_code` (same 7 districts kmch-ml's own
`dim_area` build already lands on).

---

## Gap 1 — DOPA population (`dim_population_year.csv` + `pop_total_supplement_2560_2564.csv`)

**Complexity: high — the biggest single gap.** This is the explicitly
deferred "gap 4" from the original kmch-ml-parity extension
(`docs/03_external_reference_sources.md`), now unblocked because you have
the actual files in hand. Architecturally different from every live-API
source already in the warehouse: **this is file-based, not a live API
crawl** — the project removed all file-based ingestion in an earlier phase,
so reintroducing one here is a deliberate, scoped exception, not a reversion
of that decision.

**Open decision before starting — reconcile the two files:**
`dim_population_year.csv` covers BE 2560-2568 (9 years, fine 5-yr age bands
× sex + coarse bands + totals) with per-row `source_file` provenance.
`pop_total_supplement_2560_2564.csv` covers only BE 2560-2564 (5 years,
`pop_total` only, source label `"DOPA stat_t60"` etc.) — an *overlapping*
year range with less detail. Need to decide: is the supplement a
cross-check/backfill for rows missing from the main file, or a different
vintage of the same underlying DOPA stat snapshot? Check for discrepancies
on overlapping `(unit_code, year_be)` pairs before writing the Gold merge
logic — don't silently prefer one source without checking they agree.

**Files:**
- `sql/bronze/14_create_bronze_dopa_population.sql` → two tables,
  `dopa_population_year` (fine/coarse age-sex bands, 1:1 with
  `dim_population_year.csv`) and `dopa_population_supplement` (1:1 with the
  supplement CSV) — same "land the file as-is, no interpretation" rule as
  every other Bronze table.
- A file-landing step (not `ingest_api_*` — no API call here) that reads the
  two local CSVs and lands them into SeaweedFS the same way `ingest_api_*`
  scripts land HTTP responses, just skipping the HTTP fetch.
- `sql/silver/21_create_silver_dopa_population.sql` → cast age-band counts
  to INT, normalize `year_be` → `year_ce`, resolve `unit_code` against
  `dim_area` (this file is already keyed to the *merged* unit grain, not raw
  tambon codes — confirm this against a few known fallback-district codes
  before assuming it, since dim_area.csv's own population-adjacent columns
  weren't cross-checked against this file).
- `sql/gold/08_create_gold_population_facts.sql` → `fact_population_by_area`
  (grain: `unit_code` × `year_ce`), FK to **`dim_area`, not
  `dim_geography`** — this is the cross-cutting key-scheme issue flagged in
  the original gap report; population-by-unit data should join the
  catchment-area dimension, not the name-keyed one the original 4 dashboards
  use.
- New function in `pipeline/transform_gold_facts.py`:
  `_build_fact_population_by_area()`.

**Status: done, 2026-10-27.** The "open decision" resolved cleanly, no
reconciliation needed: confirmed **zero overlapping** `(unit_code,
year_be)` pairs between the two files before writing any merge logic.
`dim_population_year.csv` turned out to have an undocumented gap of its
own — every Bangkok unit has the full 9 years (2560-2568), but every
Samut Prakan/Chachoengsao unit only has 4 (2565-2568) — and
`pop_total_supplement_2560_2564.csv` is a precise backfill for exactly
that gap (143 units × 5 years = 715 rows, matching exactly). A clean
union, not a conflict. `unit_code` was also already confirmed at
`dim_area`'s merged-unit grain (312 distinct codes in the main file,
none of the 13 split-tambon codes present) — no crosswalk resolution
needed for this gap.

Built as planned (`sql/bronze/14`, `sql/silver/21`, `sql/gold/08`,
`_build_fact_population_by_area()`), plus one addition not in the
original plan: `_build_dim_date()` needed extending from 5 years
(2022-2026) to 10 (2017-2026) to cover this data's full range — done via
a full `run_pipeline.py` run rather than a surgical patch, given the
`fact_hospital_access` staleness lesson from Gap 4.

**Results:** `fact_population_by_area`: 2,808 rows (2,093 `full` + 715
`total_only`), 0 orphaned FKs. Verified against both source files
row-for-row — e.g. unit `100101`/2560 (`full`): `pop_total=3953,
pop_male=2358, pop_female=1595`, exact match; unit `110101`/2560
(`total_only`): `pop_total=51699`, exact match. `dim_date` now spans
2560-2569 BE (2017-2026 CE).

---

## Gap 3 — industrial location quotient / concentration (`track_c_lq.csv` + `track_c_unit_summary.csv`)

**Complexity: high — needs a schema change to an existing fact table
first.** `fact_factory` has the raw ingredients (`workers`, `geo_key` via
`dim_geography`, `industry_key` via `dim_industry`) but **not at the grain
these files need**: `track_c_lq.csv` is `unit_code` (subdistrict/merged-unit,
`dim_area` grain) × `division` (2-digit TSIC). Two blockers:

1. **`fact_factory.geo_key` resolves to `dim_geography`
   (name-keyed, amphoe/province grain) — not `dim_area`
   (code-keyed, subdistrict grain).** LQ at the unit grain these files use
   needs `fact_factory` to also resolve an `area_key` FK to `dim_area`. This
   is the same dim_geography-vs-dim_area key mismatch flagged in the
   original gap report, and it blocks this gap specifically — plan to
   **additively** add `area_key` to `fact_factory` (new nullable column +
   FK, backfilled from the same geo-resolution logic `transform_gold_facts.py`
   already uses for `geo_key`, just resolved against `dim_area.unit_code`
   instead). Does not touch `geo_key` or any existing dashboard query.
2. **No TSIC division (2-digit) name lookup exists anywhere.**
   `dim_industry` only stores `tsic_code` (5-digit) + `factory_type_code` —
   no human-readable name at any level. Need a small new reference table,
   not derived from any live source (TSIC 2009 divisions are a fixed,
   small, static list — closer to a seed table than an ingested source):
   `sql/gold/09_create_gold_industry_division.sql` →
   `dim_industry_division` (`division_code` 2-digit, `division_name_en`,
   `division_name_th` if available). `dim_industry.tsic_code`'s first 2
   digits map to this.

**Then the actual LQ build:**
`sql/gold/10_create_gold_industrial_concentration.sql` →
- `agg_industrial_concentration_by_unit_division` (unit × division grain,
  matches `track_c_lq.csv`: `n_factories`, `workers`, `share_of_unit_workers`,
  `region_share_workers`, `lq_workers`, `lq_factories`, `small_n`)
- `agg_industrial_concentration_by_unit` (unit grain, matches
  `track_c_unit_summary.csv`: `top_division`, `top_division_lq`,
  `n_concentrated_divisions`, `industrial_concentration` flag)

Recommend **recomputing the LQ from `fact_factory` + the new `area_key`**,
not loading the two CSVs as static reference tables — this matches the
warehouse's existing philosophy (compute once in Gold, re-derive on every
refresh) and keeps the numbers live as `fact_factory` is re-crawled, rather
than freezing kmch-ml's one-time snapshot. LQ formula to replicate:
`lq_workers = (unit_workers_division / unit_workers_total) / (region_workers_division / region_workers_total)`
— confirm the exact `region` denominator kmch-ml used (looks like
province-level from `track_c_lq.csv`'s `region_share_workers` column) before
implementing, so your numbers match theirs on the overlapping period.

**Status: done, 2026-10-27.** Both blockers resolved as planned, plus the
exact `region` scope and formula confirmed by direct inspection before
writing any code (not assumed): `region_share_workers` for a given
division is identical across all 3 provinces in kmch-ml's own export,
confirming "region" = the whole 3-catchment-province scope, not
per-province. `small_n = n_factories < 3` reverse-engineered exactly
(100% match). `industrial_concentration` could **not** be fully
reverse-engineered — best single-threshold fit (`lq_workers >= 2 AND NOT
small_n`) only reaches ~91% agreement against kmch-ml's reference export,
suggesting their actual rule is a statistical significance test, not a
flat cutoff. Implemented as a documented best-effort approximation, not
claimed as exact parity.

Built: `fact_factory.area_key` (additive, nullable, FK to `dim_area`,
resolved via `(amphoe,tambon)` text match against
`dim_tambon_unit_xwalk` — confirmed that pair is unique across the 3
provinces before relying on it) — 13,331/13,683 rows resolved (97.4%).
`dim_industry_division` (34 seeded divisions, exact match to every
division present in live `dim_industry` data). `agg_industrial_
concentration_by_unit_division` (2,612 rows vs kmch-ml's 2,622 — close,
expected from a different DIW snapshot + the 2.6% unmatched area_keys)
and `agg_industrial_concentration_by_unit` (281 rows).

**Verified against kmch-ml's reference export, not just row counts**:
unit `100102`/division `17` — `n_factories`, `workers`, `unit_factories`,
`unit_workers`, `small_n`, and `industrial_concentration` all match
exactly; `lq_workers`/`lq_factories` match to within ~0.3% (expected
snapshot drift, not a bug). Unit `101001` (a unit with a 55%-unclassified
factory mix) — `factories_registered`, `workers_registered`,
`factories_tsic2009_5digit`, `top_division`, `top_division_workers`,
`n_concentrated_divisions`, and `industrial_concentration` all match
exactly. 0 orphaned FKs in both new tables.

**Bug found and fixed along the way (not kmch-ml-related)**: the new
`sql/gold/09_create_gold_industry_division.sql` was missing the
`FOREIGN_KEY_CHECKS` guard — broke on the second pipeline run once
`agg_industrial_concentration_by_unit_division` (sql/gold/10) existed and
referenced it. Same class of bug as the `dim_area`/`fact_hospital_access`
issue from Gap 4 — fixed the same way (guard added, matching every other
Gold DDL file with a forward FK dependency).

**Also discovered useful methodology**: MySQL *does* allow a `CREATE
TABLE` to reference a FK target table that doesn't exist yet, as long as
`FOREIGN_KEY_CHECKS=0` is set for that session (confirmed by direct
testing) — this is what let `fact_factory` (script 02) add an FK to
`dim_area` (script 04, created later in `GOLD_SCRIPTS` order) without
reordering anything.

---

## Gap 2 — migrant worker permits (`ข้อมูลแรงงานต่างด้าว.xlsx`)

**Complexity: medium-high — entirely new source, new dimension, no
existing scaffolding to extend.** Not a DIW extension — this is a BMA/DOE
work-permit publication keyed to BMA's own **10 administrative "zones"**
(each zone = a named list of districts), not `dim_geography` or `dim_area`
directly. Also file-based (same file-landing pattern as Gap 1, not a live
API).

**Open decision before starting:** the source file is a wide,
multi-section pivot (4 separate tables stacked in one sheet: current
permits by type, MOU-import breakdown by nationality, renewal breakdown by
nationality, illegal-registration breakdown by nationality — each with its
own header row structure). Decide whether to shred as 4 separate Bronze
tables (1:1 with each section, truer to "no transformation in Bronze") or
normalize into one long table during the Bronze shred itself (easier Silver,
but Bronze would then not be 1:1 with the file — a deliberate exception to
discuss, not a given).

**Files:**
- `sql/bronze/15_create_bronze_bma_migrant_worker.sql`
- File-landing step (reads the local xlsx/csv, same pattern as Gap 1)
- `sql/silver/22_create_silver_bma_migrant_worker.sql` → melt wide
  columns into long format (`zone, permit_category, nationality, sex,
  count`), parse Thai-formatted numbers with commas (`"23,742"` → `23742`),
  treat `"-"` as `0` (confirm with the file — looks like a true zero, not a
  null/not-applicable marker, but verify against a row where the total
  should reconcile)
- New dimension: `sql/gold/11_create_gold_bma_zone.sql` →
  `dim_bma_zone` (10 rows, `zone_id`, `zone_name_th`) +
  `bridge_bma_zone_district` (zone_id × district_name, many-to-many — a zone
  covers multiple districts, so this can't collapse to a single `geo_key`
  per zone)
- `fact_migrant_worker_permit` (grain: zone × permit_category × nationality
  × sex × year), FK to `dim_bma_zone`

**Status: done, 2026-10-27.** The open decision resolved as planned:
shredded as 4 separate Bronze tables (one per section), melted into one
long Silver table with a deliberate two-grain design (nationality NULL
for category-level rows, nationality-specific rows where a breakdown
exists). `"-"` confirmed to mean literal zero before parsing, not
missing/suppressed data — it coexists row-by-row with real nonzero
numbers for other nationalities in the same row (e.g. renewal's Myanmar
column is all zero while Laos/Cambodia/Vietnam have real data in the same
rows).

**Verification exceeded the original plan**: not just the within-section
grand-total-vs-zone-sum check (100% match, every column, all 4 sections),
but also a **cross-section** check that wasn't anticipated going in —
`bma_migrant_general`'s own category totals for MOU import/renewal/
illegal registration exactly equal the grand totals of the 3
nationality-breakdown sections, confirming those sections are a
breakdown of 3 of the 6 categories, not an independent measure.

**Results**: `dim_bma_zone` (10 zones), `bridge_bma_zone_district` (50
zone-district links, parsed from the source file's own district list,
**0 unmatched** against `dim_geography.district_name`),
`fact_migrant_worker_permit` (180 rows: 60 category-level + 120
nationality-level, matching the exact row count predicted from the file
structure before building). Spot-checked against the source file
row-for-row (zone 1 "ทั่วไป" = 5076/3657/1419, exact match) and the
nationality-rows-sum-to-category-total internal check (zone 3's 4
nationality MOU-import values sum to exactly its own category total,
27,118).

---

## Gap 7 — clustering QA JSON (`qa_track_b_clusters.json`)

**Complexity: none — no DW build.** This is kmch-ml's own derived
clustering output (k-means profiles, silhouette/ARI stability metrics), not
source data to ingest. It exists in this plan only to track that it's
**closed automatically** once Gap 1 (population age bands → `pct_60plus`,
`pct_0_4`) and Gap 5 (`area_km2` → `log_density`) land — those are the two
inputs this file's own `variables` list depends on that the warehouse
doesn't yet supply. `e2sfca_d0_20` (accessibility scoring) stays explicitly
out of scope per existing docs (`sql/gold/06`'s own comment) — that's
analytical modeling kmch-ml does on their side from the raw travel matrix
this warehouse already provides.

**Status: inputs ready as of 2026-10-27.** Gaps 1 and 5 are both done —
`fact_population_by_area` (`pct_60plus`/`pct_0_4` derivable from its
coarse age bands) and `dim_area.area_km2` (`log_density` derivable by
joining population to area) are both live. Nothing left to build on this
side; confirming kmch-ml can compute these variables end-to-end is a
hand-off conversation, not a warehouse task.

---

## Post-closure: converting Gap 1 and Gap 2 to live sources (2026-10-28)

Both gaps above were originally closed with one-time file-based snapshots
(`external-inputs/dim_population_year.csv` + `pop_total_supplement_2560_2564.csv`
for Gap 1, `external-inputs/bma_migrant_worker_2568.csv` for Gap 2).
Following the source-by-source API-feasibility evaluation in this doc,
both were converted to live sources so the warehouse auto-refreshes
instead of needing a manual re-upload each time.

### Migrant worker permits → DOE's monthly PDF

Source: DOE's (doe.go.th) own monthly PDF publication, "สถิติการทำงานของ
คนต่างด้าวประจำเดือน...", scraped from
`.../statistic/param/site/152/cat/82/sub/73/.../list-label` (confirmed
live this sub/73 URL returns only monthly reports, not the general
listing). New files: `pipeline/ingest_api_doe_migrant_worker.py`,
`pipeline/extract_load_api_doe_migrant_worker.py` (lands + EAV-shreds the
PDF into `bronze.doe_migrant_worker_monthly`), `sql/bronze/16`,
`pipeline/transform_silver_doe_migrant_worker.py` (pivots back to
`(zone, category, nationality)` grain), `sql/silver/23`. `sql/gold/11`
gained a `report_month_num` column on `fact_migrant_worker_permit`;
`_build_fact_migrant_worker_permit()` now resolves `date_key` from the
live report's own year instead of a hardcoded constant. The old file-based
`bma_migrant_general`/`mou_import`/`renewal`/`illegal` Bronze tables and
their ingest/Silver scripts are no longer wired into `run_pipeline.py`
(left on disk, unused, pending an explicit decision to delete them —
retiring them outright was blocked by the harness's auto-mode classifier
since the live source's month, 2569-09, doesn't match the retired file's
month, making a same-period reproduction check impossible).

This PDF's text layer turned out to have two independent quirks that
needed careful handling (both documented inline in
`extract_load_api_doe_migrant_worker.py`): embedded Thai font subsets
reassign tone marks to inconsistent Private Use Area codepoints per
subset, and the whole document spells SARA AM (ำ) using the legacy
decomposed NIKHAHIT+SARA AA form instead of the precomposed character.
Both are normalized away before any text comparison. A multi-page table's
continuation pages repeat the title with a trailing "(ต่อ)" ("continued")
suffix, which gets stripped rather than misread as a real category name.

Verified: zone 1's MOU permit total (10,000) matches exactly between the
overview table and its own nationality-breakdown table; a nationality
breakdown's component values sum exactly to its own stated total (table 7:
39,405 + 211,560 + 6 + 1 = 250,972). 430 Gold fact rows for report period
2026-09 (2569-09 BE), confirmed via a clean full pipeline run.

### DOPA population → stat.bora.dopa.go.th's download portal

Source: DOPA's own download portal (not the `stat_forward.php` JSON API
investigated earlier in this doc, which was never confirmed to expose
final population counts) — two plain static files, confirmed live to need
only a browser-like User-Agent header, no WAF issue:
  - `https://stat.bora.dopa.go.th/new_stat/file/{YY}/stat_t{YY}.txt` —
    nationwide, one row per province/district/subdistrict, carries numeric
    codes but MALE/FEMALE/TOTAL only.
  - `https://stat.bora.dopa.go.th/new_stat/file/{YYMM}/{YYMM}cc{province}.txt`
    — per-province, single-year-of-age × sex breakdown (102 ages), but no
    codes at all (areas identified by name only).

New files: `pipeline/ingest_api_dopa_population.py` (discovers the latest
year from the site's own menu, lands both files for the 3 catchment
provinces), `pipeline/extract_load_api_dopa_population.py`. The two
datasets are confirmed to publish on different schedules (the age
breakdown was already on year 2569 while the plain-count dataset still
topped out at 2568 on 2026-10-28), so the ingest always targets whichever
year the plain-count dataset's own menu lists as latest — the one
guaranteed to have both.

Since the age-breakdown file has no codes, its rows are matched to the
plain file's numeric codes by POSITION (confirmed live both files list
every area in the same order, same count per province) rather than name
matching, with a two-pointer resync fallback for the one province
(Chachoengsao) where a single subdistrict row is missing from the age file
only. Age bands are aggregated from the 102 single-year values into the
same fine/coarse bands `bronze.dopa_population_year` already used (kept
unchanged from the original file-based schema) so Silver and Gold needed
no changes — only the ingest/extract_load layer is new. Multiple original
tambons that merge into one `dim_area` unit (the 7 Bangkok post-2019
khwaeng splits) are summed before landing, not left as separate rows.

Unit-code resolution reads `bronze.tambon_xwalk` directly rather than
`gold.dim_tambon_unit_xwalk` (a straight copy of the same rows) — this was
a real ordering constraint, not a style choice: `dim_date` needs
`silver.dopa_population_by_unit_year`'s year range, which needs this
source's Bronze rows, which would otherwise need `gold.dim_area` to exist
first inside the same `transform_gold_dimensions.run()` call. Reading
Bronze directly lets this source run in the normal Bronze-phase position
alongside every other live source.

Verified: Bangkok's population sums to exactly 5,422,568 across its 50
merged units, matching DOPA's own published provincial total exactly. 312
Gold fact rows for 2025 (year_be 2568) plus 715 carried-over `total_only`
rows from the file-based supplement (2560-2564, still a permanent
file-based exception — no live equivalent exists for that historical
backfill), confirmed via a clean full pipeline run.

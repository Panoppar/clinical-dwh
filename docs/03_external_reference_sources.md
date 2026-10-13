# External Reference Data — Provenance & Scope

Source: a Google Drive folder (`share_unprocessed_20261010`) containing 10
groups of external population/epidemiological data collected for the
broader KMCH catchment-analytics effort. **As of 2026-10-19, this is the
only data in the warehouse** — an earlier phase of this project also fed a
clinic/patient OLTP source (`clinic_portal`, formerly a vaccination
portal) into the same Bronze/Silver/Gold pipeline, but that entire
pipeline (source database, container, and every Bronze/Silver/Gold table
built from it) was deleted on explicit instruction to keep the warehouse
scoped to this Drive folder's data only. See "Clinic/patient data removal"
below for what that took.

## Phase 1 — ingested (this round)

| Group | Files used | License / source | Bronze table | Silver table |
|---|---|---|---|---|
| 4_DOPA_population_by_month_and_area | `stat_t.txt` (294,474 data rows — nationwide province→district→subdistrict→village hierarchy) | Thailand DGA Open Government License, via data.go.th / DOPA | `bronze.dopa_population_monthly` | `silver.population_reference_subdistrict` |
| 5_NSO | `reg_age_2567.csv`, `reg_prov_2567.csv` (population by age × sex, national + Bangkok/Samut Prakan/Chachoengsao — the catchment provinces) | Official NSO StatHub (`TNSO:DF_01POP_REG`), pulled 2026-10-04 | `bronze.nso_population_registration` | `silver.population_reference_age_sex` |
| *(not from the Drive folder)* | `provinces.csv`, `districts.csv`, `sub_districts.csv` — zip code ↔ subdistrict/district/province, 77 provinces / 930 districts / 7,436 subdistricts | [kongvut/thai-province-data](https://github.com/kongvut/thai-province-data) (GitHub, MIT license) — downloaded with explicit user approval since no zip-code reference existed anywhere in the Drive folder | `bronze.thai_geo_province/district/subdistrict` | `silver.thai_geography`, `silver.zip_code_admin_crosswalk`, `silver.zip_code_primary_district` |

**Deliberately excluded from Phase 1, from the same group:**
- `raaycchanghwad.csv` / `raay-ameph.csv` (group 4) — redundant roll-ups of the same data already present at finer grain inside `stat_t.txt` (confirmed by comparing row structure; the source's own `NOT_INCLUDED.csv` notes an equivalent duplicate for `raaytambl.csv`).
- `stat_t60.xls` … `stat_t68.xls` (group 4) — yearly historical snapshots (BE 2560–2568). Useful for a future trend table, not needed for current-state coverage KPIs. Old `.xls` binary format needs a separate parser (`xlrd`), deferred.

## Phase 2 — ingested on explicit instruction, including restricted groups

Everything below was loaded into Bronze and Silver on 2026-10-18 at the
explicit instruction of the project owner, **overriding the Phase-1
decision above to leave groups 1/2/3/9/10 out**. Recorded here as the
audit trail for that decision: the usage-rights caveat from the source
README still applies to this data; loading it into the local warehouse was
the owner's call and risk to accept, not a determination that the
data owner's terms were actually cleared.

| Group | Files used | Bronze table(s) | Silver table(s) |
|---|---|---|---|
| 2_HDC_region6_13_by_age_api | 19 CSVs: chronic-disease incidence/population/death by age, health regions 6 & 13 | `hdc_disease_pop_age`, `hdc_disease_incidence`, `hdc_disease_death_age` | same names, typed + BE→CE year conversion |
| 9_from_repo_stored_but_unused | 330 JSON files (HDC occupational-health API cache) + 3 PDFs | `hdc_occupational_health` (flattened from nested JSON); PDFs folded into the inventory table below | *(none — see "Bronze-only" note)* |
| 10_DDS_extracted_from_pdf | `track_e_dds_yearly.csv`, `dds_snapshot_history.csv` | `dds_yearly_disease_ranking`, `dds_unit_indicator_snapshot` | `dds_yearly_disease_ranking` typed |
| 1_DDS_health_region_reports_2022-2026 | 10 PDFs (weekly disease surveillance, regions 6 & 13) + 3 more PDFs from group 9 | `dds_pdf_report_inventory` (filename/size/sha256 only) | *(none — see "Bronze-only" note)* |
| 6_other_health_and_population_tables | 4 clean CSVs: disease case counts, subdistrict case counts, sick-leave by group, disease-by-year | `other_health_disease_cases`, `other_health_subdistrict_cases`, `other_health_sick_by_group`, `other_health_disease_by_year` | same names, typed + BE→CE conversion |
| 7_Lat_Krabang_district_office_tables | 9 of 10 CSVs: population/deaths by subdistrict, universities, vocational colleges, schools, hospitals, religious sites, risk points, businesses | `lat_krabang_population_by_subdistrict`, `lat_krabang_deaths_by_subdistrict`, + 7 POI tables | `lat_krabang_population_by_subdistrict` (pivoted to long), `lat_krabang_points_of_interest` (7 POI tables consolidated, type-specific fields in a JSON column) |
| 8_KMCH_catchment_places_lists | 4 CSVs (2 column shapes, unified) | `kmch_catchment_places` | `kmch_catchment_places`, typed |

**Deliberately still not loaded, even under "load everything":**
- **Group 3** (HDC manual exports) — the source's own README states this duplicates Group 2's API-pulled data. Loading it would add ~400 messy files of pure redundancy, not new information.
- **Lat Krabang's 10th file** (`-2564.csv`, community-level data) — contains a real community leader's name and phone number (`name_head`, `tel`). Not copied into this repo, not loaded into Bronze, not loaded anywhere. If the non-PII columns (population/housing counts by community) are wanted later, that's a column-level extraction job, not a blanket load.
- **DDS PDF content** — the 13 PDFs (weekly surveillance reports) are tracked as a document inventory (filename, size, SHA-256) only. No OCR/table-extraction tooling was available this session to turn them into structured rows; that's a distinct, larger task, not silently skipped.
- **Group 6/7's `.xlsx` files** and the ~400 oddly-named files in group 6 beyond the 4 clean CSVs — deferred, not dropped, pending a file-by-file pass similar to what group 7 got.

**Business-registry note** (`lat_krabang_businesses` / `lat_krabang_points_of_interest` poi_type='business'): most rows are registered company names, but Thai law permits sole proprietors to register under their own personal name, and some rows do — e.g. one entry is literally a person's name, not "... Co., Ltd." That's public business-registration record, not a separate leak, but worth knowing before building anything that surfaces this table directly.

**Repo note**: none of this Phase 2 data is committed to git, regardless of whether a given group carries the usage-rights caveat — see `.gitignore`. The HDC/DDS/Lat Krabang raw files stay local-only; only the SQL/Python code that loads them is version-controlled. A fresh clone needs these files manually re-obtained from the original Drive folder before running the pipeline (same pattern as `stat_t.txt`).

## Phase 2 Gold promotion + Metabase dashboards (2026-10-18)

Selected Phase 2 Silver tables were promoted to Gold (`Fact_HDC_Pop_Age`,
`Fact_HDC_Incidence`, `Fact_HDC_Death_Age`, `Fact_DDS_Disease_Ranking`,
`Fact_Lat_Krabang_Population`, `Fact_Lat_Krabang_Deaths`,
`Dim_Lat_Krabang_POI`) so Metabase — which can only see `gold.*` via
`metabase_ro` — could build dashboards on them. Three dashboards exist:

| Dashboard | Data | Governance |
|---|---|---|
| HDC Chronic Disease Surveillance | `Fact_HDC_*` (groups 2 restricted) | **Restricted** — description field on the dashboard itself carries the usage-rights warning |
| DDS Disease Ranking (2025) | `Fact_DDS_Disease_Ranking` (group 10, restricted) | **Restricted** — same warning in the dashboard description |
| Lat Krabang Local Area Profile | `Fact_Lat_Krabang_*`, `Dim_Lat_Krabang_POI` (group 7, unrestricted) | No restriction |

The restricted dashboards' description fields carry the usage-rights
warning directly in Metabase, not just in this doc — so anyone who later
gets view access to this Metabase instance sees the caveat before
exploring the data, not after.

**Two bugs found and fixed while building these:**
1. `province_code` was ambiguous in the Gold load script's `GROUP BY`
   (both the Silver table and the province-name lookup subquery have that
   column) — silently produced **zero rows** in every HDC/DDS Gold table
   on the first attempt. Fixed by qualifying every reference.
2. Lat Krabang's population/deaths-by-subdistrict source files each
   include a `รวม` ("Total") row alongside the real subdistricts,
   pre-summed by the source. Summing the table without excluding it
   doubles the true total — caught by comparing `SUM(male)` (84,355,
   matching the real total) against what a naive sum-including-รวม would
   have given (168,710). Also discovered while fixing this: the deaths
   data had a Silver DDL table declared but no transform ever written for
   it — it was stuck in Bronze only. Both are now fixed and loaded through
   to Gold.

**Data characteristic, not a bug**: the HDC data (`hdc_by_age`) only
covers Samut Prakan and Chachoengsao (province codes 11, 24) — no Bangkok
rows exist despite the source folder being named `HDC_region6_13...`.
Dashboard panels and any future queries against `Fact_HDC_*` should expect
only those two provinces.

## Correction found during validation: `stat_t.txt` is not a single snapshot

Initial assumption (stated above when scoping this phase) was that `stat_t.txt`
was a current-month snapshot. Validating the loaded data after ingestion
showed otherwise: **it's a 28-point year-end time series**, one row set per
December from Thai Buddhist year 2536 to 2563 (`yymm` values `3612` … `6312`,
i.e. December 1993 – December 2020 CE) — confirmed by Bangkok's `total`
population column tracking real historical values year over year (5.57M in
1993 rising to 5.68M by 2020), not a constant.

**Two consequences:**
1. It's more useful than originally scoped — this is 28 years of population
   history "for free," not just one point in time.
2. **It is 6 years stale relative to today (2026)** — the most recent year
   available is BE2563/2020. The `stat_a67.xls`/newer yearly files in the
   source folder (not yet ingested, see above) likely carry more recent
   years; worth pulling into a Phase 2 if current-year denominators matter
   for a coverage-rate KPI.
3. **Any query against `silver.population_reference_subdistrict` must
   `GROUP BY yymm`** (or filter to a single `yymm`) before summing `total`/
   `male`/`female`/`house` — summing across all 28 years without that filter
   silently produces a ~28x-inflated number with no error (this is exactly
   the bug caught during validation: Bangkok summed to 158.8M instead of
   ~5.6M).

## Repo note: `stat_t.txt` is gitignored

`external-sources/dopa/stat_t.txt` (50MB) is excluded from version control —
too large for git, and unlike the NSO/thai-geo files it has no stable
re-fetch URL (it came from the manually-downloaded Google Drive folder, not
a public API). A fresh clone of this repo needs that file manually placed
back at the same path before running `docker compose run --rm elt-runner`,
or the DOPA bronze/silver load step will fail on a missing file. Everything
else under `external-sources/` (NSO CSVs, Thai geo CSVs) is small enough to
commit directly and is in version control.

## Full-project defect audit (2026-10-19)

A systematic audit across row reconciliation, aggregate-row contamination,
year/type conversion, loader column alignment, Metabase usage, orphaned
objects, security, and idempotency. Findings:

**Clean (verified, not assumed):**
- Bronze→Silver row counts reconcile 1:1 for all 8 source pipelines.
- Silver→Gold aggregations preserve sums exactly (spot-checked 5 measures);
  no join fan-out — `thai_geography` has no province_code or district_code
  mapping to more than one English name.
- No BE/CE year leakage; every year field lands in a plausible CE range.
- Zero numeric parse failures — every non-null source value survives to
  Silver. `investment_thb` correctly uses `DECIMAL` (an `INT` would have
  overflowed on the 122-billion-THB max value).
- Loader column counts match real source headers for all 19 HDC files, all
  9 Lat Krabang files, and all 4 KMCH shapes; a specific known source row
  was traced end-to-end to confirm no column shift.
- Every Gold table is referenced by at least one Metabase card; no
  orphaned SQL files; `.env` and all restricted data stay untracked.
- **Pipeline is genuinely idempotent** — two consecutive full runs produce
  byte-identical exact row counts across all three schemas.

**Defects found and fixed — the "pre-summed total mixed into detail rows"
class, same as the NSO 2x and Lat Krabang `รวม` issues:**
1. `other_health_disease_cases` carried a `รวมทั้งหมด (ยอดจริง)` grand-total
   row equal to the detail sum — unfiltered `SUM()` returned exactly 2x
   (110,108 vs true 55,054).
2. `other_health_sick_by_group` carried `รวม` total rows per
   (province, sex, year) — also exactly 2x (4,791,542 vs true 2,395,771).
3. `dds_yearly_disease_ranking` ranks rollup categories alongside their own
   subtypes (dengue combined vs. its two components) — a latent 9,575-case
   over-count on any province total.

All three now carry an `is_aggregate_row` flag rather than being deleted —
the rollup row is the right figure to quote for a category total, and the
subtypes are right for a breakdown; they just must not be mixed in one
aggregate.

**One false positive, deliberately not "fixed":**
`โรคไข้เลือดออกรวม (DF+DHF+DSS)` in `other_health_disease_by_year` contains
`รวม` but has **no** separate subtype rows in that table — it's a single
legitimate disease entry, so flagging it would have been wrong.

**Zombie tables removed:** `silver.zip_code_admin_crosswalk` and
`silver.zip_code_primary_district` existed in the live warehouse with data
but had **no DDL backing them in version control** — when they were
removed with the clinic pipeline, the `CREATE` *and* the `DROP` were
deleted together, so any warehouse that had already built them kept them
forever: invisible to code, never refreshed, and absent on a fresh clone.
Defensive `DROP`s were added so the live schema converges back to the code.

**Known gap, not a defect:** five Silver tables (`kmch_catchment_places`,
`other_health_disease_by_year`, `other_health_disease_cases`,
`other_health_sick_by_group`, `other_health_subdistrict_cases`) are
cleansed but never promoted to Gold, so Metabase cannot see them. That's a
scope decision rather than a bug, but it means that data is currently
loaded and paid for without being usable in the BI layer.

## Clinic/patient data removal (2026-10-19)

A zip-code ↔ Thai admin-code crosswalk (`silver.zip_code_admin_crosswalk`,
`silver.zip_code_primary_district`) was previously built and joined into
`gold.Dim_Patient.district_code`/`province_code` so clinic registrations
could be analyzed by catchment district. That entire line of work is gone
now, on explicit instruction to exclude everything not sourced from this
Drive folder (the clinic data was from a hospital's own vaccination
portal, not this folder):

- The `clinic_portal` source database, its Docker container, volume, and
  the dump file that seeded it (`source-db/init/01-clinic-portal-dump.sql`)
  are deleted — not stopped, not archived, actually removed. There is no
  copy of that data left in this project.
- Every Bronze/Silver/Gold table built from it (`Patient`, `Screening_*`,
  `Company`, `Dim_Patient`, `Dim_Company`, `Dim_Question`,
  `Fact_Patient_Registration`, `Fact_Screening_Response`, and the
  now-unused `Dim_Date` calendar table) is deleted, along with the Python
  loader (`extract_load_bronze.py`) and every SQL file that created or
  populated them.
- The zip-code crosswalk tables above are **also removed** — they existed
  solely to resolve `Dim_Patient.zip_code`, and nothing in the surviving
  warehouse carries a zip code field. `silver.thai_geography` (the
  underlying province/district/subdistrict **name** lookup, as opposed to
  the zip-specific crosswalk) is kept — several surviving Gold tables
  (`Dim_District_Population`, `Dim_Population_By_Age_Sex`, `Fact_HDC_*`,
  `Fact_DDS_Disease_Ranking`) join against it purely to resolve English
  province/district names, so it's still load-bearing infrastructure, not
  orphaned code.
- Verified after the rebuild: `SHOW DATABASES` no longer lists
  `clinic_portal` at all (the container is gone), and a search across
  `information_schema.tables` for `%Patient%`/`%Screening%`/`%Company%`
  returns zero rows anywhere in `bronze`/`silver`/`gold`.
- None of the four Metabase dashboards built in this project ever
  referenced the clinic tables (checked by searching every saved card's
  SQL before deleting anything), so no dashboard cleanup was needed.

# External Reference Data — Provenance & Scope

Source: a Google Drive folder (`share_unprocessed_20261010`) containing 10
groups of external population/epidemiological data collected for the
broader KMCH catchment-analytics effort. This is **not** a replica of the
vaccinework OLTP database — it's reference data brought in to support
geographic/demographic KPIs (catchment population denominators, coverage
rates) that the vaccination portal's own schema can't answer alone.

## Phase 1 — ingested (this round)

| Group | Files used | License / source | Bronze table | Silver table |
|---|---|---|---|---|
| 4_DOPA_population_by_month_and_area | `stat_t.txt` (294,474 data rows — nationwide province→district→subdistrict→village hierarchy) | Thailand DGA Open Government License, via data.go.th / DOPA | `bronze.dopa_population_monthly` | `silver.population_reference_subdistrict` |
| 5_NSO | `reg_age_2567.csv`, `reg_prov_2567.csv` (population by age × sex, national + Bangkok/Samut Prakan/Chachoengsao — the catchment provinces) | Official NSO StatHub (`TNSO:DF_01POP_REG`), pulled 2026-10-04 | `bronze.nso_population_registration` | `silver.population_reference_age_sex` |
| *(not from the Drive folder)* | `provinces.csv`, `districts.csv`, `sub_districts.csv` — zip code ↔ subdistrict/district/province, 77 provinces / 930 districts / 7,436 subdistricts | [kongvut/thai-province-data](https://github.com/kongvut/thai-province-data) (GitHub, MIT license) — downloaded with explicit user approval since no zip-code reference existed anywhere in the Drive folder | `bronze.thai_geo_province/district/subdistrict` | `silver.thai_geography`, `silver.zip_code_admin_crosswalk`, `silver.zip_code_primary_district` |

**Deliberately excluded from Phase 1, from the same group:**
- `raaycchanghwad.csv` / `raay-ameph.csv` (group 4) — redundant roll-ups of the same data already present at finer grain inside `stat_t.txt` (confirmed by comparing row structure; the source's own `NOT_INCLUDED.csv` notes an equivalent duplicate for `raaytambl.csv`).
- `stat_t60.xls` … `stat_t68.xls` (group 4) — yearly historical snapshots (BE 2560–2568). Useful for a future trend table, not needed for current-state coverage KPIs. Old `.xls` binary format needs a separate parser (`xlrd`), deferred.

## Explicitly NOT ingested — needs a decision before any future phase touches them

- **Groups 1, 2, 3, 9, 10** (DDS disease-surveillance PDFs/reports, HDC region 6/13 chronic-disease exports, HDC manual exports, repo-stored-but-unused dumps, DDS-extracted-from-PDF tables): the source folder's own README states **usage terms from the data owner are not yet confirmed and the data must not be redistributed further.** None of this was copied into this project. If there's a reason to use it later, get that confirmation first — this applies even to local-only use if the warehouse is ever shared, backed up externally, or demoed to the partner hospital.
- **Group 3** is additionally redundant with Group 2 (same HDC data, pulled manually instead of via API) — would be skipped even if cleared.
- **Group 6** (other health/population tables) and **Group 7** (Lat Krabang district office tables): undocumented, mixed CSV/Excel formats, inconsistent/garbled filenames, no per-file schema description. Needs manual review file-by-file before a sensible ingestion design can be written.
- **Group 8** (KMCH catchment places lists): not health data — a travel-time/market-potential place list for outreach planning. No postal code, zip code, or administrative code to join against `Dim_Patient` or the Phase 1 reference tables. Potentially useful for a separate "outreach planning" view, not a data-warehouse dimension.

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

## Zip-code crosswalk — built and joined to Gold

The zip ↔ admin-code crosswalk flagged above as the next step is now built
and wired all the way into Gold:

- `silver.zip_code_admin_crosswalk` — full-fidelity bridge, one row per
  (zip_code, subdistrict_code). A zip code is **not** 1:1 with a district:
  167 of 966 distinct zip codes in the reference data (17%) legitimately
  span more than one district, so this table preserves every subdistrict a
  zip could mean.
- `silver.zip_code_primary_district` — one row per zip_code, resolved to its
  most-common district (tie-break: lowest district code), with
  `district_count` and `is_ambiguous` so the simplification is visible
  rather than silently hidden.
- `gold.Dim_Patient` now carries `district_code`, `district_name_en`,
  `province_code`, `province_name_en`, `is_geo_ambiguous` — resolved via a
  `LEFT JOIN` to `zip_code_primary_district` on load, so patients with a
  missing/invalid zip (one patient has `730000`, a 6-digit value — invalid
  for a Thai postal code) simply get NULL geography rather than a bad match
  or a failed load.

Validated against real data: zip `10520` resolves to Lat Krabang,
Bangkok — the hospital's own district — and a coverage-rate query (resident
population denominator from `silver.population_reference_subdistrict`,
year BE2563/2020) shows Lat Krabang with the highest registration
penetration of any district, falling off with distance, exactly as a real
catchment-area pattern should look. See the example query in
[02_data_dictionary.md](02_data_dictionary.md#5-example-executive-kpi-queries-metabase-ready).

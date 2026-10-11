# ML Team Onboarding — Clone, Run, Connect

This doc is for pulling data out of this warehouse into Python/pandas for
model development. For BI dashboards, see the main [README.md](../README.md)
instead — this doc skips the Metabase setup wizard and goes straight to a
database connection.

**This warehouse has no clinic/patient data.** Everything in it is
externally-sourced reference and health-surveillance data — population
statistics, disease surveillance exports, local-area tables — not a
hospital's own records. Keep that in mind when deciding what a model
trained on this data can and can't claim.

## 1. Clone and configure

```powershell
git clone <this-repo-url> clinical-dwh
cd clinical-dwh
Copy-Item .env.example .env
```

Open `.env` and change the `ChangeMe_*` passwords if this will run anywhere
other than your own laptop.

**Manual steps before the first run** — these files are gitignored and
must be re-obtained from whoever shared the repo with you:
- `external-sources/dopa/stat_t.txt` (50MB, DOPA population data) — skip
  it and every other table still loads fine; only the DOPA population
  step fails.
- `external-sources/hdc_by_age/`, `external-sources/hdc_occupational/`,
  `external-sources/dds_extracted/`, `external-sources/dds_pdf_inventory/`,
  `external-sources/lat_krabang/` — these carry the HDC/DDS usage-rights
  caveat described in §4 below. Get explicit confirmation on redistribution
  rights before pulling these into anything beyond your own local copy of
  this warehouse.

## 2. Start the warehouse and run the pipeline

```powershell
docker compose up -d warehouse-db
docker compose run --rm elt-runner
```

The second command does the actual Bronze → Silver → Gold build and prints
a row-count summary when it's done. It's idempotent — rerun it any time,
no cleanup needed in between.

You do **not** need to start the `metabase` service for this workflow;
skip straight to querying the warehouse from Python.

## 3. Connect from Python

Use the **`metabase_ro`** account (already created by the warehouse's init
script) and point at the `gold` database:

```powershell
pip install pandas sqlalchemy pymysql
```

```python
import pandas as pd
from sqlalchemy import create_engine

# Values match .env — DWH_DB_HOST_PORT is the HOST-side port (3308 by
# default), since you're connecting from outside Docker, not from another
# container on the same network.
engine = create_engine(
    "mysql+pymysql://metabase_ro:ChangeMe_Metabase_Ro_2026!@localhost:3308/gold"
)

population = pd.read_sql("SELECT * FROM Dim_District_Population", engine)
hdc_incidence = pd.read_sql("SELECT * FROM Fact_HDC_Incidence", engine)
dds_ranking = pd.read_sql("SELECT * FROM Fact_DDS_Disease_Ranking", engine)
```

## 4. What you can model with this data

| Gold table | What it gives you |
|---|---|
| `Dim_District_Population` | District population time series, 1993–2020 (treat pre-1997 as a separate era — see §5) |
| `Dim_Population_By_Age_Sex` | National + 3-province age×sex population pyramid, single year (2024) |
| `Fact_HDC_Pop_Age` / `Fact_HDC_Incidence` / `Fact_HDC_Death_Age` | Chronic disease (diabetes, hypertension, COPD, coronary, cancers) burden by age group, **2022–2026** — the one genuinely multi-year series in this warehouse, good for trend/forecast tasks. ⚠ Restricted use, see below. |
| `Fact_DDS_Disease_Ranking` | Top-ranked diseases by province, single year (2025) — not a trend table. ⚠ Restricted use, see below. |
| `Fact_Lat_Krabang_Population` / `Fact_Lat_Krabang_Deaths` | Population/deaths by subdistrict — only 6 subdistricts, too small for anything beyond description |
| `Dim_Lat_Krabang_POI` | Points of interest (schools, hospitals, businesses, risk points) — categorical/count features for a local-area model |

**A natural first model**: forecast next-year incidence for a chronic
disease using `Fact_HDC_Incidence`'s 2022–2026 series — the only table
here with enough time points for a real trend task rather than a
single-snapshot description.

```python
df = pd.read_sql("""
    SELECT disease, province_name_en, year_ce, target, result, achievement_rate_pct
    FROM Fact_HDC_Incidence
    ORDER BY disease, province_name_en, year_ce
""", engine)
```

## 5. ⚠ Usage-rights restriction — read before training or publishing

`Fact_HDC_*` and `Fact_DDS_Disease_Ranking` are built from data whose
redistribution rights are **not confirmed with the data owner** (see
[03_external_reference_sources.md](03_external_reference_sources.md)).
Pulling this data into your own notebook for local exploration is the
same use the warehouse owner already accepted the risk for. **Publishing
a model trained on it, or sharing derived statistics outside this local
environment, is a step beyond that** — raise it with whoever owns this
data before doing either, don't treat it as a technical question to work
around.

## 6. Known limitations — read before trusting a model

- **HDC age groups have no documented numeric boundaries.** The source
  system's own age_group1–5 codes aren't explained anywhere in the
  export. Ordering strongly suggests youngest→oldest (Group 5 has the
  highest disease burden across every chronic condition, consistent with
  age being a real risk factor), but that's an inference, not confirmed
  from the source.
- **HDC data covers Samut Prakan and Chachoengsao only** — no Bangkok,
  despite the source folder being named `HDC_region6_13...`. Don't filter
  for `province_code=10` and get confused by an empty result.
- **DDS ranking is a single year (2025).** There's no DDS time series in
  this warehouse — don't build a trend feature from it.
- **`Dim_District_Population`'s pre-1997 rows are a different data era.**
  The source changed its registration-office coding scheme around
  1996/1997, producing a ~10x population discontinuity that's a genuine
  source artifact, not noise. Any model using this as a time series
  should filter to `year_ce >= 1997` or explicitly handle the break.
- **Population denominator is otherwise stale**: `Dim_District_Population`'s
  latest year is 2020. Fine for structural features (which district is
  bigger than which), not for anything claiming current-year precision.
- **This is a manually-curated extract**, not a live feed. "Freshness"
  means "as of whenever someone last downloaded the Drive folder," which
  for most of these tables was 2026-10.

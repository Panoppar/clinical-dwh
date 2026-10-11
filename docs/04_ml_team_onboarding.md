# ML Team Onboarding — Clone, Run, Connect

This doc is for pulling data out of this warehouse into Python/pandas for
model development. For BI dashboards, see the main [README.md](../README.md)
instead — this doc skips the Metabase setup wizard and goes straight to a
database connection.

## 1. Clone and configure

```powershell
git clone <this-repo-url> clinical-dwh
cd clinical-dwh
Copy-Item .env.example .env
```

Open `.env` and change the `ChangeMe_*` passwords if this will run anywhere
other than your own laptop.

**One manual step before the first run:** `external-sources/dopa/stat_t.txt`
(50MB) is gitignored — it has no stable re-fetch URL since it came from a
manually-downloaded Google Drive folder, not a public API. Get this file
from whoever shared the repo with you and place it at that exact path. If
you skip this, every other table still loads fine; only the DOPA
population-reference step fails.

## 2. Start the warehouse and run the pipeline

```powershell
docker compose up -d source-db warehouse-db
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

patients = pd.read_sql("SELECT * FROM Dim_Patient", engine)
screening = pd.read_sql("SELECT * FROM Fact_Screening_Response", engine)
registrations = pd.read_sql("SELECT * FROM Fact_Patient_Registration", engine)
```

### Why `metabase_ro` and not a new account

It's tempting to provision a separate, broader credential for ad-hoc
feature engineering. We deliberately didn't: `bronze` and `silver` both
still carry raw identifiers (`id_card`, `passport_id`, `tel_no`, `email`,
`address`) for operational traceability, so any account with `SELECT` on
those schemas is a PII access decision, not just a convenience. `gold.*`
is the one schema that's already been deliberately stripped of direct
identifiers (see `Dim_Patient` in
[02_data_dictionary.md](02_data_dictionary.md)) — so `metabase_ro`,
read-only and Gold-only, is the credential that's safe to hand to a second
team by default. If you find Gold too coarse for a specific modeling task
and need raw Silver/Bronze fields, raise that explicitly with whoever owns
this data rather than treating it as a blocker to work around.

## 4. What you can model with this data

| Gold table | What it gives you |
|---|---|
| `Dim_Patient` | Demographics: sex, age/age_band, patient_type (employee/student/corporate/external), has_underlying_disease, resolved geography (district/province), is_geo_ambiguous |
| `Dim_Company` | Corporate cohort membership |
| `Dim_Question` | The 8 pre-procedure screening questions (bilingual text) |
| `Dim_District_Population` | Resident population by district, 1993–2020 — a denominator for any per-capita/catchment feature |
| `Fact_Patient_Registration` | 1 row per patient — registration date, company |
| `Fact_Screening_Response` | 1 row per (patient × screening visit × question) — `is_flagged` is a natural binary classification target |

**A natural first model**: predict `is_flagged` (did this patient trigger a
safety-screening flag) from `Dim_Patient` demographics
(age_band, sex, patient_type, has_underlying_disease, district/province).
Join `Fact_Screening_Response` to `Dim_Patient` and `Dim_Question`, pivot or
filter to the question(s) you care about, and you have a labeled dataset.

```python
df = pd.read_sql("""
    SELECT dp.sex, dp.age, dp.age_band, dp.patient_type_desc,
           dp.has_underlying_disease, dp.province_name_en,
           dq.question_text_en, f.is_flagged
    FROM Fact_Screening_Response f
    JOIN Dim_Patient dp ON dp.patient_sk = f.patient_sk
    JOIN Dim_Question dq ON dq.question_sk = f.question_sk
""", engine)
```

## 5. Known limitations — read before trusting a model

- **Small sample**: 376 patients total. Fine for prototyping a pipeline,
  not enough to claim a generalizable model. Treat any result as a proof
  of concept.
- **Severe class imbalance on `is_flagged`**: flag rates per question run
  0.5%–1.6% (see the example query in
  [02_data_dictionary.md](02_data_dictionary.md#5-example-executive-kpi-queries-metabase-ready)).
  A naive "always predict no" baseline will look deceptively strong on
  accuracy — use precision/recall or PR-AUC, not accuracy, to evaluate.
- **`Dim_Company` / corporate cohort is empty in practice**: the source
  `Company_Employee` table has 0 rows even though `patient_type` claims
  some patients are `company_employee`. Any feature depending on real
  corporate linkage will be all-NULL/zero right now — this is a source
  data-integrity gap, not a bug in this pipeline.
- **Geography resolves to NULL for ~1% of patients**: either a missing zip
  code or an invalid one (one patient has a 6-digit value, which isn't a
  valid Thai postal code). Don't silently drop these rows without checking
  whether that biases your sample.
- **Population denominator is stale**: `Dim_District_Population`'s latest
  year is 2020 (CE), six years behind current when this pipeline was
  built. Fine for structural features (which district is bigger than
  which), not for anything claiming current-year precision.
- **This is seeded/demo data**, not real patient records from production —
  don't treat any descriptive statistic here as representative of the
  actual clinic population.

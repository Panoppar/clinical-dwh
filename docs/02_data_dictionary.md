# Gold Layer — Data Dictionary

## 1. Design rationale

This Gold schema has **no conformed star schema with a central fact
grain** in the traditional Kimball sense — it's a set of independent
dimensional tables, each built from a different external reference
source, joined only where they share a natural key (province code).
That's the honest shape of the data: population statistics, disease
surveillance, and local-area tables don't share a common business
process the way a single organization's OLTP system would.

| Domain | Tables | Source |
|---|---|---|
| Population reference | `Dim_District_Population`, `Dim_Population_By_Age_Sex` | DOPA, NSO |
| HDC chronic disease surveillance | `Fact_HDC_Pop_Age`, `Fact_HDC_Incidence`, `Fact_HDC_Death_Age` | HDC region 6/13 by-age API exports (**restricted**, see §4) |
| DDS disease ranking | `Fact_DDS_Disease_Ranking` | DDS yearly priority report (**restricted**, see §4) |
| Lat Krabang local area | `Fact_Lat_Krabang_Population`, `Fact_Lat_Krabang_Deaths`, `Dim_Lat_Krabang_POI` | Lat Krabang district office tables (unrestricted) |

## 2. Population reference tables

### Dim_District_Population
Grain: one row per district per year. Time series spans 1993–2020 (DOPA);
treat pre-1997 rows as **not comparable** to later years — the source
changed its registration-office coding scheme around 1996/1997, producing
a ~10x population discontinuity that's a genuine data-era boundary, not a
pipeline bug.

| Column | Type | Key | Description |
|---|---|---|---|
| `district_code` | `INT` | **PK (composite)** | Official Thai district code |
| `year_ce` | `INT` | **PK (composite)** | Gregorian year |
| `district_name_th` / `district_name_en` | `VARCHAR(100)` | | |
| `province_code` | `INT` | | |
| `province_name_th` / `province_name_en` | `VARCHAR(100)` | | |
| `male`, `female`, `total`, `house` | `INT` | | Resident population/household counts for that district/year |

### Dim_Population_By_Age_Sex
Grain: one row per (scope, province, **indicator**, sex, age_label, year).
`scope` is `national` or `province` — only Bangkok, Samut Prakan, and
Chachoengsao have province-level rows (the NSO extract was scoped to those
three). Single year (BE2567/CE2024) only — not a time series.

> ### ⚠ Always filter by indicator before aggregating
>
> The NSO source publishes **four different population measures** for every
> (scope, province, sex, age, year) cell. They are not alternative
> estimates of the same number — `DEM_IND24` is the **total**, and the
> other three are its **mutually exclusive components**:
>
> | indicator_code | meaning | national (2024) |
> |---|---|---|
> | `DEM_IND24` | Population from registration — **TOTAL** | 65,951,210 |
> | `DEM_IND109` | Registered in a household registration | 65,588,431 |
> | `DEM_IND48` | Central house registration | 345,830 |
> | `DEM_IND50` | During move (mid-transfer) | 16,949 |
>
> `109 + 48 + 50 = 65,951,210` — exactly `DEM_IND24`. So `SUM()` without an
> indicator filter returns **precisely 2× the true population**.
>
> Use `WHERE is_headline_total = 1` (equivalent to
> `indicator_code = 'DEM_IND24'`) unless you specifically want the
> component breakdown.
>
> This is not hypothetical: an earlier version of this table omitted the
> indicator column entirely, and the resulting population pyramid shipped
> to a live dashboard showing Thailand at **130.9M** against a true ~66M.

| Column | Type | Description |
|---|---|---|
| `scope` | `VARCHAR(10)` | `national` \| `province` |
| `province_code` | `INT` | NULL for `scope='national'` |
| `province_name_th` / `province_name_en` | `VARCHAR(100)` | |
| `indicator_code` | `VARCHAR(20)` | `DEM_IND24` \| `DEM_IND109` \| `DEM_IND48` \| `DEM_IND50` — see warning above |
| `indicator_name_en` | `VARCHAR(100)` | Decoded from the source's own SDMX structure file (`5_NSO/reg_structure.xml`), not guessed |
| `is_headline_total` | `TINYINT(1)` | `1` only for `DEM_IND24`. **Filter on this before any `SUM()`.** |
| `sex` | `VARCHAR(10)` | `Total` \| `Male` \| `Female` |
| `age_label` | `VARCHAR(20)` | Original SDMX age code (kept for traceability) |
| `age_exact` | `INT` | Populated for `exact`, `le`, `ge`, `gt`, `lt` qualifiers |
| `age_qualifier` | `VARCHAR(10)` | See the age-qualifier table below |
| `year_be` / `year_ce` | `INT` | Thai Buddhist Era / Gregorian year |
| `population_count` | `INT` | |

#### `age_qualifier` values

| qualifier | rows | source codes | `age_exact` | meaning |
|---|---|---|---|---|
| `exact` | 3,000 | `Y1`…`Y100` | 1–100 | Single-year-of-age bucket |
| `total` | 36 | `_T` | NULL | All ages combined (a sum — don't add it to the `exact` rows) |
| `le` | 30 | `Y_LE1` | 1 | Age ≤ 1 (infants) |
| `gt` | 30 | `Y_GT100` | 100 | Age > 100 — the open-ended top bracket |
| `other` | 25 | `LUNAR` | NULL | **Unexplained.** Possibly relates to Thai lunar-calendar age counting for infants, but nothing in the source confirms that — treat as unresolved rather than assuming a meaning. |

`ge` and `lt` are handled by the transform but don't appear in the current
extract. Note that `exact` + `le` + `gt` overlap (an infant is in both `Y1`
and `Y_LE1`), so don't sum across qualifiers either — pick one.

## 3. HDC chronic disease surveillance (⚠ restricted — see §4)

Grain note: age_group1..5 are the source system's own codes. **The source
does not document the numeric age boundaries anywhere in the export** —
ordering (Group 1 lowest disease burden → Group 5 highest) strongly
suggests youngest-to-oldest, but treat that as an inference, not a
confirmed mapping. Coverage is Samut Prakan and Chachoengsao only — no
Bangkok rows exist despite the source folder being named
`HDC_region6_13...`.

### Fact_HDC_Pop_Age
One row per (disease, province, year, age_group).

| Column | Type | Description |
|---|---|---|
| `disease` | `VARCHAR(30)` | Short code: `ca_breast`, `ca_cervix`, `ca_lung`, `copd`, `coronary`, `dm`, `emphysema`, `ht`, `stroke` |
| `province_code` / `province_name_en` | | |
| `year_ce` | `INT` | |
| `age_group` | `VARCHAR(20)` | `Age Group 1`–`Age Group 5` |
| `population` | `BIGINT` | At-risk population in that age group |
| `cases` | `BIGINT` | Screened/confirmed cases |

### Fact_HDC_Incidence
One row per (disease, province, year). Diseases: `asthma`, `copd`,
`coronary`, `dm`, `ht`, `ihd`.

| Column | Type | Description |
|---|---|---|
| `target` | `BIGINT` | Screening target population |
| `result` | `BIGINT` | Actual screened/positive count |
| `achievement_rate_pct` | `DECIMAL(6,2)` | `result / target * 100` |

### Fact_HDC_Death_Age
Same grain and age-group caveat as `Fact_HDC_Pop_Age`. Diseases: `copd`,
`coronary`, `dm`, `ht`.

| Column | Type | Description |
|---|---|---|
| `person_time` | `BIGINT` | Person-time denominator |
| `deaths` | `BIGINT` | |

## 4. DDS disease ranking (⚠ restricted — see §4)

### Fact_DDS_Disease_Ranking
One row per (province, year, disease) — top ~20 ranked diseases per
province. **Single year only (2025)** — not a trend table.

| Column | Type | Description |
|---|---|---|
| `province_code` / `province_name_en` / `province_name_th` | | |
| `year_ce` | `INT` | |
| `disease_th` | `VARCHAR(100)` | Disease name, Thai only |
| `case_count`, `death_count` | `BIGINT` | |
| `case_fatality_pct` | `DECIMAL(6,2)` | |
| `rate_per_100k` | `DECIMAL(10,2)` | Normalized rate — use this, not raw `case_count`, when comparing provinces of different sizes |
| `rank_by_cases` | `INT` | 1 = most cases that year in that province |
| `is_provisional` | `TINYINT(1)` | |

## ⚠ Restricted-data note

`Fact_HDC_*` and `Fact_DDS_Disease_Ranking` are built from data whose
redistribution rights are **not confirmed with the data owner**. Loaded
into this local warehouse on explicit instruction — see
[03_external_reference_sources.md](03_external_reference_sources.md) for
the full governance trail. The Metabase dashboards built on these tables
carry the same warning directly in their description field.

## 5. Lat Krabang local area (unrestricted)

### Fact_Lat_Krabang_Population / Fact_Lat_Krabang_Deaths
One row per (subdistrict, sex). Source files include a pre-summed `รวม`
("Total") row alongside the real subdistricts — **excluded** at the
Silver transform step; `SUM(population)` or `SUM(deaths)` over these
tables is safe to use directly without further filtering.

| Column | Type | Description |
|---|---|---|
| `subdistrict_name_th` | `VARCHAR(100)` | |
| `sex` | `VARCHAR(10)` | `male` \| `female` |
| `population` / `deaths` | `BIGINT` | |

### Dim_Lat_Krabang_POI
One row per point of interest (university, vocational college, school,
hospital, religious site, risk point, or business). Most fields are
type-specific and NULL for other types.

| Column | Type | Description |
|---|---|---|
| `poi_type` | `VARCHAR(20)` | `university` \| `vocational_college` \| `school` \| `hospital` \| `religious_site` \| `risk_point` \| `business` |
| `name_th` | `VARCHAR(300)` | |
| `investment_thb` | `DECIMAL(15,2)` | Only for `poi_type='business'`. Most rows are registered company names, but Thai law permits sole proprietors to register under their own personal name — a few rows are literally an individual's name, not "... Co., Ltd." That's public business-registration record, not a data leak, but worth knowing before surfacing this table directly. |
| `student_num` | `INT` | Only for `poi_type='school'` |
| `risk_type` | `VARCHAR(10)` | Only for `poi_type='risk_point'` |

## 6. Example queries (Metabase-ready, Gold-only)

```sql
-- Catchment coverage: Lat Krabang's population vs. whole-district services
SELECT subdistrict_name_th, SUM(population) AS population
FROM Fact_Lat_Krabang_Population
GROUP BY subdistrict_name_th
ORDER BY population DESC;

-- Chronic disease mortality, ranked
SELECT disease, SUM(deaths) AS total_deaths
FROM Fact_HDC_Death_Age
GROUP BY disease
ORDER BY total_deaths DESC;

-- Disease rate per 100k, normalized province comparison
SELECT province_name_en, disease_th, rate_per_100k
FROM Fact_DDS_Disease_Ranking
WHERE rank_by_cases <= 5
ORDER BY rate_per_100k DESC;

-- Province population trend (comparable years only, see §2 caveat)
SELECT year_ce, province_name_en, SUM(total) AS population
FROM Dim_District_Population
WHERE province_code IN (10, 11, 24) AND year_ce >= 1997
GROUP BY year_ce, province_name_en
ORDER BY year_ce;
```

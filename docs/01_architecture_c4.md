# System Architecture — C4 Context Diagram

Scope: how data flows from the shared Google Drive folder, through the
Medallion ELT pipeline, into the Metabase dashboards. This is a **C4
Level 1 (System Context)** diagram — it shows systems and major data
flows, not internal component detail (that lives in the Data Dictionary
and SQL scripts).

This warehouse has **no clinic/patient source system**. Everything in it
originates from externally-sourced reference and surveillance data
(population statistics, health-facility surveillance exports, local-area
tables) collected into one shared Drive folder.

```mermaid
C4Context
    title Regional Health & Population Data Warehouse (System Context)

    Person(analyst, "Analyst / Program Lead", "Reviews population, disease-surveillance, and local-area KPIs")
    Person(steward, "Data Engineer", "Operates and monitors the ELT pipeline")

    Enterprise_Boundary(b0, "Local Docker Environment") {

        System(drive, "Shared Google Drive Folder", "External reference data: DOPA/NSO population statistics, HDC/DDS health-facility surveillance exports, Lat Krabang district office tables, Thai geography reference. Manually downloaded, not a live feed.")

        System_Boundary(b2, "elt-runner container (Python)") {
            System(elt, "ELT Pipeline", "Python + SQL, run on-demand", "Loads flat files into Bronze, transforms Silver, builds Gold")
        }

        System_Boundary(b3, "warehouse-db container (MySQL 8.0)") {
            SystemDb(bronze, "Bronze Schema", "MySQL schema: bronze", "Raw, untransformed 1:1 replicas of source files + load metadata")
            SystemDb(silver, "Silver Schema", "MySQL schema: silver", "Cleansed, conformed, deduplicated, typed entity tables")
            SystemDb(gold, "Gold Schema", "MySQL schema: gold", "Dimensional tables: Dim_District_Population, Dim_Population_By_Age_Sex, Fact_HDC_*, Fact_DDS_Disease_Ranking, Fact_Lat_Krabang_*, Dim_Lat_Krabang_POI")
        }

        System_Boundary(b4, "metabase container") {
            System(metabase, "Metabase", "BI / Dashboarding tool", "Connects ONLY to warehouse-db.gold via a SELECT-only DB account")
        }
    }

    Rel(steward, drive, "Manually downloads/places files into external-sources/", "filesystem")
    Rel(elt, drive, "Reads flat files (CSV/JSON) from external-sources/", "filesystem, bind-mounted")
    Rel(elt, bronze, "Loads raw replicas", "INSERT, batched")
    Rel(elt, silver, "Cleanses & conforms", "INSERT INTO ... SELECT")
    Rel(elt, gold, "Builds dimensions & facts", "INSERT INTO ... SELECT")
    Rel(steward, elt, "Triggers / monitors pipeline runs", "docker compose run")
    Rel(metabase, gold, "Reads dashboard data (read-only)", "MySQL protocol, metabase_ro account")
    Rel(analyst, metabase, "Views dashboards", "HTTPS, browser")

    UpdateLayoutConfig($c4ShapeInRow="2", $c4BoundaryInRow="1")
```

## Flow narrative

1. **Shared Drive → external-sources/**: A data steward manually downloads
   files from the shared Google Drive folder and places them under
   `external-sources/` in this repo. There is no automated sync — if the
   Drive folder changes, someone has to re-download and re-place the
   relevant files, then rerun the pipeline.

2. **external-sources/ → Bronze**: The ELT pipeline reads each flat file
   (CSV, JSON) and lands it in `bronze.*` as close to 1:1 with the source
   structure as the format allows, plus `_bronze_loaded_at` /
   `_source_system` lineage columns. No business logic applied.

3. **Bronze → Silver**: SQL transforms cleanse and conform the data:
   cast/validate numeric and date fields, convert Thai Buddhist-Era years
   to Gregorian, deduplicate, exclude known-bad rows (e.g. pre-summed
   "Total" rows mixed into source files), and consolidate structurally
   similar tables (e.g. Lat Krabang's seven points-of-interest exports
   into one typed table).

4. **Silver → Gold**: `INSERT INTO ... SELECT` scripts build the
   dimensional tables Metabase actually queries — see
   [02_data_dictionary.md](02_data_dictionary.md) for the full table list.

5. **Gold → Metabase**: Metabase connects **exclusively** to the `gold`
   schema using a database account (`metabase_ro`) that is granted
   `SELECT`-only on `gold.*` — it has no grant on `bronze` or `silver` at
   all, so "Gold-only" is enforced by MySQL privileges, not just by
   dashboard convention.

## Design notes

- **No live source system**: unlike a typical OLTP-fed warehouse, there is
  no application writing to a source database here. Every load is a
  manual file-drop followed by a pipeline run. Treat "freshness" as "as of
  whenever someone last downloaded the Drive folder," not real-time.
- **Usage-rights governance**: a subset of this data (HDC/DDS health
  surveillance) carries an unconfirmed-redistribution-rights caveat from
  the data owner — see
  [03_external_reference_sources.md](03_external_reference_sources.md).
  That caveat is also written directly into the relevant Metabase
  dashboards' description fields, not just this doc.
- **Refresh pattern**: every layer uses a **full-refresh (truncate +
  reload)** pattern. The pipeline is idempotent — rerunning it produces
  the same Gold state.

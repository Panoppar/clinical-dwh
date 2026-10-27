"""Generates docs/01_architecture.html, docs/02_data_dictionary.html,
docs/04_gold_layer_and_kpi_guide.html, and docs/05_runbook.html. The first
three read the live schema from %TEMP%\\schema_dump.tsv / row_counts.tsv
(dumped via information_schema) plus hand-written descriptions below;
05_runbook.html is static deployment/operations content. Run with:
    python docs/build_html_docs.py
"""

import os
from collections import defaultdict

TEMP = os.environ.get("TEMP", r"C:\Users\PunPun\AppData\Local\Temp")
SCHEMA_TSV = os.path.join(TEMP, "schema_dump.tsv")
ROWCOUNT_TSV = os.path.join(TEMP, "row_counts.tsv")
DOCS_DIR = os.path.dirname(os.path.abspath(__file__))

CSS = """
:root {
  --bronze: #CD7F32; --silver: #9DA3A8; --gold: #D4AF37;
  --ink: #1a1a2e; --muted: #5a6472; --bg: #fafbfc; --card: #ffffff;
  --border: #e2e5ea; --accent: #2E75B6; --warn: #C00000; --ok: #2e7d32;
}
* { box-sizing: border-box; }
body { font-family: 'Segoe UI', -apple-system, Roboto, sans-serif; background: var(--bg); color: var(--ink);
       margin: 0; padding: 0; line-height: 1.55; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 32px 24px 80px; }
header.page { background: linear-gradient(135deg, #1a1a2e 0%, #2E75B6 100%); color: #fff; padding: 40px 24px; }
header.page h1 { margin: 0 0 8px; font-size: 1.9rem; }
header.page .sub { opacity: .88; font-size: .98rem; max-width: 900px; }
header.page .meta { margin-top: 14px; font-size: .85rem; opacity: .75; }
nav.toc { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px 20px; margin: 24px 0; }
nav.toc a { color: var(--accent); text-decoration: none; margin-right: 18px; font-size: .92rem; }
nav.toc a:hover { text-decoration: underline; }
h2.section { font-size: 1.4rem; margin-top: 44px; padding-bottom: 8px; border-bottom: 3px solid var(--accent); }
h2.section.bronze { border-color: var(--bronze); } h2.section.silver { border-color: var(--silver); }
h2.section.gold { border-color: var(--gold); }
h3.table-title { font-size: 1.08rem; margin: 28px 0 4px; display: flex; align-items: center; gap: 10px; }
.badge { display: inline-block; font-size: .72rem; font-weight: 600; padding: 2px 9px; border-radius: 999px; color: #fff; }
.badge.bronze { background: var(--bronze); } .badge.silver { background: #6b7280; } .badge.gold { background: #b8860b; }
.badge.pending { background: var(--warn); } .badge.ok { background: var(--ok); }
.rowcount { font-size: .85rem; color: var(--muted); font-weight: 500; }
p.table-desc { color: var(--muted); margin: 4px 0 10px; font-size: .93rem; max-width: 900px; }
table.cols { width: 100%; border-collapse: collapse; margin-bottom: 8px; background: var(--card);
             border: 1px solid var(--border); border-radius: 8px; overflow: hidden; font-size: .87rem; }
table.cols th { background: #f1f3f6; text-align: left; padding: 9px 12px; font-weight: 600; color: var(--muted);
                 text-transform: uppercase; font-size: .72rem; letter-spacing: .03em; }
table.cols td { padding: 8px 12px; border-top: 1px solid var(--border); vertical-align: top; }
table.cols tr:nth-child(even) td { background: #fbfbfd; }
code { background: #eef0f3; padding: 1px 6px; border-radius: 4px; font-size: .85em; color: #333; }
.callout { border-left: 4px solid var(--accent); background: #eef5fc; padding: 12px 16px; margin: 16px 0; border-radius: 0 8px 8px 0; font-size: .92rem; }
.callout.warn { border-color: var(--warn); background: #fdecec; }
.callout.ok { border-color: var(--ok); background: #eaf6ea; }
.flow { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin: 22px 0; }
.flow .box { background: var(--card); border: 2px solid var(--border); border-radius: 10px; padding: 14px 18px; font-size: .88rem; min-width: 150px; }
.flow .box.bronze { border-color: var(--bronze); } .flow .box.silver { border-color: #9DA3A8; } .flow .box.gold { border-color: var(--gold); }
.flow .arrow { font-size: 1.4rem; color: var(--muted); }
.svcgrid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; margin: 20px 0; }
.svc { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
.svc h4 { margin: 0 0 6px; font-size: .96rem; }
.svc p { margin: 0; font-size: .85rem; color: var(--muted); }
.pyramid { display: flex; flex-direction: column; align-items: center; gap: 4px; margin: 24px 0; }
.pyramid .level { color: #fff; padding: 10px 18px; border-radius: 6px; font-size: .85rem; text-align: center; }
.kpi-table td.kpi-id { font-family: Consolas, monospace; font-weight: 600; white-space: nowrap; }
footer.page { text-align: center; color: var(--muted); font-size: .8rem; padding: 30px 0; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 800px) { .two-col { grid-template-columns: 1fr; } }
ol.steps { counter-reset: step; list-style: none; padding: 0; margin: 18px 0; }
ol.steps > li { counter-increment: step; position: relative; padding: 4px 0 18px 42px; border-left: 2px solid var(--border); margin-left: 15px; }
ol.steps > li:last-child { border-left: 2px solid transparent; padding-bottom: 0; }
ol.steps > li::before { content: counter(step); position: absolute; left: -15px; top: 2px; width: 28px; height: 28px;
  background: var(--accent); color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: .82rem; font-weight: 700; }
ol.steps h4 { margin: 0 0 6px; font-size: 1rem; }
pre { background: #1a1a2e; color: #e8eaf0; padding: 14px 16px; border-radius: 8px; overflow-x: auto; font-size: .84rem; line-height: 1.5; }
pre code { background: none; color: inherit; padding: 0; }
table.checklist td:first-child { width: 28px; text-align: center; }
"""


def _page(title, header_h1, header_sub, body_html, accent="gold"):
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>{title}</title>
<style>{CSS}</style></head><body>
<header class="page"><div class="wrap" style="padding:0">
<h1>{header_h1}</h1><div class="sub">{header_sub}</div>
<div class="meta">clinical-dwh &middot; generated 2026-10-26 &middot; live-API scope only</div>
</div></header>
<div class="wrap">{body_html}</div>
<footer class="page">clinical-dwh documentation &middot; see docs/03_external_reference_sources.md for full provenance notes</footer>
</body></html>"""


def _load_schema():
    tables = defaultdict(list)  # (schema, table) -> [(col, type, nullable, comment, pos), ...]
    with open(SCHEMA_TSV, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 7:
                continue
            schema, table, col, coltype, nullable, comment, pos = parts
            tables[(schema, table)].append((col, coltype, nullable, comment))
    return tables


def _load_rowcounts():
    counts = {}
    with open(ROWCOUNT_TSV, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == 3:
                counts[(parts[0], parts[1])] = int(parts[2])
    return counts


# ---------------------------------------------------------------------------
# Hand-written descriptions
# ---------------------------------------------------------------------------
TABLE_DESC = {
    ("bronze", "api_nso_income"): "Raw 1:1 landing of NSO's household-income-by-province CSV (table SFD_SPB0802_66). No transformation.",
    ("bronze", "api_bma_community"): "Raw 1:1 landing of BMA's community-registry CSV, one resource per fiscal year (2565/2566/2567).",
    ("bronze", "api_diw_factory"): "Raw landing of DIW's factory registry, amphoe-by-amphoe crawl across 3 provinces. operator_name/phone deliberately excluded (PII).",
    ("bronze", "api_dds_disease_ranking"): "Raw landing of DDS's priority disease-ranking PDF (Table 1 extraction). 0 rows -- DDS's own backend has returned a server-side DB-driver error since 2026-10-25.",
    ("bronze", "api_hdc_report_catalog"): "Reference/lookup: HDC report catalog (report_code -> name, subcatalog, years available). Not fact data.",
    ("bronze", "api_hdc_observations"): "Raw EAV landing of HDC's health-status data API. One row per (report, year, zone, record, field) -- live reports vary column layout per report, so every field is kept generically rather than inventing a schema per report.",
    ("silver", "api_nso_income"): "Cleansed NSO income: year cast Buddhist Era -> Christian Era, value cast to DECIMAL, text fields trimmed.",
    ("silver", "api_bma_community"): "Cleansed BMA community: fiscal_year BE->CE, population/male/female cast to INT.",
    ("silver", "api_diw_factory"): "Cleansed DIW factory: capital/horsepower cast to DECIMAL, workers to INT. PII exclusion carries through from Bronze.",
    ("silver", "api_dds_disease_ranking"): "Cleansed DDS: rank/metrics cast to numeric (thousands-separator-safe). 0 rows -- same DDS outage as Bronze.",
    ("silver", "api_hdc_observations"): "Cleansed HDC EAV: report_name resolved via join against the Bronze catalog, year BE->CE. field_value stays TEXT -- ~116 reports mix counts/rates/percentages under the same generic column, so per-report typing is a Gold concern.",
    ("gold", "dim_date"): "Calendar-year dimension spanning every year observed across the 5 sources.",
    ("gold", "dim_geography"): "Province/district/subdistrict hierarchy, built purely from the live sources' own plain-text geographic labels (NOT DOPA codes -- that dimension was removed with the old Gold layer). Confirmed BMA.district and DIW.amphoe match character-for-character for Bangkok.",
    ("gold", "dim_industry"): "Distinct (TSIC code, factory_type_code) combinations from DIW -- Thailand Standard Industrial Classification, carried as-is (no decode table available).",
    ("gold", "dim_hdc_report"): "HDC report reference, promoted from bronze.api_hdc_report_catalog.",
    ("gold", "dim_disease"): "Distinct disease names from DDS. 0 rows -- same DDS outage as Bronze/Silver; structurally ready.",
    ("gold", "fact_income"): "NSO income fact, resolved to dim_geography (province) and dim_date.",
    ("gold", "fact_factory"): "DIW factory fact, one row per registered factory, resolved to dim_geography (amphoe/district where available) and dim_industry.",
    ("gold", "fact_community_population"): "BMA community population fact, resolved to dim_geography (subdistrict where available) and dim_date.",
    ("gold", "fact_disease_ranking"): "DDS disease-ranking fact. 0 rows -- same DDS outage; resolved to dim_geography (via province code translation), dim_date, dim_disease once populated.",
    ("gold", "fact_hdc_observation"): "HDC fact, PIVOTED from Silver's EAV rows into named columns (target/result/f3_rate/male/female/total) for the headline fields the KPI tree needs. geo_key is resolved from the record's own area name when the report's layout carries one (province_keyed layout); NULL is a real 'not area-resolvable from this report', not a loading gap.",
    ("gold", "agg_economic_by_province_year"): "Feeds Dashboard 2 (Economic & Industrial Development). One row per province x year.",
    ("gold", "agg_population_by_district_year"): "Feeds Dashboard 3 (Population & Community). One row per district x fiscal year.",
    ("gold", "agg_health_kpi_by_province_year"): "Feeds Dashboard 4 (Public Health Surveillance). One row per province x year.",
    ("gold", "obt_regional_composite_index"): "Feeds Dashboard 1 (Executive Overview). Level-3 strategic KPIs (K-STR-01/02/03), min-max normalized 0-100, equal-weighted across components.",

    # kmch-ml input-parity extension (2026-10-26)
    ("bronze", "geo_boundary_subdistrict"): "Raw 1:1 landing of Thailand's canonical ADM3 (subdistrict) reference CSV -- DevelopedbyWill/thailand-canonical-admin-names (GitHub, public, CC BY 4.0), fetched independently of kmch-ml's own repo. Feeds gold.dim_area.",
    ("bronze", "geo_boundary_district"): "Raw 1:1 landing of the matching ADM2 (district) reference CSV, same source.",
    ("bronze", "geo_boundary_polygon"): "Raw 1:1 landing of the ADM3 polygon GeoJSON (full geometry per feature, kept as source-of-truth text -- not used directly by Gold, which only needs the centroid/distance/tier derived from it).",
    ("bronze", "geo_hospital_facility"): "Raw Overpass (OSM) API landing of hospital/healthcare facilities near KMCH. 0 rows -- Overpass's public instance (overpass-api.de, incl. its lz4 mirror) returned HTTP 406 on every request tested 2026-10-26, confirmed blocked from both the container and the host machine directly, unrelated to this code.",
    ("bronze", "geo_travel_matrix"): "Raw OSRM table-API landing: every gold.dim_area unit x every gold.dim_facility destination (always includes the fixed KMCH coordinate regardless of OSM's block above). Public demo server, confirmed working.",
    ("bronze", "tambon_xwalk"): "Raw 1:1 landing of xwalk_tambon_unit.csv -- file-based, not a live API (a deliberate, scoped exception, see docs/06_kmch_ml_gap_closure_plan.md Gap 4). kmch-ml's own authoritative mapping of every original TIS-1099 tambon code to the merged gold.dim_area unit_code it belongs to, used to fix a grouping bug in dim_area's earlier centroid-based fallback heuristic.",
    ("bronze", "dopa_population_year"): "Raw 1:1 landing of dim_population_year.csv -- file-based, not a live API (kmch-ml input-parity gap 1, the previously-deferred \"DOPA population\" gap, see docs/06_kmch_ml_gap_closure_plan.md Gap 1). Fine (5-yr) and coarse age-sex population bands, 9 years (2560-2568 BE), already at gold.dim_area's merged-unit grain.",
    ("bronze", "dopa_population_supplement"): "Raw 1:1 landing of pop_total_supplement_2560_2564.csv -- pop_total only, backfills the 5 years (2560-2564) missing from dopa_population_year for Samut Prakan/Chachoengsao units specifically. Confirmed zero overlapping (unit_code, year_be) pairs with the main file before this was built -- a clean union, not a conflict to reconcile.",
    ("bronze", "bma_migrant_general"): "Raw 1:1 landing of BMA's migrant-worker-permit publication (2568 BE snapshot), section A: 6 permit categories, no nationality breakdown (kmch-ml input-parity gap 2, file-based). Grain: 1 grand-total row + 10 zone rows (BMA's own zone numbering, each zone a list of districts).",
    ("bronze", "bma_migrant_mou_import"): "Same source, section B: the 'นำเข้าตาม MOU' category broken down by nationality (Myanmar/Laos/Cambodia/Vietnam). Verified: this section's own grand total exactly equals bma_migrant_general's 'นำเข้าตาม MOU' category total.",
    ("bronze", "bma_migrant_renewal"): "Same source, section C: the 'ต่ออายุ' (renewal) category broken down by nationality. Same cross-section reconciliation verified as bma_migrant_mou_import.",
    ("bronze", "bma_migrant_illegal"): "Same source, section D: the 'จดทะเบียนสถานะไม่ถูกกฎหมาย' (illegal registration) category broken down by nationality. Same cross-section reconciliation verified as bma_migrant_mou_import.",
    ("silver", "geo_boundary_subdistrict"): "Cleansed subdistrict reference: coordinates cast to DECIMAL, text trimmed.",
    ("silver", "geo_boundary_district"): "Cleansed district reference: coordinates/area cast to DECIMAL, text trimmed.",
    ("silver", "geo_hospital_facility"): "Cleansed OSM facilities. 0 rows -- same Overpass block as Bronze.",
    ("silver", "geo_travel_matrix"): "Cleansed OSRM travel matrix: duration/distance cast to DECIMAL.",
    ("silver", "dopa_population_by_unit_year"): "Cleansed, unioned DOPA population: casts text to INT, converts year_be->year_ce, merges dopa_population_year + dopa_population_supplement (disjoint (unit_code,year_be) pairs, confirmed). data_source flags 'full' (age-sex bands) vs 'total_only' (supplement backfill) rows.",
    ("silver", "bma_migrant_worker_permit"): "Melts the 4 bronze.bma_migrant_* wide tables into one long table, grain (zone, permit_category, nationality). nationality is NULL for the 3 categories with no breakdown available; both a nationality-NULL row and 4 nationality rows exist for the other 3 (deliberate two-grain design). Grand-total rows excluded (same is_rollup_row convention as elsewhere) -- verified every section's total exactly equals the sum of its 10 zones before relying on this.",
    ("gold", "dim_area"): "Catchment-area dimension (kmch-ml input-parity gap 1). 312 units across the 3 catchment provinces, matching kmch-ml's own documented total exactly. Grain is normally a subdistrict; Bangkok's 13 post-2019 khwaeng splits merge into their 7 pre-2019-split parent tambons (not district-grain -- is_district_level_fallback is kept as the column name but now means \"merged pre-split group\"), grouped via bronze.tambon_xwalk (kmch-ml's own authoritative mapping) rather than a centroid heuristic -- see docs/06_kmch_ml_gap_closure_plan.md. area_km2/centroid_lat/lon/contains_kmch_point all derive from the same polygon consistently. catchment_tier/dist_to_kmch_km computed via Haversine distance from the fixed KMCH coordinate -- verified: the hospital's own subdistrict (ลาดกระบัง) correctly lands as the closest, core-tier unit, and unit 101104 (ลำปลาทิว) is the one unit whose polygon physically contains the hospital's coordinate, matching kmch-ml's reference export exactly.",
    ("gold", "dim_tambon_unit_xwalk"): "Tambon-to-unit crosswalk (kmch-ml input-parity gap 4/6). Grain: one row per original TIS-1099 tambon code, finer than dim_area's merged-unit grain -- the 13 post-2019 khwaeng-split tambons each get their own row pointing at their shared merged unit_code. Carries postal_code and adm3_pcode (the exact key the nationwide ADM3 polygon geojson uses) so that geometry can be joined straight to dim_area without a separate crosswalk.",
    ("gold", "dim_facility"): "Hospital/facility dimension (kmch-ml input-parity gap 3). Always contains at least the fixed KMCH coordinate (destination_id='KMCH') regardless of whether OSM facility discovery has landed anything.",
    ("gold", "fact_hdc_weekly_observation"): "4 PM2.5-linked weekly disease reports (kmch-ml input-parity gap 2) -- confirmed already discovered by the existing HDC subcatalog crawl (no ingest change needed), just never pivoted into Gold before. Normalized (not wide-pivoted: each week has 4+ metric variants, e.g. m/y/z/zy, undocumented meaning per HDC) into (report, year, zone, disease group, week 1-53 or NULL for annual totals, variant, value).",
    ("gold", "fact_hospital_access"): "Raw unit-to-facility travel matrix (kmch-ml input-parity gap 3) -- duration/distance only, explicitly excludes kmch-ml's derived accessibility scores (Huff share, E2SFCA), which are analytical modeling out of scope here. Verified: road distance consistently exceeds straight-line distance as expected; closest units by straight-line also show shortest drive times.",
    ("gold", "fact_population_by_area"): "DOPA population by unit and year (kmch-ml input-parity gap 1, the previously-deferred \"DOPA population\" gap, now built from files supplied directly -- see docs/06_kmch_ml_gap_closure_plan.md Gap 1). Grain: (unit, year). data_source='full' rows carry fine/coarse age-sex bands; 'total_only' rows (the Samut Prakan/Chachoengsao 2560-2564 backfill) carry pop_total only. Verified against source files row-for-row (e.g. unit 100101/2560 and unit 110101/2560 match exactly).",
    ("gold", "dim_industry_division"): "TSIC 2009 2-digit division code -> English name (kmch-ml input-parity gap 3). A fixed, static, seeded reference list (34 divisions, scoped to those actually observed in the DIW factory registry's 3 catchment provinces), not ingested from any source.",
    ("gold", "agg_industrial_concentration_by_unit_division"): "Industrial location quotient, unit x division grain (kmch-ml input-parity gap 3). Recomputed from fact_factory + dim_industry on every refresh, scoped to TSIC-2009-5-digit-coded factories only. \"region\" = the whole 3-catchment-province scope, not per-province (confirmed against kmch-ml's own export: region_share_workers for a division is identical across all 3 provinces). Verified: lq_workers/lq_factories match kmch-ml's reference export to within expected DIW-snapshot drift; industrial_concentration is a best-effort approximation of their own flag (not exact parity -- their precise rule looks like a statistical significance test, not a flat threshold).",
    ("gold", "agg_industrial_concentration_by_unit"): "Industrial concentration summary, unit grain (kmch-ml input-parity gap 3) -- top division, its LQ, and a concentration flag per unit. factories_registered/workers_registered are ALL factories regardless of TSIC classification; factories_tsic2009_5digit is the classified subset the LQ figures are based on.",
    ("gold", "dim_bma_zone"): "BMA's own 10-zone grouping (kmch-ml input-parity gap 2, file-based). A different grain than dim_geography/dim_area -- a zone covers several districts, hence bridge_bma_zone_district rather than a geo_key column here.",
    ("gold", "bridge_bma_zone_district"): "Many-to-many zone<->district bridge, parsed from the source file's own district-name list (not hardcoded) and matched against dim_geography.district_name. Verified: all 50 zone-district links matched with 0 unmatched names.",
    ("gold", "fact_migrant_worker_permit"): "Migrant worker permits by zone (kmch-ml input-parity gap 2). Single snapshot (2568 BE / 2025 CE), not a time series. nationality NULL = category-level total (bma_migrant_general); nationality-specific rows (4 per category) exist for the 3 categories with a breakdown available. Verified against source file row-for-row, including the nationality-rows-sum-to-category-total internal consistency check.",
}

GENERIC_LINEAGE_DESC = {
    "bronze_id": "Surrogate primary key.",
    "source_file_name": "Landing-zone object key this row was shredded from.",
    "source_folder": "Landing-zone bucket/prefix.",
    "source_sheet_name": "Sheet name, where the source format has one (NULL otherwise).",
    "source_row_number": "1-based row position within the source file/response.",
    "file_hash": "SHA-256 of the landed object's bytes.",
    "ingestion_batch_id": "Groups every row loaded in one pipeline run.",
    "ingested_at": "Timestamp this row was written to Bronze.",
    "source_system": "Which of NSO/BMA/DIW/DDS/HDC this row came from.",
}


def _col_desc(schema, table, col, db_comment):
    if db_comment:
        return db_comment
    if schema == "bronze" and col in GENERIC_LINEAGE_DESC:
        return GENERIC_LINEAGE_DESC[col]
    return ""


def build_data_dictionary():
    tables = _load_schema()
    counts = _load_rowcounts()

    table_order = {
        "bronze": ["api_nso_income", "api_bma_community", "api_diw_factory",
                   "api_dds_disease_ranking", "api_hdc_report_catalog", "api_hdc_observations",
                   "geo_boundary_subdistrict", "geo_boundary_district", "geo_boundary_polygon",
                   "geo_hospital_facility", "geo_travel_matrix", "tambon_xwalk",
                   "dopa_population_year", "dopa_population_supplement",
                   "bma_migrant_general", "bma_migrant_mou_import", "bma_migrant_renewal", "bma_migrant_illegal"],
        "silver": ["api_nso_income", "api_bma_community", "api_diw_factory",
                   "api_dds_disease_ranking", "api_hdc_observations",
                   "geo_boundary_subdistrict", "geo_boundary_district",
                   "geo_hospital_facility", "geo_travel_matrix", "dopa_population_by_unit_year",
                   "bma_migrant_worker_permit"],
        "gold": ["dim_date", "dim_geography", "dim_industry", "dim_hdc_report", "dim_disease",
                 "dim_area", "dim_tambon_unit_xwalk", "dim_facility", "dim_industry_division", "dim_bma_zone",
                 "fact_income", "fact_factory", "fact_community_population",
                 "fact_disease_ranking", "fact_hdc_observation", "fact_hdc_weekly_observation",
                 "fact_hospital_access", "fact_population_by_area",
                 "bridge_bma_zone_district", "fact_migrant_worker_permit",
                 "agg_economic_by_province_year", "agg_population_by_district_year",
                 "agg_health_kpi_by_province_year", "obt_regional_composite_index",
                 "agg_industrial_concentration_by_unit_division", "agg_industrial_concentration_by_unit"],
    }

    body = ['<nav class="toc"><strong>Jump to:</strong> '
            '<a href="#bronze">Bronze</a><a href="#silver">Silver</a><a href="#gold">Gold</a></nav>']

    for schema in ("bronze", "silver", "gold"):
        body.append(f'<h2 class="section {schema}" id="{schema}">{schema.capitalize()} Layer</h2>')
        for table in table_order[schema]:
            cols = tables.get((schema, table), [])
            n = counts.get((schema, table))
            desc = TABLE_DESC.get((schema, table), "")
            pending_reason = "DDS pending" if "DDS" in desc else "Overpass blocked" if "Overpass" in desc else None
            pending = n == 0 and pending_reason is not None
            badge = f'<span class="badge pending">0 rows — {pending_reason}</span>' if pending else f'<span class="rowcount">{n:,} rows</span>' if n is not None else ""
            body.append(f'<h3 class="table-title">{schema}.{table} {badge}</h3>')
            body.append(f'<p class="table-desc">{desc}</p>')
            body.append('<table class="cols"><tr><th>Column</th><th>Type</th><th>Nullable</th><th>Description</th></tr>')
            for col, coltype, nullable, comment in cols:
                cd = _col_desc(schema, table, col, comment)
                body.append(f'<tr><td><code>{col}</code></td><td>{coltype}</td>'
                            f'<td>{"yes" if nullable == "YES" else "no"}</td><td>{cd}</td></tr>')
            body.append('</table>')

    html = _page(
        "clinical-dwh — Data Dictionary", "Data Dictionary",
        "Every Bronze, Silver, and Gold table and column in the live-API warehouse (NSO, BMA, DIW, DDS, HDC). "
        "Generated directly from information_schema + the pipeline's own build-time descriptions.",
        "\n".join(body),
    )
    with open(os.path.join(DOCS_DIR, "02_data_dictionary.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote docs/02_data_dictionary.html")


def build_architecture():
    body = f"""
<nav class="toc"><strong>Jump to:</strong> <a href="#flow">Data Flow</a><a href="#services">Services</a><a href="#sources">Sources</a><a href="#status">Known Issues</a></nav>

<h2 class="section gold" id="flow">Data Flow</h2>
<p>Live Thai government APIs + 2 public geo/routing services, no flat files, no manual exports. Raw API
responses land in a versioned, content-hashed S3-compatible store before Bronze shreds them into tables.</p>
<div class="flow">
  <div class="box">API<br><small>NSO / BMA / DIW / DDS / HDC / geo-boundary / OSM / OSRM</small></div>
  <div class="arrow">&rarr;</div>
  <div class="box">Landing Zone<br><small>SeaweedFS, versioned, content-hashed</small></div>
  <div class="arrow">&rarr;</div>
  <div class="box bronze">Bronze<br><small>1:1 shred, no transformation</small></div>
  <div class="arrow">&rarr;</div>
  <div class="box silver">Silver<br><small>typed, cleansed, BE&rarr;CE years</small></div>
  <div class="arrow">&rarr;</div>
  <div class="box gold">Gold<br><small>dims, facts, aggregates, composite index</small></div>
  <div class="arrow">&rarr;</div>
  <div class="box">Metabase<br><small>SELECT-only on gold.*</small></div>
</div>
<div class="callout">Each live source is wrapped in <code>run_pipeline.run_live_source()</code>, which logs a
failure and continues rather than aborting the whole run — confirmed necessary in practice (DDS's and Overpass's
outages would otherwise block Silver/Gold on every pipeline run). One exception to the usual
Bronze-all&rarr;Silver-all&rarr;Gold-all ordering: OSRM's ingest needs <code>gold.dim_area</code>'s unit
centroids as its source points, so it runs between Gold dimensions and Gold facts, not alongside the other live
sources.</div>

<h2 class="section gold" id="services">Services (docker-compose.yml)</h2>
<div class="svcgrid">
  <div class="svc"><h4>warehouse-db</h4><p>MySQL 8.0, hosts bronze/silver/gold schemas. <code>dwh_elt</code> (full DML/DDL)
  and <code>metabase_ro</code> (SELECT on gold.* only) accounts.</p></div>
  <div class="svc"><h4>elt-runner</h4><p>One-shot Python batch job, runs the full Bronze&rarr;Silver&rarr;Gold pipeline,
  then exits. Re-run any time with <code>docker compose run --rm elt-runner</code>.</p></div>
  <div class="svc"><h4>landing-zone</h4><p>SeaweedFS, S3-compatible. MinIO was the original choice but its free
  container distribution was discontinued across every registry as of this build (confirmed by direct testing).</p></div>
  <div class="svc"><h4>metabase</h4><p>BI tool, connects only to warehouse-db.gold via the read-only account.
  Dashboards are built manually via the Metabase UI, not by the pipeline.</p></div>
</div>

<h2 class="section gold" id="sources">The Sources</h2>
<table class="cols">
<tr><th>Source</th><th>What it is</th><th>Ingest script</th><th>Status</th></tr>
<tr><td>NSO</td><td>Household income by province, socio-economic class</td><td><code>ingest_api_nso.py</code></td><td><span class="badge ok">verified</span></td></tr>
<tr><td>BMA</td><td>Bangkok community registry, one CSV resource per fiscal year</td><td><code>ingest_api_bma.py</code></td><td><span class="badge ok">verified</span></td></tr>
<tr><td>DIW</td><td>Factory registry, 3 provinces, amphoe-by-amphoe crawl</td><td><code>ingest_api_diw.py</code></td><td><span class="badge ok">verified</span></td></tr>
<tr><td>DDS</td><td>Notifiable-disease ranking, CSRF-token-gated PDF report</td><td><code>ingest_api_dds.py</code></td><td><span class="badge pending">blocked — DDS backend down</span></td></tr>
<tr><td>HDC</td><td>Health-status reports, 4 subcatalogs (incl. 4 PM2.5-linked weekly reports), ~1,100 throttled requests for a full crawl</td><td><code>ingest_api_hdc.py</code></td><td><span class="badge ok">verified</span></td></tr>
<tr><td>Geo boundary</td><td>Thailand admin-boundary reference (dim_area input): subdistrict/district CSV + ADM3 polygon GeoJSON</td><td><code>ingest_api_geo_boundary.py</code></td><td><span class="badge ok">verified</span></td></tr>
<tr><td>OSM</td><td>Hospital/healthcare facilities near KMCH (Overpass API)</td><td><code>ingest_api_osm.py</code></td><td><span class="badge pending">blocked — Overpass 406</span></td></tr>
<tr><td>OSRM</td><td>Unit-to-facility travel-time/distance matrix (public demo server)</td><td><code>ingest_api_osrm.py</code></td><td><span class="badge ok">verified</span></td></tr>
<tr><td>Tambon↔unit crosswalk</td><td>File-based. kmch-ml's authoritative mapping of original tambon codes to dim_area's merged units</td><td><code>ingest_file_tambon_xwalk.py</code></td><td><span class="badge ok">verified</span></td></tr>
<tr><td>DOPA population</td><td>File-based. Population by area/year, fine+coarse age-sex bands (+ a 5-year backfill for 2 provinces)</td><td><code>ingest_file_dopa_population.py</code></td><td><span class="badge ok">verified</span></td></tr>
<tr><td>BMA migrant worker</td><td>File-based. 2568 BE snapshot, permits by BMA's own 10-zone grouping</td><td><code>ingest_file_bma_migrant_worker.py</code></td><td><span class="badge ok">verified</span></td></tr>
</table>
<p class="table-desc">8 live-API sources (6 reachable, 2 blocked at the source -- see Troubleshooting in the
runbook) + 3 file-based sources (deliberate, scoped exceptions for data with no API -- see
<a href="03_external_reference_sources.md">03_external_reference_sources.md</a> for why each one is file-based,
not a reversion to this project's earlier, larger file-based architecture).</p>

<h2 class="section gold" id="status">Known Issues</h2>
<div class="callout warn"><strong>DDS backend down since 2026-10-25.</strong> Every request returns a server-side
error: <code>"could not find driver (Connection: pgsql...)"</code> — a missing/misconfigured PostgreSQL PHP driver
on DDS's own server, confirmed by repeated direct testing, unrelated to this code. Re-run
<code>ingest_api_dds.run()</code> once it recovers; the landing zone exists specifically because DDS "keeps no
archive: a finished year it stops serving cannot be fetched again."</div>
<div class="callout warn"><strong>Overpass (OSM) blocked since 2026-10-26.</strong> The public
<code>overpass-api.de</code> instance (incl. its <code>lz4</code> mirror) returns HTTP 406 on every request,
confirmed from both the <code>elt-runner</code> container and the host machine directly — a block on this
network origin, unrelated to this code. <code>ingest_api_osrm.py</code> does not depend on this succeeding: it
always computes the travel matrix from every <code>dim_area</code> unit to the fixed KMCH coordinate.</div>
<div class="callout"><strong>PII exclusion, DIW.</strong> The source sheet carries <code>operator_name</code>
(factory owner's personal name) and <code>phone</code>. Both are read off the sheet (to keep column positions
aligned) and dropped before any row is built, logged, or inserted — they never reach Bronze, Silver, Gold, or
any output.</div>
<div class="callout"><strong>fact_hdc_observation.geo_key is often NULL.</strong> Only ~40% of pivoted HDC
records resolve to a geography — this is correct: reports using the <code>disease_ranking</code> or
<code>unsupported</code> layout (see Silver EAV notes) don't carry a resolvable area name per record.</div>
"""
    html = _page(
        "clinical-dwh — Architecture", "System Architecture",
        "Live-API-only Medallion (Bronze/Silver/Gold) ELT pipeline. No flat files, no clinic/patient source system.",
        body,
    )
    with open(os.path.join(DOCS_DIR, "01_architecture.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote docs/01_architecture.html")


def build_gold_kpi_guide():
    levels = [
        (3, "#2E75B6", "Level 3 — Strategic (Apex)", ["K-STR-01 Regional Socioeconomic-Health Vulnerability Index",
         "K-STR-02 Industrial-Health Impact Index", "K-STR-03 Catchment Economic Vitality Score"]),
        (2, "#5B9BD5", "Level 2 — Tactical / Diagnostic", ["K-ECO-08/09/10", "K-DEM-06", "K-HLT-07/08/09"]),
        (1, "#9DC3E6", "Level 1 — Operational", ["K-ECO-01..07", "K-DEM-01..05", "K-HLT-01..06"]),
        (0, "#D9D9D9", "Level 0 — Base Measures (raw Silver facts)", ["B-ECO-01..05", "B-DEM-01..02", "B-HLT-01..03"]),
    ]
    pyramid_html = ['<div class="pyramid">']
    for lvl, color, label, kpis in levels:
        width = 100 - lvl * 18
        pyramid_html.append(
            f'<div class="level" style="background:{color};color:{"#1a1a2e" if lvl<3 else "#fff"};width:{width}%;">'
            f'<strong>{label}</strong><br><small>{", ".join(kpis)}</small></div>'
        )
    pyramid_html.append('</div>')

    body = f"""
<nav class="toc"><strong>Jump to:</strong> <a href="#pyramid">KPI Pyramid</a><a href="#dashboards">Dashboards</a><a href="#gold">Gold Tables</a><a href="#metabase">Metabase</a></nav>

<p>Full detail (every KPI's exact formula, source column, and grain) lives in
<code>Excel\\KPI_Tree_and_Dashboard_Design.xlsx</code> (tabs <code>KPI_Tree</code> / <code>Dashboard_Design</code>).
This page is the web-readable summary.</p>

<h2 class="section gold" id="pyramid">KPI Pyramid (Bottom-Up)</h2>
{"".join(pyramid_html)}
<p style="text-align:center;color:var(--muted);font-size:.88rem;">38 KPI nodes total. Base measures roll up into
operational KPIs, which combine into tactical/diagnostic KPIs, which combine into the 3 strategic composite
indices at the apex.</p>

<h2 class="section gold" id="dashboards">4 Dashboards (built manually in Metabase)</h2>
<table class="cols">
<tr><th>Dashboard</th><th>Audience</th><th>Feeds From</th></tr>
<tr><td><strong>1. Executive Overview</strong></td><td>Leadership / cross-department</td><td><code>gold.obt_regional_composite_index</code> + all 3 agg_ tables</td></tr>
<tr><td><strong>2. Economic &amp; Industrial Development</strong></td><td>Economic planners / DIW liaison</td><td><code>gold.agg_economic_by_province_year</code>, <code>fact_income</code>, <code>fact_factory</code></td></tr>
<tr><td><strong>3. Population &amp; Community</strong></td><td>Social services / BMA liaison</td><td><code>gold.agg_population_by_district_year</code>, <code>fact_community_population</code></td></tr>
<tr><td><strong>4. Public Health Surveillance</strong></td><td>Health dept / HDC &amp; DDS program officers</td><td><code>gold.agg_health_kpi_by_province_year</code>, <code>fact_disease_ranking</code>, <code>fact_hdc_observation</code></td></tr>
</table>

<h2 class="section gold" id="gold">Gold Table Reference</h2>
<p>Full column-level detail is in <a href="02_data_dictionary.html">02_data_dictionary.html</a>. Quick map
(14 original dashboard-feeding tables, plus 12 added 2026-10-26/27 toward kmch-ml input parity):</p>
<div class="two-col">
<div><h4>Dimensions</h4><ul>
<li><code>dim_date</code>, <code>dim_geography</code>, <code>dim_industry</code>, <code>dim_hdc_report</code>, <code>dim_disease</code></li>
<li><code>dim_area</code> (catchment units, kmch-ml parity), <code>dim_tambon_unit_xwalk</code> (tambon crosswalk, kmch-ml parity), <code>dim_facility</code> (hospitals, kmch-ml parity), <code>dim_industry_division</code> (TSIC division names, kmch-ml parity), <code>dim_bma_zone</code> (BMA's 10 zones, kmch-ml parity)</li>
</ul><h4>Facts</h4><ul>
<li><code>fact_income</code>, <code>fact_factory</code> (+<code>area_key</code>, kmch-ml parity), <code>fact_community_population</code></li>
<li><code>fact_disease_ranking</code> (0 rows, DDS pending)</li>
<li><code>fact_hdc_observation</code> (pivoted from Silver's EAV shape)</li>
<li><code>fact_hdc_weekly_observation</code> (PM2.5 weekly, kmch-ml parity)</li>
<li><code>fact_hospital_access</code> (OSM/OSRM travel matrix, kmch-ml parity)</li>
<li><code>fact_population_by_area</code> (DOPA population by unit/year, kmch-ml parity)</li>
<li><code>bridge_bma_zone_district</code>, <code>fact_migrant_worker_permit</code> (BMA zones, kmch-ml parity)</li>
</ul></div>
<div><h4>Aggregates / Composite</h4><ul>
<li><code>agg_economic_by_province_year</code></li>
<li><code>agg_population_by_district_year</code></li>
<li><code>agg_health_kpi_by_province_year</code></li>
<li><code>obt_regional_composite_index</code> (K-STR-01/02/03)</li>
<li><code>agg_industrial_concentration_by_unit_division</code>, <code>agg_industrial_concentration_by_unit</code> (location quotient, kmch-ml parity)</li>
</ul><p style="font-size:.85rem;color:var(--muted)">The 12 kmch-ml-parity additions aren't wired into any of
these aggregates or the 4 dashboards -- additive ingestion only, not a KPI/dashboard change.</p></div>
</div>

<h2 class="section gold" id="metabase">Metabase Connection</h2>
<div class="callout ok">Fresh Metabase instance (old one dropped entirely 2026-10-26). Connects to
<code>warehouse-db.gold</code> via the read-only <code>metabase_ro</code> account — same least-privilege
enforcement as before, bronze/silver are not reachable from Metabase. The original 14 Gold tables are confirmed
synced and unchanged by the 2026-10-26 kmch-ml-parity extension (verified against information_schema before/after).
Dashboards are being built manually via the Metabase UI, not generated by the pipeline.</div>
"""
    html = _page(
        "clinical-dwh — Gold Layer &amp; KPI Guide", "Gold Layer &amp; KPI Guide",
        "Bottom-up KPI pyramid, the 4 dashboards built from it, and the Gold tables that feed them.",
        body,
    )
    with open(os.path.join(DOCS_DIR, "04_gold_layer_and_kpi_guide.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote docs/04_gold_layer_and_kpi_guide.html")


def build_runbook():
    body = """
<nav class="toc"><strong>Jump to:</strong> <a href="#prereq">Prerequisites</a><a href="#firstrun">First Deploy</a>
<a href="#verify">Verify</a><a href="#metabase">Metabase Bootstrap</a><a href="#production">Production (VM)</a>
<a href="#day2">Day-2 Ops</a><a href="#troubleshooting">Troubleshooting</a><a href="#reset">Reset</a></nav>

<h2 class="section gold" id="prereq">Prerequisites</h2>
<ul>
<li>Docker Engine with Compose v2 (Docker Desktop for local dev; plain <code>docker</code> + the
<code>docker-compose-plugin</code> package for a Linux VM -- see <a href="#production">Production (VM)</a>)</li>
<li>Outbound internet access to 6 live hosts (NSO, BMA, DIW, HDC, GitHub for the admin-boundary reference data,
<code>router.project-osrm.org</code>) plus 2 that are currently blocked at the source, not this code (DDS,
Overpass/OSM -- see Troubleshooting) — this pipeline has no offline mode</li>
<li>A local copy of the 4 file-based inputs under <code>external-inputs/</code> (tambon crosswalk, DOPA
population x2, BMA migrant worker permits) -- these are bind-mounted, not baked into the image, so updating any
of them later needs no rebuild</li>
<li>Python 3 with <code>pymysql</code> on the host only if regenerating these docs directly (dumps
<code>information_schema</code> to <code>%TEMP%</code>, see Day-2 Ops), or <code>openpyxl</code> if
regenerating <code>Excel\\KPI_Tree_and_Dashboard_Design.xlsx</code></li>
</ul>

<h2 class="section gold" id="firstrun">First-Time Deploy</h2>
<ol class="steps">
<li><h4>Clone and configure environment</h4>
<pre><code>Copy-Item .env.example .env
Copy-Item seaweedfs_s3_config.json.example seaweedfs_s3_config.json
# Edit BOTH files: change every ChangeMe_* password.
# The access/secret key pair must match between the two files --
# .env is read by elt-runner; seaweedfs_s3_config.json is read
# directly by the SeaweedFS binary, not env-templated.</code></pre></li>

<li><h4>Bring up infrastructure</h4>
<pre><code>docker compose up -d warehouse-db landing-zone metabase
docker compose ps   # wait for warehouse-db and landing-zone to show "healthy"</code></pre>
<p class="table-desc">warehouse-db's healthcheck is <code>mysqladmin ping</code>; landing-zone's accepts any HTTP
response (even 403) as healthy -- confirms the SeaweedFS S3 gateway is reachable, not that credentials are
correct yet.</p></li>

<li><h4>Build and run the pipeline</h4>
<pre><code>docker compose build elt-runner
docker compose run --rm elt-runner</code></pre>
<p class="table-desc">One-shot batch job, full Bronze -&gt; Silver -&gt; Gold refresh every time (idempotent). Ingests
all 8 live-API sources (DIW's amphoe crawl takes ~70s; HDC's full 119-report crawl is the long pole, typically
10-20 min at its throttled rate -- watch for <code>[ingest_api_hdc] (N/119)...</code> advancing, this is normal,
not a hang) and the 3 file-based sources. A source that's down (DDS, OSM -- both confirmed blocked at the
source, not this code, see Troubleshooting) logs a warning and the run continues -- it will NOT abort the whole
deploy.</p></li>
</ol>

<h2 class="section gold" id="verify">Verify the Deploy</h2>
<p>The pipeline prints a row-count summary on success. Expected figures (2026-10-27 baseline; BMA/HDC will grow
as those sources publish new fiscal years/reports):</p>
<table class="cols checklist">
<tr><th></th><th>Table</th><th>Expected rows</th></tr>
<tr><td>&check;</td><td><code>bronze.api_nso_income</code></td><td>15,400</td></tr>
<tr><td>&check;</td><td><code>bronze.api_bma_community</code></td><td>6,027</td></tr>
<tr><td>&check;</td><td><code>bronze.api_diw_factory</code></td><td>13,683</td></tr>
<tr><td>&#9888;</td><td><code>bronze.api_dds_disease_ranking</code></td><td>0 -- expected while DDS's backend is down (see Troubleshooting)</td></tr>
<tr><td>&check;</td><td><code>bronze.api_hdc_observations</code></td><td>163,233</td></tr>
<tr><td>&#9888;</td><td><code>bronze.geo_hospital_facility</code></td><td>0 -- expected while Overpass/OSM is blocked (see Troubleshooting)</td></tr>
<tr><td>&check;</td><td><code>gold.dim_geography</code></td><td>451 (77 provinces + 67 districts + 307 subdistricts)</td></tr>
<tr><td>&check;</td><td><code>gold.dim_area</code></td><td>312 catchment units (exact match to kmch-ml's own documented total)</td></tr>
<tr><td>&check;</td><td><code>gold.fact_factory</code></td><td>13,683 (~97% with <code>area_key</code> resolved)</td></tr>
<tr><td>&check;</td><td><code>gold.fact_population_by_area</code></td><td>2,808</td></tr>
<tr><td>&check;</td><td><code>gold.fact_migrant_worker_permit</code></td><td>180</td></tr>
<tr><td>&check;</td><td><code>gold.obt_regional_composite_index</code></td><td>154 (province x year combinations)</td></tr>
</table>
<p>Spot-check manually if any number looks off:</p>
<pre><code>docker compose exec warehouse-db mysql --default-character-set=utf8mb4 -u root -p `
  -e "SELECT COUNT(*) FROM gold.fact_hdc_observation;"</code></pre>
<div class="callout warn">Always pass <code>--default-character-set=utf8mb4</code> explicitly on any manual
mysql client invocation. Confirmed by direct testing: the MySQL server image's own bundled client defaults to
latin1 and silently corrupts Thai string comparisons with no error raised.</div>

<h2 class="section gold" id="metabase">Metabase Bootstrap</h2>
<p>A brand-new Metabase container has no admin account and no database connections -- first boot shows a setup
wizard. Two ways to complete it:</p>
<div class="two-col">
<div><h4>Option A -- UI wizard</h4><p class="table-desc">Open http://localhost:3000, follow the prompts: create
the admin account, then add a database connection (MySQL, host <code>warehouse-db</code>, port 3306, database
<code>gold</code>, user <code>metabase_ro</code>, password = <code>DWH_METABASE_RO_PASSWORD</code> from
<code>.env</code>).</p></div>
<div><h4>Option B -- API (scriptable, used for this deploy)</h4><p class="table-desc">Get the setup token, then
POST the admin user. <strong>The embedded <code>database</code> object in <code>/api/setup</code> was unreliable
on v0.50.19 in practice</strong> -- it silently succeeded without creating a connection. Add the database as a
separate explicit call instead:</p></div>
</div>
<pre><code>$token = (Invoke-RestMethod http://localhost:3000/api/session/properties).'setup-token'
Invoke-RestMethod -Method Post http://localhost:3000/api/setup -ContentType 'application/json' -Body (@{
  token = $token
  user = @{ first_name='Admin'; last_name='User'; email='you@example.com'; password='...'; site_name='clinical-dwh' }
  prefs = @{ site_name='clinical-dwh'; site_locale='en'; allow_tracking=$false }
} | ConvertTo-Json -Depth 5)

# Then log in and add the real database connection explicitly:
$session = (Invoke-RestMethod -Method Post http://localhost:3000/api/session -ContentType 'application/json' `
  -Body (@{ username='you@example.com'; password='...' } | ConvertTo-Json)).id
Invoke-RestMethod -Method Post http://localhost:3000/api/database -Headers @{'X-Metabase-Session'=$session} `
  -ContentType 'application/json' -Body (@{
    engine = 'mysql'; name = 'gold'
    details = @{ host='warehouse-db'; port=3306; dbname='gold'; user='metabase_ro'; password='...'; ssl=$false }
  } | ConvertTo-Json -Depth 5)</code></pre>
<p class="table-desc">Verify sync completed: <code>GET /api/database/{id}?include=tables</code>, check every
table shows <code>"initial_sync_status":"complete"</code>.</p>
<div class="callout">A default "Sample Database" (Metabase's own H2 demo dataset, <code>id=1</code> on a fresh
instance) is added automatically during setup. Remove it for a clean workspace:
<code>DELETE /api/database/1</code> with the admin session header.</div>

<h2 class="section gold" id="production">Production Deployment (VM)</h2>
<p>Everything above works unchanged on a VM -- Docker Compose doesn't care whether it's running on a laptop or a
server. The differences below are what actually matters once the warehouse is reachable over a network instead
of just <code>localhost</code>, and left running unattended for weeks instead of a dev session.</p>

<h4>Sizing (baseline, not a hard minimum)</h4>
<ul>
<li><strong>2 vCPU / 4GB RAM</strong> comfortably runs the 3 persistent services (MySQL, SeaweedFS, Metabase)
idle; the <code>elt-runner</code> batch job is CPU-light (mostly waiting on throttled HTTP requests) so it
doesn't need dedicated headroom, just enough to not starve the other 3 while it runs.</li>
<li><strong>20GB disk</strong> minimum. Current data footprint is small (38+ Bronze/Silver/Gold tables, largest
at ~163K rows) -- the landing zone is the one that grows over time, though content-addressed dedup means a
source that returns unchanged bytes on every re-run (the common case) adds nothing. Budget more if re-running
frequently against sources that change often (HDC's own data updates faster than the others).</li>
</ul>

<h4>OS and Docker install</h4>
<p class="table-desc">Docker Desktop is a dev-machine product -- a VM runs plain Docker Engine + the Compose v2
plugin instead (Ubuntu Server LTS is a reasonable default target):</p>
<pre><code># Ubuntu/Debian -- see docs.docker.com for other distros
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER   # log out/in once for this to take effect
docker compose version          # confirms the v2 plugin, not the old standalone docker-compose</code></pre>

<h4>Docker log limits -- already configured, verify it took effect</h4>
<p class="table-desc">Every service in <code>docker-compose.yml</code> caps its own json-file log via a shared
<code>x-logging</code> anchor (<code>max-size: 3m</code>, <code>max-file: 2</code> -- 6MB worst case per
service). Docker's own default has <strong>no cap at all</strong>, so this matters most on a VM where disk is
finite and nobody's watching interactively. Confirm it's actually applied after bringing services up:</p>
<pre><code>docker inspect cdw-warehouse-db --format '{{json .HostConfig.LogConfig}}'
# expect: {"Type":"json-file","Config":{"max-file":"2","max-size":"3m"}}</code></pre>
<div class="callout warn">This caps <em>container</em> logs only. It does not cap the 3 data volumes
(<code>warehouse_db_data</code>, <code>metabase_data</code>, <code>landing_zone_data</code>) -- those grow with
real data, by design, and are what Day-2 backups below protect.</div>

<h4>Persist across reboots</h4>
<p class="table-desc"><code>warehouse-db</code>, <code>landing-zone</code>, and <code>metabase</code> already
have <code>restart: unless-stopped</code> -- Docker itself restarts them after a host reboot, as long as the
Docker daemon is enabled to start on boot (<code>get.docker.com</code>'s installer does this automatically;
confirm with <code>systemctl is-enabled docker</code>). <code>elt-runner</code> intentionally has no restart
policy -- it's a one-shot batch job, not a daemon; scheduling re-runs is a cron concern, below.</p>

<h4>Schedule periodic pipeline runs</h4>
<p class="table-desc">There's no built-in scheduler -- a VM deployment that wants fresh data without someone
running the command by hand needs a cron entry:</p>
<pre><code># /etc/cron.d/clinical-dwh-pipeline -- daily at 02:00 local time
0 2 * * * root cd /opt/clinical-dwh && docker compose run --rm elt-runner >> /var/log/clinical-dwh-pipeline.log 2>&1</code></pre>
<div class="callout warn">Redirecting cron's own output to a plain log file sidesteps the container log cap above
-- rotate that file too (<code>logrotate</code>, or just redirect to <code>docker compose run --rm elt-runner
2>&amp;1 | tail -n 1000 > /var/log/clinical-dwh-pipeline.log</code> to keep only the latest run).</div>

<h4>Network exposure</h4>
<p class="table-desc">By default every port in <code>docker-compose.yml</code> binds to all interfaces
(<code>0.0.0.0</code>) -- fine on a laptop behind a home router, not fine on a VM with a public IP.</p>
<ul>
<li><strong>Metabase (3000)</strong> is the only service end users need. If exposing it beyond the VM's own
internal network, put a reverse proxy in front for TLS (Caddy or nginx with Let's Encrypt) rather than exposing
Metabase's own HTTP port directly -- it has no TLS of its own.</li>
<li><strong>warehouse-db (3306) and landing-zone (8333/8888) should not be internet-facing.</strong> Change
their host-port bindings in <code>docker-compose.yml</code> from <code>"${PORT}:3306"</code> to
<code>"127.0.0.1:${PORT}:3306"</code> (same pattern for the other two) so they're reachable from the VM itself
and anything in the same Docker network, but not from outside -- nothing external needs direct DB or landing-zone
access; Metabase already reaches warehouse-db over the internal <code>cdw-net</code> bridge network regardless.</li>
<li>If a cloud firewall/security-group is available at the VM level, use it as the primary control -- only open
22 (SSH) and whichever port fronts Metabase (443 if behind a reverse proxy, 3000 if not).</li>
</ul>

<h4>Secrets</h4>
<ul>
<li><strong>Change every <code>ChangeMe_*</code> password in <code>.env</code> and
<code>seaweedfs_s3_config.json</code> before this VM is reachable by anyone else</strong> -- the defaults in
this repo are placeholders, not production credentials.</li>
<li><code>chmod 600 .env seaweedfs_s3_config.json</code> -- both contain plaintext credentials; restrict to the
deploying user.</li>
<li>Neither file belongs in version control -- confirm both are gitignored before pushing this VM's working
copy anywhere.</li>
</ul>

<h4>Backups</h4>
<p class="table-desc">The 3 named volumes are the entire state of the warehouse. A logical MySQL dump is more
portable and consistent than a raw volume copy for the database specifically:</p>
<pre><code># Database -- logical dump, safe to take while the DB is running
docker compose exec warehouse-db mysqldump --default-character-set=utf8mb4 -u root -p --all-databases \\
  > backup_$(date +%Y%m%d).sql

# Metabase + landing zone -- raw volume archives (stop the service first for a consistent snapshot,
# or accept a small risk of an in-flight write on a running one)
docker run --rm -v clinical-dwh_metabase_data:/data -v $(pwd):/backup alpine \\
  tar czf /backup/metabase_$(date +%Y%m%d).tar.gz -C /data .
docker run --rm -v clinical-dwh_landing_zone_data:/data -v $(pwd):/backup alpine \\
  tar czf /backup/landingzone_$(date +%Y%m%d).tar.gz -C /data .</code></pre>
<div class="callout">The landing zone is re-derivable by re-running the pipeline against live sources (except
DDS/OSM while those remain blocked, and the 4 file-based inputs, which only exist wherever
<code>external-inputs/</code> is kept outside the container) -- lower backup priority than the database itself,
whose Gold layer took real compute (HDC's throttled crawl, OSRM's tiled routing) to rebuild from scratch.</div>

<h4>Disk monitoring</h4>
<pre><code>docker system df            # image/container/volume disk usage at a glance
df -h /var/lib/docker        # or wherever Docker's data-root actually lives on this VM</code></pre>
<div class="callout warn"><code>docker system prune</code> removes stopped containers, unused networks, and
dangling images -- safe in general, but never run <code>-a</code> or <code>--volumes</code> without reading what
it would remove first; <code>--volumes</code> can delete the named volumes this warehouse's entire state lives
in if they're not currently attached to a running container.</div>

<h2 class="section gold" id="day2">Day-2 Operations</h2>
<ul>
<li><strong>Re-run the pipeline</strong> any time: <code>docker compose run --rm elt-runner</code>. Idempotent --
the landing zone skips re-storing identical bytes, each layer's DDL drops/recreates its own tables.</li>
<li><strong>Re-run just one source</strong> (faster than a full run while iterating):
<pre><code>docker compose run --rm elt-runner python -c "import ingest_api_nso, extract_load_api_nso; ingest_api_nso.run(); extract_load_api_nso.run()"</code></pre></li>
<li><strong>Regenerate these docs</strong> after any schema change -- dump the schema, then run the generator:
<pre><code>docker compose exec warehouse-db mysql --default-character-set=utf8mb4 -u root -p `
  -N -e "SELECT table_schema,table_name,column_name,column_type,is_nullable,column_comment,ordinal_position FROM information_schema.columns WHERE table_schema IN ('bronze','silver','gold') ORDER BY 1,2,7;" `
  > "$env:TEMP\\schema_dump.tsv"
python docs\\build_html_docs.py</code></pre></li>
<li><strong>Browse the landing zone</strong> at <a href="http://localhost:8888/buckets/landing-zone/">http://localhost:8888/buckets/landing-zone/</a>
-- SeaweedFS's own Filer web UI (folders by source, file download/preview, upload/new-folder). Already running
inside the <code>landing-zone</code> container via the <code>server</code> command; exposed to the host via
<code>LANDING_FILER_UI_HOST_PORT</code> (default 8888) in <code>docker-compose.yml</code>. No separate client
needed -- this is the "DBeaver for the landing zone."</li>
<li><strong>Rebuild the elt-runner image</strong> after any Python/requirements change:
<code>docker compose build elt-runner</code></li>
</ul>

<h2 class="section gold" id="troubleshooting">Troubleshooting</h2>
<div class="callout warn"><strong>DDS returns 500 on every request.</strong> Check for
<code>"could not find driver (Connection: pgsql...)"</code> in the response body -- that's DDS's own backend
missing its PostgreSQL PHP driver, not fixable from this side. Nothing to do but wait and re-run
<code>ingest_api_dds.run()</code> periodically.</div>
<div class="callout warn"><strong>NSO requests return an HTTP 418 block page.</strong> The WAF in front of
NSO's API blocks the default requests/curl User-Agent. Confirm <code>ingest_api_nso.py</code> still sends
<code>User-Agent: Mozilla/5.0 kmch-phase3-nso/1.0</code> -- if NSO changes their WAF rules, the fix is a
different UA string, not a code redesign.</div>
<div class="callout warn"><strong>OSM facility discovery returns HTTP 406 from every Overpass endpoint.</strong>
Confirmed by direct testing (both from inside the container and from the host machine directly) that Overpass's
public instance (<code>overpass-api.de</code>, including its <code>lz4</code> mirror) is blocking this network
origin -- unrelated to this code. <code>ingest_api_osrm.py</code> does not depend on this succeeding (it always
computes the travel matrix to the fixed KMCH coordinate regardless), so this only affects
<code>dim_facility</code> staying at 1 row (KMCH itself). Retry periodically; worth trying a different Overpass
mirror if this persists.</div>
<div class="callout"><strong>landing-zone container is "unhealthy".</strong> Its healthcheck accepts any HTTP
response as healthy (even 403) -- a real failure means the container can't be reached at all. Check
<code>docker compose logs landing-zone</code>; a common cause is <code>seaweedfs_s3_config.json</code> missing
(copy it from the <code>.example</code> if you skipped that step).</div>
<div class="callout"><strong>A full pipeline run seems to hang for ~15-20 minutes.</strong> That's the HDC
crawl (119 reports x up to 5 years x 2 zones, throttled 0.6s between requests) -- not a hang. Watch the log for
<code>[ingest_api_hdc] (N/119)...</code> lines advancing.</div>

<h2 class="section gold" id="reset">Full Reset</h2>
<pre><code>docker compose down -v   # removes containers AND volumes -- landed objects, warehouse data, Metabase state all gone
docker compose up -d warehouse-db landing-zone metabase
docker compose run --rm elt-runner
# then redo the Metabase Bootstrap section above -- a fresh volume means a fresh setup wizard</code></pre>
<div class="callout warn">This deletes everything: every landed API response in SeaweedFS, every Bronze/Silver/Gold
row, and the entire Metabase instance (admin account, saved questions, dashboards). Only run this when you
genuinely want to start over.</div>
"""
    html = _page(
        "clinical-dwh — Runbook", "Deployment Runbook",
        "How to deploy this warehouse from zero: first-time setup, verification, Metabase bootstrap, "
        "day-2 operations, troubleshooting, and full reset.",
        body,
    )
    with open(os.path.join(DOCS_DIR, "05_runbook.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote docs/05_runbook.html")


if __name__ == "__main__":
    build_architecture()
    build_data_dictionary()
    build_gold_kpi_guide()
    build_runbook()

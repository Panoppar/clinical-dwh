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
                   "api_dds_disease_ranking", "api_hdc_report_catalog", "api_hdc_observations"],
        "silver": ["api_nso_income", "api_bma_community", "api_diw_factory",
                   "api_dds_disease_ranking", "api_hdc_observations"],
        "gold": ["dim_date", "dim_geography", "dim_industry", "dim_hdc_report", "dim_disease",
                 "fact_income", "fact_factory", "fact_community_population",
                 "fact_disease_ranking", "fact_hdc_observation",
                 "agg_economic_by_province_year", "agg_population_by_district_year",
                 "agg_health_kpi_by_province_year", "obt_regional_composite_index"],
    }

    body = ['<nav class="toc"><strong>Jump to:</strong> '
            '<a href="#bronze">Bronze</a><a href="#silver">Silver</a><a href="#gold">Gold</a></nav>']

    for schema in ("bronze", "silver", "gold"):
        body.append(f'<h2 class="section {schema}" id="{schema}">{schema.capitalize()} Layer</h2>')
        for table in table_order[schema]:
            cols = tables.get((schema, table), [])
            n = counts.get((schema, table))
            desc = TABLE_DESC.get((schema, table), "")
            pending = n == 0 and "DDS" in desc
            badge = '<span class="badge pending">0 rows — DDS pending</span>' if pending else f'<span class="rowcount">{n:,} rows</span>' if n is not None else ""
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
<p>Five live Thai government APIs, no flat files, no manual exports. Raw API responses land in a
versioned, content-hashed S3-compatible store before Bronze shreds them into tables.</p>
<div class="flow">
  <div class="box">API<br><small>NSO / BMA / DIW / DDS / HDC</small></div>
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
<div class="callout">Each of the 5 live-API sources is wrapped in <code>run_pipeline.run_live_source()</code>,
which logs a failure and continues rather than aborting the whole run — confirmed necessary in practice (DDS's
outage would otherwise block Silver/Gold on every pipeline run until DDS's own team fixes their server).</div>

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

<h2 class="section gold" id="sources">The 5 Sources</h2>
<table class="cols">
<tr><th>Source</th><th>What it is</th><th>Ingest script</th><th>Status</th></tr>
<tr><td>NSO</td><td>Household income by province, socio-economic class</td><td><code>ingest_api_nso.py</code></td><td><span class="badge ok">verified</span></td></tr>
<tr><td>BMA</td><td>Bangkok community registry, one CSV resource per fiscal year</td><td><code>ingest_api_bma.py</code></td><td><span class="badge ok">verified</span></td></tr>
<tr><td>DIW</td><td>Factory registry, 3 provinces, amphoe-by-amphoe crawl</td><td><code>ingest_api_diw.py</code></td><td><span class="badge ok">verified</span></td></tr>
<tr><td>DDS</td><td>Notifiable-disease ranking, CSRF-token-gated PDF report</td><td><code>ingest_api_dds.py</code></td><td><span class="badge pending">blocked — DDS backend down</span></td></tr>
<tr><td>HDC</td><td>Health-status reports, 4 subcatalogs, ~1,100 throttled requests for a full crawl</td><td><code>ingest_api_hdc.py</code></td><td><span class="badge ok">verified</span></td></tr>
</table>

<h2 class="section gold" id="status">Known Issues</h2>
<div class="callout warn"><strong>DDS backend down since 2026-10-25.</strong> Every request returns a server-side
error: <code>"could not find driver (Connection: pgsql...)"</code> — a missing/misconfigured PostgreSQL PHP driver
on DDS's own server, confirmed by repeated direct testing, unrelated to this code. Re-run
<code>ingest_api_dds.run()</code> once it recovers; the landing zone exists specifically because DDS "keeps no
archive: a finished year it stops serving cannot be fetched again."</div>
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
<p>Full column-level detail is in <a href="02_data_dictionary.html">02_data_dictionary.html</a>. Quick map:</p>
<div class="two-col">
<div><h4>Dimensions</h4><ul>
<li><code>dim_date</code>, <code>dim_geography</code>, <code>dim_industry</code>, <code>dim_hdc_report</code>, <code>dim_disease</code></li>
</ul><h4>Facts</h4><ul>
<li><code>fact_income</code>, <code>fact_factory</code>, <code>fact_community_population</code></li>
<li><code>fact_disease_ranking</code> (0 rows, DDS pending)</li>
<li><code>fact_hdc_observation</code> (pivoted from Silver's EAV shape)</li>
</ul></div>
<div><h4>Aggregates / Composite</h4><ul>
<li><code>agg_economic_by_province_year</code></li>
<li><code>agg_population_by_district_year</code></li>
<li><code>agg_health_kpi_by_province_year</code></li>
<li><code>obt_regional_composite_index</code> (K-STR-01/02/03)</li>
</ul></div>
</div>

<h2 class="section gold" id="metabase">Metabase Connection</h2>
<div class="callout ok">Fresh Metabase instance (old one dropped entirely 2026-10-26). Connects to
<code>warehouse-db.gold</code> via the read-only <code>metabase_ro</code> account — same least-privilege
enforcement as before, bronze/silver are not reachable from Metabase. All 14 Gold tables confirmed synced.
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
<a href="#verify">Verify</a><a href="#metabase">Metabase Bootstrap</a><a href="#day2">Day-2 Ops</a>
<a href="#troubleshooting">Troubleshooting</a><a href="#reset">Reset</a></nav>

<h2 class="section gold" id="prereq">Prerequisites</h2>
<ul>
<li>Docker Desktop with Compose v2</li>
<li>Outbound internet access to 5 government API hosts (NSO, BMA, DIW, DDS, HDC) and GitHub (if re-fetching
anything) — this pipeline has no offline mode</li>
<li>Python 3 with <code>openpyxl</code> only if regenerating <code>Excel\\KPI_Tree_and_Dashboard_Design.xlsx</code>
or these docs</li>
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
<p class="table-desc">One-shot batch job. Ingests all 5 sources (DIW's amphoe crawl takes ~70s; HDC's full
report crawl takes ~15-20 min at its 0.6s throttle -- this is the long pole of a first deploy), shreds to
Bronze, cleanses to Silver, builds Gold. A source that's down (see DDS, below) logs a warning and the run
continues -- it will NOT abort the whole deploy.</p></li>
</ol>

<h2 class="section gold" id="verify">Verify the Deploy</h2>
<p>The pipeline prints a row-count summary on success. Expected figures (2026-10-26 baseline; BMA/HDC will grow
as those sources publish new fiscal years/reports):</p>
<table class="cols checklist">
<tr><th></th><th>Table</th><th>Expected rows</th></tr>
<tr><td>&check;</td><td><code>bronze.api_nso_income</code></td><td>15,400</td></tr>
<tr><td>&check;</td><td><code>bronze.api_bma_community</code></td><td>6,027</td></tr>
<tr><td>&check;</td><td><code>bronze.api_diw_factory</code></td><td>13,683</td></tr>
<tr><td>&#9888;</td><td><code>bronze.api_dds_disease_ranking</code></td><td>0 -- expected while DDS's backend is down (see Troubleshooting)</td></tr>
<tr><td>&check;</td><td><code>bronze.api_hdc_observations</code></td><td>163,219</td></tr>
<tr><td>&check;</td><td><code>gold.dim_geography</code></td><td>451 (77 provinces + 67 districts + 307 subdistricts)</td></tr>
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

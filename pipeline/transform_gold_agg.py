"""Builds gold's 3 dashboard-feeding aggregate tables + the Level-3
composite index table, from the fact tables (must run after
transform_gold_facts.py). Column-to-KPI mapping matches the Dashboard
Design tab in KPI_Tree_and_Dashboard_Design.xlsx.

Composite indices (K-STR-01/02/03) use simple min-max normalization to a
0-100 scale with equal weighting across components -- a transparent,
easily-adjustable starting design, not a validated statistical model.
"""

import os

import pymysql


def _connect(database):
    return pymysql.connect(
        host=os.environ["DWH_DB_HOST"], port=int(os.environ["DWH_DB_PORT"]),
        user=os.environ["DWH_DB_USER"], password=os.environ["DWH_DB_PASSWORD"],
        database=database, charset="utf8mb4", cursorclass=pymysql.cursors.Cursor,
        connect_timeout=10,
    )


def _minmax_normalize(values: dict[str, float]) -> dict[str, float]:
    """-> {key: 0-100}. All-equal or empty input maps everything to 50.0 (neutral)."""
    present = {k: v for k, v in values.items() if v is not None}
    if not present:
        return {k: None for k in values}
    lo, hi = min(present.values()), max(present.values())
    if hi == lo:
        return {k: (50.0 if v is not None else None) for k, v in values.items()}
    return {k: (round(100 * (v - lo) / (hi - lo), 2) if v is not None else None) for k, v in values.items()}


def _build_agg_economic(gold_conn):
    # Factory metrics: province-grain, year-independent (DIW is a single current-state
    # crawl) -- resolve each fact_factory row's geo_key up to its province in Python
    # (dim_geography's province_name is already correct at every admin_level).
    with gold_conn.cursor() as cur:
        cur.execute("SELECT geo_key, admin_level, province_name, parent_geo_key FROM dim_geography")
        geo_rows = cur.fetchall()
    province_of = {}
    for geo_key, admin_level, province_name, parent_geo_key in geo_rows:
        province_of[geo_key] = province_name  # province_name is already correct at every level

    with gold_conn.cursor() as cur:
        cur.execute("SELECT geo_key, capital, workers FROM fact_factory")
        factory_rows = cur.fetchall()
    factory_by_province: dict[str, list] = {}
    for geo_key, capital, workers in factory_rows:
        p = province_of.get(geo_key)
        if p is None:
            continue
        factory_by_province.setdefault(p, []).append((capital, workers))

    factory_agg = {}
    for province, items in factory_by_province.items():
        capitals = [c for c, _ in items if c is not None]
        workers = [w for _, w in items if w is not None]
        factory_agg[province] = {
            "factory_count": len(items),
            "avg_capital": sum(capitals) / len(capitals) if capitals else None,
            "avg_workers": sum(workers) / len(workers) if workers else None,
            "total_workforce": sum(workers) if workers else None,
        }

    with gold_conn.cursor() as cur:
        cur.execute(
            "SELECT g.province_name, fi.date_key, fi.source_income1, fi.income_value "
            "FROM fact_income fi JOIN dim_geography g ON g.geo_key=fi.geo_key"
        )
        income_rows = cur.fetchall()
    income_agg: dict[tuple, dict] = {}
    for province, year, source1, value in income_rows:
        key = (province, year)
        bucket = income_agg.setdefault(key, {"total": [], "regular": []})
        if source1 == "รายได้ทั้งสิ้นต่อเดือน":
            bucket["total"].append(value)
        elif source1 == "รายได้ประจำ":
            bucket["regular"].append(value)

    rows = []
    for (province, year), bucket in income_agg.items():
        total_vals = [v for v in bucket["total"] if v is not None]
        regular_vals = [v for v in bucket["regular"] if v is not None]
        avg_income = sum(total_vals) / len(total_vals) if total_vals else None
        regular_share = (sum(regular_vals) / sum(total_vals)) if total_vals and sum(total_vals) else None
        fa = factory_agg.get(province, {})
        income_to_capital = (avg_income / fa["avg_capital"]) if avg_income and fa.get("avg_capital") else None
        rows.append((
            province, year, avg_income, regular_share, fa.get("factory_count"), fa.get("avg_capital"),
            fa.get("avg_workers"), fa.get("total_workforce"), income_to_capital,
        ))

    insert_sql = (
        "INSERT INTO agg_economic_by_province_year (province_name, year_ce, avg_monthly_income, "
        "regular_income_share, factory_count, avg_factory_capital, avg_workers_per_factory, "
        "total_industrial_workforce, income_to_capital_ratio) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    with gold_conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    gold_conn.commit()
    print(f"[gold_agg] agg_economic_by_province_year: {len(rows)} rows")
    return income_agg, factory_agg


def _build_agg_population(gold_conn):
    with gold_conn.cursor() as cur:
        cur.execute(
            "SELECT g.province_name, g.district_name, fcp.date_key, fcp.name_of_community, "
            "fcp.type_of_community, fcp.population, fcp.male, fcp.female "
            "FROM fact_community_population fcp JOIN dim_geography g ON g.geo_key=fcp.geo_key"
        )
        pop_rows = cur.fetchall()

    bucket: dict[tuple, dict] = {}
    for province, district, year, name, type_c, pop, male, female in pop_rows:
        key = (province, district, year)
        b = bucket.setdefault(key, {"pop": 0, "male": 0, "female": 0, "crowded_pop": 0, "communities": set()})
        b["pop"] += pop or 0
        b["male"] += male or 0
        b["female"] += female or 0
        if type_c == "ชุมชนแออัด":
            b["crowded_pop"] += pop or 0
        b["communities"].add(name)

    rows = []
    for (province, district, year), b in bucket.items():
        sex_ratio = (b["male"] / b["female"]) if b["female"] else None
        crowded_share = (b["crowded_pop"] / b["pop"]) if b["pop"] else None
        prior_key = (province, district, year - 1)
        yoy = None
        if prior_key in bucket and bucket[prior_key]["pop"]:
            yoy = (b["pop"] - bucket[prior_key]["pop"]) / bucket[prior_key]["pop"]
        rows.append((province, district, year, b["pop"], sex_ratio, len(b["communities"]), crowded_share, yoy))

    insert_sql = (
        "INSERT INTO agg_population_by_district_year (province_name, district_name, fiscal_year_ce, "
        "total_population, sex_ratio, community_count, crowded_population_share, yoy_growth_rate) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    with gold_conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    gold_conn.commit()
    print(f"[gold_agg] agg_population_by_district_year: {len(rows)} rows")
    return bucket


def _build_agg_health(gold_conn):
    with gold_conn.cursor() as cur:
        cur.execute(
            "SELECT g.province_name, fho.date_key, fho.target, fho.result, fho.f3_rate, "
            "dr.subcatalog_name, fho.report_key "
            "FROM fact_hdc_observation fho "
            "JOIN dim_hdc_report dr ON dr.report_key = fho.report_key "
            "LEFT JOIN dim_geography g ON g.geo_key = fho.geo_key"
        )
        hdc_rows = cur.fetchall()
        cur.execute(
            "SELECT g.province_name, fdr.date_key, fdr.rate_per_100k, fdr.case_fatality_pct "
            "FROM fact_disease_ranking fdr JOIN dim_geography g ON g.geo_key = fdr.geo_key"
        )
        dds_rows = cur.fetchall()

    bucket: dict[tuple, dict] = {}
    for province, year, target, result, f3, subcat, report_key in hdc_rows:
        if province is None or year is None:
            continue
        b = bucket.setdefault((province, year), {
            "attainment": [], "f3": [], "occ_reports": set(), "air_reports": set(),
            "total_obs": 0, "complete_obs": 0, "dds_rate": [], "dds_cfp": [],
        })
        b["total_obs"] += 1
        if target and result is not None and target != 0:
            b["attainment"].append(result / target)
            b["complete_obs"] += 1
        if f3 is not None:
            b["f3"].append(f3)
            b["complete_obs"] += 0 if (target and result is not None) else 1
        if subcat and ("อาชีพ" in subcat or "สิ่งแวดล้อม" in subcat):
            b["occ_reports"].add(report_key)
        if subcat and "มลพิษ" in subcat:
            b["air_reports"].add(report_key)

    for province, year, rate, cfp in dds_rows:
        b = bucket.setdefault((province, year), {
            "attainment": [], "f3": [], "occ_reports": set(), "air_reports": set(),
            "total_obs": 0, "complete_obs": 0, "dds_rate": [], "dds_cfp": [],
        })
        if rate is not None:
            b["dds_rate"].append(rate)
        if cfp is not None:
            b["dds_cfp"].append(cfp)

    rows = []
    for (province, year), b in bucket.items():
        avg_rate = sum(b["dds_rate"]) / len(b["dds_rate"]) if b["dds_rate"] else None
        avg_cfp = sum(b["dds_cfp"]) / len(b["dds_cfp"]) if b["dds_cfp"] else None
        avg_attainment = sum(b["attainment"]) / len(b["attainment"]) if b["attainment"] else None
        avg_f3 = sum(b["f3"]) / len(b["f3"]) if b["f3"] else None
        completeness = (b["complete_obs"] / b["total_obs"]) if b["total_obs"] else None
        rows.append((
            province, year, avg_rate, avg_cfp, avg_attainment, avg_f3,
            len(b["occ_reports"]), len(b["air_reports"]), completeness,
        ))

    insert_sql = (
        "INSERT INTO agg_health_kpi_by_province_year (province_name, year_ce, avg_disease_incidence_rate, "
        "avg_case_fatality_pct, avg_ncd_target_attainment, avg_hdc_calculated_rate, occupational_report_count, "
        "air_pollution_report_count, surveillance_completeness_pct) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )
    with gold_conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    gold_conn.commit()
    print(f"[gold_agg] agg_health_kpi_by_province_year: {len(rows)} rows")
    return bucket


def _build_obt_composite_index(gold_conn, income_agg, factory_agg, pop_bucket, health_bucket):
    with gold_conn.cursor() as cur:
        cur.execute("SELECT DISTINCT province_name, year_ce FROM agg_economic_by_province_year")
        province_years = cur.fetchall()

    vuln_components, impact_components, vitality_components = {}, {}, {}
    for province, year in province_years:
        key = (province, year)
        inc = income_agg.get(key, {})
        total_vals = [v for v in inc.get("total", []) if v is not None]
        avg_income = sum(total_vals) / len(total_vals) if total_vals else None
        fa = factory_agg.get(province, {})

        pop_b = next((b for (p, d, y), b in pop_bucket.items() if p == province and y == year), None)
        crowded_share = (pop_b["crowded_pop"] / pop_b["pop"]) if pop_b and pop_b["pop"] else None

        health_b = health_bucket.get(key, {})
        attainment = health_b.get("attainment", [])
        avg_attainment = sum(attainment) / len(attainment) if attainment else None
        disease_burden = (1 - avg_attainment) if avg_attainment is not None else None  # lower attainment = higher burden
        risk_reports = len(health_b.get("occ_reports", set())) + len(health_b.get("air_reports", set()))

        def _f(v):  # pymysql returns DECIMAL columns as decimal.Decimal -- normalize to float
            return float(v) if v is not None else None

        vuln_components[key] = {
            "low_income": _f(-avg_income) if avg_income is not None else None,
            "crowding": _f(crowded_share),
            "disease_burden": _f(disease_burden),
        }
        impact_components[key] = {
            "factory_count": _f(fa.get("factory_count")),
            "workforce": _f(fa.get("total_workforce")),
            "risk_reports": _f(risk_reports),
        }
        vitality_components[key] = {
            "income": _f(avg_income),
            "capital": _f(fa.get("avg_capital")),
            "workforce": _f(fa.get("total_workforce")),
        }

    def _composite(components_by_key):
        all_keys = {k for d in components_by_key.values() for k in d}
        normalized_by_metric = {}
        for metric in all_keys:
            normalized_by_metric[metric] = _minmax_normalize(
                {pk: d.get(metric) for pk, d in components_by_key.items()}
            )
        result = {}
        for pk in components_by_key:
            vals = [normalized_by_metric[m][pk] for m in all_keys if normalized_by_metric[m][pk] is not None]
            result[pk] = round(sum(vals) / len(vals), 2) if vals else None
        return result

    vuln_score = _composite(vuln_components)
    impact_score = _composite(impact_components)
    vitality_score = _composite(vitality_components)

    rows = [
        (province, year, vuln_score.get((province, year)), impact_score.get((province, year)),
         vitality_score.get((province, year)))
        for province, year in province_years
    ]
    insert_sql = (
        "INSERT INTO obt_regional_composite_index (province_name, year_ce, "
        "socioeconomic_health_vulnerability_index, industrial_health_impact_index, "
        "catchment_economic_vitality_score) VALUES (%s,%s,%s,%s,%s)"
    )
    with gold_conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    gold_conn.commit()
    print(f"[gold_agg] obt_regional_composite_index: {len(rows)} rows")


def run() -> None:
    gold_conn = _connect("gold")
    income_agg, factory_agg = _build_agg_economic(gold_conn)
    pop_bucket = _build_agg_population(gold_conn)
    health_bucket = _build_agg_health(gold_conn)
    _build_obt_composite_index(gold_conn, income_agg, factory_agg, pop_bucket, health_bucket)
    gold_conn.close()


if __name__ == "__main__":
    run()

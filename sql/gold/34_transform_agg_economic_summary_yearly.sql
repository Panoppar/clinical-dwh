USE gold;

INSERT INTO agg_economic_summary_yearly (geo_key, year_ce, factory_count, total_investment_sum, total_workers_sum, investment_per_worker)
SELECT f.geo_key, dt.year_ce, COUNT(*),
    SUM(f.total_investment), SUM(f.total_workers),
    IF(SUM(f.total_workers) = 0 OR SUM(f.total_workers) IS NULL, NULL, ROUND(SUM(f.total_investment) / SUM(f.total_workers), 2))
FROM fact_factory_registration f
JOIN dim_date dt ON f.date_key = dt.date_key
GROUP BY f.geo_key, dt.year_ce;

UPDATE agg_economic_summary_yearly a
JOIN agg_economic_summary_yearly ay ON ay.geo_key = a.geo_key AND ay.year_ce = a.year_ce - 1
SET a.yoy_investment_growth_pct = CASE WHEN ay.total_investment_sum IS NULL OR ay.total_investment_sum = 0 THEN NULL
    ELSE ROUND((a.total_investment_sum - ay.total_investment_sum) / ay.total_investment_sum * 100, 4) END;

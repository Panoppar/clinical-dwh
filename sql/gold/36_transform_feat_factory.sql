USE gold;

-- Resolve each factory to its single latest registration record (max
-- date_key, then max fact_key as tiebreak) in two steps rather than a
-- correlated subquery, so there's no ambiguity about which row wins.
CREATE TEMPORARY TABLE latest_registration AS
SELECT factory_key, MAX(date_key) AS max_date_key
FROM fact_factory_registration
GROUP BY factory_key;

CREATE TEMPORARY TABLE latest_fact AS
SELECT r.factory_key, MAX(r.fact_key) AS latest_fact_key
FROM fact_factory_registration r
JOIN latest_registration lr ON lr.factory_key = r.factory_key AND lr.max_date_key = r.date_key
GROUP BY r.factory_key;

INSERT INTO feat_factory
    (factory_reg_no, province_name_th, tsic_code, permit_year_ce, total_investment, total_workers,
     male_workers, female_workers, total_horsepower, investment_per_worker, workforce_female_pct)
SELECT
    df.factory_reg_no, dg.province_name_th, df.tsic_code, dt.year_ce,
    f.total_investment, f.total_workers, f.male_workers, f.female_workers, f.total_horsepower,
    IF(f.total_workers IS NULL OR f.total_workers = 0, NULL, ROUND(f.total_investment / f.total_workers, 2)),
    IF(f.total_workers IS NULL OR f.total_workers = 0, NULL, ROUND(f.female_workers / f.total_workers * 100, 4))
FROM dim_factory df
JOIN latest_fact lf ON lf.factory_key = df.factory_key
JOIN fact_factory_registration f ON f.fact_key = lf.latest_fact_key
JOIN dim_date dt ON f.date_key = dt.date_key
LEFT JOIN dim_geography dg ON f.geo_key = dg.geo_key;

DROP TEMPORARY TABLE latest_registration;
DROP TEMPORARY TABLE latest_fact;

USE gold;

UPDATE feat_geography_month ft
JOIN fact_disease_incidence_hdc f ON f.geo_key = ft.geo_key AND f.date_key = ft.date_key AND f.grain = 'monthly'
JOIN dim_disease dd ON f.disease_key = dd.disease_key AND dd.source_system = 'hdc' AND dd.disease_code = 'dm'
SET ft.incidence_rate_dm = f.result;

UPDATE feat_geography_month ft
JOIN fact_disease_incidence_hdc f ON f.geo_key = ft.geo_key AND f.date_key = ft.date_key AND f.grain = 'monthly'
JOIN dim_disease dd ON f.disease_key = dd.disease_key AND dd.source_system = 'hdc' AND dd.disease_code = 'ht'
SET ft.incidence_rate_ht = f.result;

UPDATE feat_geography_month ft
JOIN fact_disease_incidence_hdc f ON f.geo_key = ft.geo_key AND f.date_key = ft.date_key AND f.grain = 'monthly'
JOIN dim_disease dd ON f.disease_key = dd.disease_key AND dd.source_system = 'hdc' AND dd.disease_code = 'copd'
SET ft.incidence_rate_copd = f.result;

UPDATE feat_geography_month ft
JOIN fact_disease_incidence_hdc f ON f.geo_key = ft.geo_key AND f.date_key = ft.date_key AND f.grain = 'monthly'
JOIN dim_disease dd ON f.disease_key = dd.disease_key AND dd.source_system = 'hdc' AND dd.disease_code = 'coronary'
SET ft.incidence_rate_coronary = f.result;

-- ihd is only tracked at annual grain (confirmed: hdc_incidence_annual
-- has disease='ihd' exclusively, hdc_incidence_monthly never does) --
-- date_key for an annual row is Jan 1 of that year, so this only
-- populates January rows of feat_geography_month, by design.
UPDATE feat_geography_month ft
JOIN fact_disease_incidence_hdc f ON f.geo_key = ft.geo_key AND f.date_key = ft.date_key AND f.grain = 'annual'
JOIN dim_disease dd ON f.disease_key = dd.disease_key AND dd.source_system = 'hdc' AND dd.disease_code = 'ihd'
SET ft.incidence_rate_ihd = f.result;

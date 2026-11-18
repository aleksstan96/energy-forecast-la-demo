-- Gold: a curated, model-ready data product for the CNOR market, one row per 15-minute interval and forecast issue.
-- Gold is the contract with consumers (models, dashboards): they read gold, not bronze or silver.
-- Every forecast issue is kept (not only the latest), so consumers can apply their own point-in-time rules.

CREATE OR REFRESH MATERIALIZED VIEW gold.cnor_market_15min (
  CONSTRAINT has_actual_price EXPECT (actual_price_eur_mwh IS NOT NULL)
)
COMMENT 'Gold: CNOR 15-minute intervals with the actual GME price and every Meteologica forecast issue (UTC).'
AS SELECT
  p.interval_start_utc,
  p.local_date,
  p.quarter_hour,
  CAST(p.price_eur_mwh AS DOUBLE)   AS actual_price_eur_mwh,
  f.content_id                      AS forecast_series_id,
  f.zone                            AS forecast_zone,
  f.kind                            AS forecast_kind,
  f.issued_at_utc                   AS forecast_issued_at_utc,
  CAST(f.forecast AS DOUBLE)        AS forecast_value
FROM silver.gme_zonal_prices p
JOIN silver.meteologica_forecasts_15min f
  ON f.interval_start_utc = p.interval_start_utc
WHERE p.zone = 'CNOR';

-- Silver (SQL), built on a Python table: SQL and Python datasets can depend on each other in one pipeline.
--
-- Materialized view vs streaming table:
--   - A streaming table appends new data incrementally and never recomputes old rows.
--   - A materialized view stores the result of a query and keeps it correct as the source changes
--     (refreshed incrementally when possible, otherwise recomputed). Use it for "latest", aggregates, joins.

CREATE OR REFRESH MATERIALIZED VIEW silver.meteologica_forecasts_latest
COMMENT 'Silver: latest issued forecast per series and 15-minute interval.'
AS SELECT
  content_id, zone, kind, local_date, quarter_hour,
  interval_start_utc, interval_end_utc, forecast, issued_at_utc, horizon_minutes
FROM silver.meteologica_forecasts_15min           -- batch read (no STREAM): a materialized view
QUALIFY row_number() OVER (PARTITION BY content_id, interval_start_utc ORDER BY issued_at_utc DESC) = 1;

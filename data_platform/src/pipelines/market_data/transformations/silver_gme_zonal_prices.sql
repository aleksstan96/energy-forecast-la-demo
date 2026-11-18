-- Silver: one price per zone and 15-minute interval, in UTC, latest publication only.
-- A materialized view, because de-duplicating needs to look across all rows, not only new ones.

CREATE OR REFRESH MATERIALIZED VIEW silver.gme_zonal_prices (
  CONSTRAINT valid_period EXPECT (quarter_hour BETWEEN 1 AND 100)
)
COMMENT 'Silver: GME MGP zonal prices, one row per zone and 15-minute interval (UTC), latest publication.'
AS SELECT
  Zone                                                    AS zone,
  to_date(CAST(FlowDate AS STRING), 'yyyyMMdd')           AS local_date,
  CAST(Period AS INT)                                     AS quarter_hour,
  timestampadd(MINUTE, (CAST(Period AS INT) - 1) * 15,
               to_utc_timestamp(CAST(to_date(CAST(FlowDate AS STRING), 'yyyyMMdd') AS TIMESTAMP), 'Europe/Rome'))
                                                          AS interval_start_utc,
  Price                                                   AS price_eur_mwh,
  _file_path,
  _file_modified_at
FROM bronze.gme_zonal_prices
QUALIFY row_number() OVER (PARTITION BY Zone, FlowDate, Period ORDER BY _file_modified_at DESC, _file_path DESC) = 1;

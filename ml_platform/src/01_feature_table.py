# Databricks notebook source
# MAGIC %md
# MAGIC # 1. Feature table: CNOR day-ahead price
# MAGIC One row per 15-minute delivery interval with:
# MAGIC - **features:** the Meteologica forecasts available **before the day-ahead gate closure** (D-1 12:00 local time),
# MAGIC   plus calendar features;
# MAGIC - **target:** the GME CNOR zonal price.
# MAGIC
# MAGIC Source: the gold data product `gold.cnor_market_15min` (owned by the data platform). The ML side reads gold only.
# MAGIC
# MAGIC **Point-in-time correctness:** for each interval, only the latest forecast issued before the decision time is used.
# MAGIC Using later forecasts in training would leak information the model won't have when it predicts.
# MAGIC
# MAGIC Any Unity Catalog table with a primary key can be used as a feature table. The `TIMESERIES` key marks the time
# MAGIC column for point-in-time lookups.

# COMMAND ----------

dbutils.widgets.text("catalog", "dev")
dbutils.widgets.text("schema", "ml")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
table = f"{catalog}.{schema}.cnor_price_features"

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {table} (
  interval_start_utc      TIMESTAMP NOT NULL COMMENT 'Start of the 15-minute delivery interval (UTC)',
  local_date              DATE      COMMENT 'Delivery day (Europe/Rome)',
  quarter_hour            INT       COMMENT 'Quarter-hour of the local delivery day (1..92/96/100)',
  hour_local              INT,
  day_of_week             INT       COMMENT '1 = Sunday ... 7 = Saturday',
  is_weekend              BOOLEAN,
  price_fc                DOUBLE    COMMENT 'Meteologica CNOR price forecast (EUR/MWh)',
  solar_sud_fc            DOUBLE    COMMENT 'Meteologica SUD solar production forecast (MW)',
  solar_nord_fc           DOUBLE    COMMENT 'Meteologica NORD solar production forecast (MW)',
  wind_sici_fc            DOUBLE    COMMENT 'Meteologica SICI wind production forecast (MW)',
  forecast_issued_at_utc  TIMESTAMP COMMENT 'Issue time of the forecasts used (before gate closure)',
  target_price            DOUBLE    COMMENT 'GME CNOR zonal price (EUR/MWh): the label',
  CONSTRAINT cnor_price_features_pk PRIMARY KEY (interval_start_utc TIMESERIES)
)
COMMENT 'Features and target for the CNOR day-ahead price model. One row per 15-minute interval.'
""")

# COMMAND ----------

spark.sql(f"""
INSERT INTO {table}
WITH market AS (                     -- the gold data product: actuals + every forecast issue per interval
  SELECT * FROM {catalog}.gold.cnor_market_15min
),
available AS (                       -- forecasts issued before gate closure (D-1 12:00 local) of each delivery day
  SELECT * FROM market
  WHERE forecast_issued_at_utc <= to_utc_timestamp(CAST(date_sub(local_date, 1) AS TIMESTAMP) + INTERVAL 12 HOURS, 'Europe/Rome')
),
latest AS (                          -- latest such forecast per series and interval
  SELECT * FROM available
  QUALIFY row_number() OVER (PARTITION BY forecast_series_id, interval_start_utc ORDER BY forecast_issued_at_utc DESC) = 1
)
SELECT interval_start_utc, local_date, quarter_hour,
       hour(from_utc_timestamp(interval_start_utc, 'Europe/Rome')) AS hour_local,
       dayofweek(local_date)                                       AS day_of_week,
       dayofweek(local_date) IN (1, 7)                             AS is_weekend,
       max(CASE WHEN forecast_series_id = 7872 THEN forecast_value END) AS price_fc,
       max(CASE WHEN forecast_series_id = 9101 THEN forecast_value END) AS solar_sud_fc,
       max(CASE WHEN forecast_series_id = 9103 THEN forecast_value END) AS solar_nord_fc,
       max(CASE WHEN forecast_series_id = 9102 THEN forecast_value END) AS wind_sici_fc,
       max(forecast_issued_at_utc)                                      AS forecast_issued_at_utc,
       max(actual_price_eur_mwh)                                        AS target_price
FROM latest
GROUP BY interval_start_utc, local_date, quarter_hour
""")


# COMMAND ----------

summary = spark.sql(f"SELECT count(*) AS rows, min(local_date) AS first_day, max(local_date) AS last_day FROM {table}").first()
print(summary)
dbutils.notebook.exit(str(summary.asDict()))

# Databricks notebook source
# MAGIC %md
# MAGIC # 1. Feature table: CNOR day-ahead price
# MAGIC One row per 15-minute delivery interval with:
# MAGIC - **features:** the Meteologica forecasts available **before the day-ahead gate closure** (D-1 12:00 local time),
# MAGIC   plus calendar features;
# MAGIC - **target:** the GME CNOR zonal price.
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
WITH labels AS (
  SELECT interval_start_utc, local_date, quarter_hour, CAST(price_eur_mwh AS DOUBLE) AS target_price
  FROM {catalog}.silver.gme_zonal_prices
  WHERE zone = 'CNOR'
),
available AS (                       -- forecasts issued before gate closure (D-1 12:00 local) of each delivery day
  SELECT f.content_id, f.interval_start_utc, f.issued_at_utc, CAST(f.forecast AS DOUBLE) AS forecast
  FROM {catalog}.silver.meteologica_forecasts_15min f
  JOIN labels l USING (interval_start_utc)
  WHERE f.issued_at_utc <= to_utc_timestamp(CAST(date_sub(l.local_date, 1) AS TIMESTAMP) + INTERVAL 12 HOURS, 'Europe/Rome')
),
latest AS (                          -- latest such forecast per series and interval
  SELECT * FROM available
  QUALIFY row_number() OVER (PARTITION BY content_id, interval_start_utc ORDER BY issued_at_utc DESC) = 1
),
features AS (
  SELECT interval_start_utc,
         max(CASE WHEN content_id = 7872 THEN forecast END) AS price_fc,
         max(CASE WHEN content_id = 9101 THEN forecast END) AS solar_sud_fc,
         max(CASE WHEN content_id = 9103 THEN forecast END) AS solar_nord_fc,
         max(CASE WHEN content_id = 9102 THEN forecast END) AS wind_sici_fc,
         max(issued_at_utc)                                  AS forecast_issued_at_utc
  FROM latest GROUP BY interval_start_utc
)
SELECT l.interval_start_utc, l.local_date, l.quarter_hour,
       hour(from_utc_timestamp(l.interval_start_utc, 'Europe/Rome')) AS hour_local,
       dayofweek(l.local_date)                                      AS day_of_week,
       dayofweek(l.local_date) IN (1, 7)                            AS is_weekend,
       f.price_fc, f.solar_sud_fc, f.solar_nord_fc, f.wind_sici_fc, f.forecast_issued_at_utc,
       l.target_price
FROM labels l JOIN features f USING (interval_start_utc)
""")

# COMMAND ----------

summary = spark.sql(f"SELECT count(*) AS rows, min(local_date) AS first_day, max(local_date) AS last_day FROM {table}").first()
print(summary)
dbutils.notebook.exit(str(summary.asDict()))

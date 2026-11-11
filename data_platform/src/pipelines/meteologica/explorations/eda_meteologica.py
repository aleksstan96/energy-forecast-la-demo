# Databricks notebook source
# MAGIC %md
# MAGIC # Exploration notebook (not pipeline code)
# MAGIC This notebook sits next to the pipeline's source files but outside `transformations/`, so the pipeline never runs it.
# MAGIC Use files like this in the pipeline editor for exploratory analysis and checks while developing.
# MAGIC Run it on serverless after the pipeline has run in `dev`.

# COMMAND ----------

dbutils.widgets.text("catalog", "dev")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Rows per layer

# COMMAND ----------

display(spark.sql(f"""
    SELECT 'bronze files'          AS layer, count(*) AS rows FROM {catalog}.bronze.meteologica_forecasts
    UNION ALL SELECT 'silver: all issues', count(*) FROM {catalog}.silver.meteologica_forecasts_15min
    UNION ALL SELECT 'silver: latest only', count(*) FROM {catalog}.silver.meteologica_forecasts_latest
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Quarter-hours per local day (92 / 96 / 100 around daylight saving time changes)

# COMMAND ----------

display(spark.sql(f"""
    SELECT local_date, count(DISTINCT quarter_hour) AS quarter_hours
    FROM {catalog}.silver.meteologica_forecasts_latest
    WHERE content_id = 7872 AND local_date BETWEEN '2026-10-23' AND '2026-10-27'
    GROUP BY local_date ORDER BY local_date
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ### How forecasts for the same interval change across issues

# COMMAND ----------

display(spark.sql(f"""
    SELECT interval_start_utc, issued_at_utc, horizon_minutes, forecast
    FROM {catalog}.silver.meteologica_forecasts_15min
    WHERE content_id = 7872 AND interval_start_utc = (SELECT max(interval_start_utc) - INTERVAL 1 DAY
                                                    FROM {catalog}.silver.meteologica_forecasts_15min)
    ORDER BY issued_at_utc
"""))

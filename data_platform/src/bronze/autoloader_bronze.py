# Databricks notebook source
# MAGIC %md
# MAGIC # Auto Loader: landing volume → bronze Delta table
# MAGIC - Picks up only files not processed before (tracked in the checkpoint), then stops (`availableNow`).
# MAGIC - Exactly-once applies to **files**, not records. Overlapping pulls and revisions are kept here and resolved in silver.
# MAGIC - Unexpected fields go to `_rescued_data` instead of failing the load.

# COMMAND ----------

dbutils.widgets.text("catalog", "dev")
dbutils.widgets.text("source", "open_meteo")
dbutils.widgets.text("dataset", "weather_forecast")

catalog = dbutils.widgets.get("catalog")
source = dbutils.widgets.get("source")
dataset = dbutils.widgets.get("dataset")

landing_path = f"/Volumes/{catalog}/raw/api_landing/{source}/{dataset}/"
checkpoint_path = f"/Volumes/{catalog}/bronze/checkpoints/{source}/{dataset}/"
target_table = f"{catalog}.bronze.{source}_{dataset}"

# COMMAND ----------

from pyspark.sql import functions as F

stream = (
    spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", checkpoint_path + "_schema")
    .option("cloudFiles.inferColumnTypes", "true")
    .option("cloudFiles.schemaEvolutionMode", "rescue")
    .option("multiLine", "true")          # each file is one JSON document (object or array)
    .load(landing_path)
    .select(
        "*",
        F.lit(source).alias("_source"),
        F.lit(dataset).alias("_dataset"),
        F.col("_metadata.file_path").alias("_file_path"),
        F.col("_metadata.file_modification_time").alias("_file_modified_at"),
        F.current_timestamp().alias("_ingested_at"),
    )
)

query = (
    stream.writeStream
    .option("checkpointLocation", checkpoint_path)
    .trigger(availableNow=True)
    .toTable(target_table)
)
query.awaitTermination()

# COMMAND ----------

spark.sql(f"COMMENT ON TABLE {target_table} IS 'Bronze: raw {source}/{dataset} records as received, plus ingestion metadata. Append-only.'")
print(spark.sql(f"SELECT count(*) AS rows, count(DISTINCT _file_path) AS files FROM {target_table}").first())

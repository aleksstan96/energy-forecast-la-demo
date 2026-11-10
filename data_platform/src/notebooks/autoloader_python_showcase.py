# Databricks notebook source
# MAGIC %md
# MAGIC # Auto Loader in Python: showcase (run cell by cell)
# MAGIC The bronze pipeline uses Auto Loader through SQL (`STREAM read_files`). This notebook shows the same engine in
# MAGIC Python (`spark.readStream.format("cloudFiles")`), where you manage the checkpoint and trigger yourself.
# MAGIC
# MAGIC It reads the simulated Meteologica files and writes to a **separate scratch table**, so it never touches the
# MAGIC pipeline's `bronze.meteologica_forecasts`. The last cell resets the demo.

# COMMAND ----------

dbutils.widgets.text("catalog", "dev")
catalog = dbutils.widgets.get("catalog")
if catalog == "prod":
    raise ValueError("This showcase only runs against dev")

landing_path = f"/Volumes/{catalog}/raw/api_landing/meteologica/"
# The checkpoint is Auto Loader's memory: which files were processed, plus the inferred schema.
# In a pipeline this is managed for you; here we choose its location ourselves.
checkpoint_path = f"/Volumes/{catalog}/bronze/checkpoints/showcase/meteologica/"
target_table = f"{catalog}.bronze.showcase_meteologica_python"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Read new files incrementally
# MAGIC - `cloudFiles` = Auto Loader. It lists the folder (recursively) and skips files recorded in the checkpoint.
# MAGIC - `singleVariantColumn`: the whole JSON document goes into one VARIANT column. Needed here because the provider's
# MAGIC   field names (e.g. `"From yyyy-mm-dd hh:mm"`) are not valid Delta column names.
# MAGIC - `maxFilesPerTrigger`: process at most N files per micro-batch, to keep large backfills in steady batches.
# MAGIC - `_metadata`: file-level metadata (path, modification time) for lineage.

# COMMAND ----------

from pyspark.sql import functions as F

stream = (
    spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", checkpoint_path + "_schema")   # where the inferred schema is stored
    .option("singleVariantColumn", "raw")                               # whole file -> one VARIANT column
    .option("cloudFiles.maxFilesPerTrigger", 100)                       # 336 files -> 4 micro-batches
    # Other useful options (not needed here):
    #   .option("pathGlobFilter", "7872_*.json")                        # only some files
    #   .option("cloudFiles.includeExistingFiles", "false")             # only files arriving after the first run
    #   .option("cloudFiles.schemaHints", "...")                        # pin column types when not using VARIANT
    .load(landing_path)
    .select(
        F.expr("raw:content_id::int").alias("content_id"),            # extracted for filtering
        "raw",
        F.col("_metadata.file_path").alias("_file_path"),
        F.col("_metadata.file_modification_time").alias("_file_modified_at"),
        F.current_timestamp().alias("_ingested_at"),
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Write with `availableNow`
# MAGIC Process everything that's new, in micro-batches, then stop. This is the scheduled-batch pattern on serverless.

# COMMAND ----------

query = (
    stream.writeStream
    .option("checkpointLocation", checkpoint_path)    # exactly-once per file is tracked here
    .trigger(availableNow=True)
    .toTable(target_table)
)
query.awaitTermination()

# Each micro-batch is one entry in recentProgress: shows maxFilesPerTrigger at work.
for p in query.recentProgress:
    print(f"batch {p['batchId']}: {p['numInputRows']} rows")
print(spark.sql(f"SELECT count(*) AS rows, count(DISTINCT _file_path) AS files FROM {target_table}").first())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Run it again: nothing is reprocessed
# MAGIC Re-run cells 1 and 2. The checkpoint already lists every file, so the new run reads 0 rows and the table count
# MAGIC stays the same. Land new files (run the simulator job with later dates) and only those get picked up.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Parse the VARIANT (a preview of silver)

# COMMAND ----------

display(spark.sql(f"""
    SELECT content_id,
           d.value:["From yyyy-mm-dd hh:mm"]::string        AS from_local,
           d.value:["UTC offset from (UTC+/-hhmm)"]::string AS utc_offset,
           d.value:forecast::decimal(10,2)                  AS forecast
    FROM {target_table}, LATERAL variant_explode(raw:data) AS d
    WHERE content_id = 7872
    LIMIT 20
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Reset the demo
# MAGIC Dropping the table **and** the checkpoint starts from scratch. Deleting only the checkpoint would reprocess every
# MAGIC file into the existing table and create duplicates.

# COMMAND ----------

spark.sql(f"DROP TABLE IF EXISTS {target_table}")
dbutils.fs.rm(checkpoint_path, recurse=True)
print("reset done")

# Databricks notebook source
# MAGIC %md
# MAGIC # 4. Batch inference
# MAGIC Loads the **champion** model and scores the feature table in Spark. Results go to a predictions table with the
# MAGIC model version and scoring time, so every prediction can be traced back to the model that produced it, and compared
# MAGIC with actuals for monitoring.

# COMMAND ----------

dbutils.widgets.text("catalog", "dev")
dbutils.widgets.text("schema", "ml")
dbutils.widgets.text("model_name", "cnor_price_model")
catalog, schema = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
full_name = f"{catalog}.{schema}.{dbutils.widgets.get('model_name')}"
predictions = f"{catalog}.{schema}.cnor_price_predictions"

# COMMAND ----------

import mlflow
from mlflow import MlflowClient
from pyspark.sql import functions as F

mlflow.set_registry_uri("databricks-uc")
version = MlflowClient().get_model_version_by_alias(full_name, "champion").version

# Spark UDF: distributed scoring. env_manager="local" uses this task's (pinned) environment.
predict = mlflow.pyfunc.spark_udf(spark, model_uri=f"models:/{full_name}@champion", env_manager="local",
                                   result_type="double")   # one number per row

FEATURES = ["quarter_hour", "hour_local", "day_of_week", "is_weekend",
            "price_fc", "solar_sud_fc", "solar_nord_fc", "wind_sici_fc"]
features = (spark.table(f"{catalog}.{schema}.cnor_price_features")
            .withColumn("is_weekend", F.col("is_weekend").cast("int"))
            .dropna(subset=FEATURES))

scored = features.select(
    "interval_start_utc", "local_date", "quarter_hour",
    predict(*[F.col(c) for c in FEATURES]).alias("predicted_price"),
    F.col("target_price").alias("actual_price"),             # known later; kept for monitoring
    F.lit(version).alias("model_version"),
    F.current_timestamp().alias("scored_at"),
)

# COMMAND ----------

# Upsert by interval: re-scoring replaces the previous prediction for the same interval.
spark.sql(f"""CREATE TABLE IF NOT EXISTS {predictions} (
  interval_start_utc TIMESTAMP, local_date DATE, quarter_hour INT, predicted_price DOUBLE, actual_price DOUBLE,
  model_version STRING, scored_at TIMESTAMP) COMMENT 'CNOR price predictions from the champion model.'""")
scored.createOrReplaceTempView("new_predictions")
spark.sql(f"""MERGE INTO {predictions} t USING new_predictions s ON t.interval_start_utc = s.interval_start_utc
              WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *""")

summary = spark.sql(f"""SELECT count(*) AS rows, max(model_version) AS model_version,
                        round(avg(abs(predicted_price - actual_price)), 2) AS mae FROM {predictions}""").first()
print(summary)
dbutils.notebook.exit(str(summary.asDict()))

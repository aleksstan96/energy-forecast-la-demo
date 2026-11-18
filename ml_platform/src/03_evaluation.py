# Databricks notebook source
# MAGIC %md
# MAGIC # 3a. Evaluation (deployment job)
# MAGIC Scores the new model version and the current **champion** on the same recent data and records the results as
# MAGIC tags on the model version, so the approver sees them in the model version page.

# COMMAND ----------

dbutils.widgets.text("model_name", "")
dbutils.widgets.text("model_version", "")
dbutils.widgets.text("catalog", "dev")
dbutils.widgets.text("schema", "ml")
model_name, model_version = dbutils.widgets.get("model_name"), dbutils.widgets.get("model_version")
catalog, schema = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")

# COMMAND ----------

import mlflow
import numpy as np
from mlflow import MlflowClient

mlflow.set_registry_uri("databricks-uc")
client = MlflowClient()

FEATURES = ["quarter_hour", "hour_local", "day_of_week", "is_weekend",
            "price_fc", "solar_sud_fc", "solar_nord_fc", "wind_sici_fc"]
df = (spark.table(f"{catalog}.{schema}.cnor_price_features")
      .select("local_date", *FEATURES, "target_price").dropna().toPandas())
df["is_weekend"] = df["is_weekend"].astype(int)
recent = df[df["local_date"] >= sorted(df["local_date"].unique())[-5]]


def mae(uri):
    model = mlflow.pyfunc.load_model(uri)
    return float(np.mean(np.abs(model.predict(recent[FEATURES]) - recent["target_price"])))


new_mae = mae(f"models:/{model_name}/{model_version}")
client.set_model_version_tag(model_name, model_version, "eval_mae", f"{new_mae:.3f}")

try:
    champion = client.get_model_version_by_alias(model_name, "champion")
    champion_mae = mae(f"models:/{model_name}@champion")
    client.set_model_version_tag(model_name, model_version, "champion_mae", f"{champion_mae:.3f}")
    client.set_model_version_tag(model_name, model_version, "better_than_champion", str(new_mae <= champion_mae))
    print(f"version {model_version}: MAE {new_mae:.3f} vs champion v{champion.version}: {champion_mae:.3f}")
except mlflow.exceptions.MlflowException:
    client.set_model_version_tag(model_name, model_version, "better_than_champion", "no champion yet")
    print(f"version {model_version}: MAE {new_mae:.3f} (no champion yet)")

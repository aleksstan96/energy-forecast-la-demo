# Databricks notebook source
# MAGIC %md
# MAGIC # 2. Train and register the model
# MAGIC - Time-based split: the last days are held out as the test set (never a random split for time series).
# MAGIC - LightGBM, tracked with MLflow autologging; metrics compared with a naive baseline (the provider's price forecast).
# MAGIC - Registered in Unity Catalog with a signature and alias **challenger**.
# MAGIC - The registered model is connected to the deployment job, which starts automatically for the new version.

# COMMAND ----------

dbutils.widgets.text("catalog", "dev")
dbutils.widgets.text("schema", "ml")
dbutils.widgets.text("model_name", "cnor_price_model")
dbutils.widgets.text("experiment_id", "")
dbutils.widgets.text("deployment_job_id", "")
catalog, schema = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
full_name = f"{catalog}.{schema}.{dbutils.widgets.get('model_name')}"
experiment_id = dbutils.widgets.get("experiment_id")
deployment_job_id = dbutils.widgets.get("deployment_job_id")

# COMMAND ----------

import json

import lightgbm as lgb
import mlflow
import numpy as np
from mlflow import MlflowClient
from mlflow.models import infer_signature

mlflow.set_registry_uri("databricks-uc")          # register in Unity Catalog, not the legacy workspace registry
if experiment_id:
    mlflow.set_experiment(experiment_id=experiment_id)

FEATURES = ["quarter_hour", "hour_local", "day_of_week", "is_weekend",
            "price_fc", "solar_sud_fc", "solar_nord_fc", "wind_sici_fc"]
TARGET = "target_price"
TEST_DAYS = 5

df = (spark.table(f"{catalog}.{schema}.cnor_price_features")
      .select("local_date", *FEATURES, TARGET).dropna().toPandas())
df["is_weekend"] = df["is_weekend"].astype(int)
cutoff = sorted(df["local_date"].unique())[-TEST_DAYS]
train, test = df[df["local_date"] < cutoff], df[df["local_date"] >= cutoff]
X_train, y_train, X_test, y_test = train[FEATURES], train[TARGET], test[FEATURES], test[TARGET]

# COMMAND ----------

client = MlflowClient()
# Connect the deployment job to the model before registering a version, so the new version triggers it.
try:
    client.get_registered_model(full_name)
    if deployment_job_id:
        client.update_registered_model(full_name, deployment_job_id=deployment_job_id)
except mlflow.exceptions.MlflowException:
    client.create_registered_model(full_name, deployment_job_id=deployment_job_id or None,
                                   description="CNOR day-ahead price forecast (15-minute), LightGBM.")

mlflow.lightgbm.autolog(log_models=False)         # params and training metrics; the model is logged explicitly below

with mlflow.start_run(run_name="lightgbm_cnor_price") as run:
    model = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=15, random_state=42, verbose=-1)
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    metrics = {
        "test_mae": float(np.mean(np.abs(pred - y_test))),
        "test_rmse": float(np.sqrt(np.mean((pred - y_test) ** 2))),
        "baseline_mae": float(np.mean(np.abs(X_test["price_fc"] - y_test))),   # provider forecast as-is
        "train_rows": len(train), "test_rows": len(test),
    }
    mlflow.log_metrics(metrics)
    mlflow.log_params({"test_from": str(cutoff), "features": ",".join(FEATURES)})

    info = mlflow.lightgbm.log_model(
        model, name="model",
        signature=infer_signature(X_test, pred),       # input/output schema, checked at scoring time
        input_example=X_test.head(5),
        registered_model_name=full_name,               # creates a new version in Unity Catalog
    )

version = info.registered_model_version
client.set_registered_model_alias(full_name, "challenger", version)   # aliases replace the old "stages"
result = {"model": full_name, "version": version, **{k: round(v, 3) for k, v in metrics.items() if "mae" in k or "rmse" in k}}
print(result)
dbutils.notebook.exit(json.dumps(result))

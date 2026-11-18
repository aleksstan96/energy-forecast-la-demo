# Databricks notebook source
# MAGIC %md
# MAGIC # 2. Train and register the model
# MAGIC - Time-based split: the last days are held out as the test set (never a random split for time series).
# MAGIC - Three LightGBM variants, each an MLflow run (nested under one parent run), compared on the same test set and
# MAGIC   against a naive baseline (the provider's price forecast as-is).
# MAGIC - Only the **best** variant is registered in Unity Catalog, with a signature and alias **challenger**.
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

mlflow.lightgbm.autolog(log_models=False)         # params and training metrics per run; models logged explicitly

# Model variants to compare (could also come from job parameters).
VARIANTS = {
    "lgbm_small_fast":   dict(n_estimators=100, learning_rate=0.10, num_leaves=63),
    "lgbm_baseline":     dict(n_estimators=300, learning_rate=0.05, num_leaves=15),
    "lgbm_regularised":  dict(n_estimators=600, learning_rate=0.02, num_leaves=7, min_child_samples=40),
}
baseline_mae = float(np.mean(np.abs(X_test["price_fc"] - y_test)))   # the provider's forecast, as-is

results = {}
with mlflow.start_run(run_name="cnor_price_training") as parent:
    mlflow.log_params({"test_from": str(cutoff), "features": ",".join(FEATURES), "variants": ",".join(VARIANTS)})
    mlflow.log_metric("baseline_mae", baseline_mae)
    for name, params in VARIANTS.items():
        with mlflow.start_run(run_name=name, nested=True) as child:          # one run per variant
            model = lgb.LGBMRegressor(random_state=42, verbose=-1, **params).fit(X_train, y_train)
            pred = model.predict(X_test)
            metrics = {"test_mae": float(np.mean(np.abs(pred - y_test))),
                       "test_rmse": float(np.sqrt(np.mean((pred - y_test) ** 2))),
                       "baseline_mae": baseline_mae}
            mlflow.log_metrics(metrics)
            # Log the model with every run (not registered yet), so any run could be registered later.
            logged = mlflow.lightgbm.log_model(model, name="model", signature=infer_signature(X_test, pred),
                                               input_example=X_test.head(5))
            results[name] = {"run_id": child.info.run_id, "model_uri": logged.model_uri, **metrics}

    best_name = min(results, key=lambda n: results[n]["test_mae"])
    best = results[best_name]
    mlflow.log_params({"best_variant": best_name})
    mlflow.log_metric("best_test_mae", best["test_mae"])

# Register only the best run's model: one new version in Unity Catalog (this triggers the deployment job).
mv = mlflow.register_model(best["model_uri"], full_name)
client.set_model_version_tag(full_name, mv.version, "variant", best_name)
version = mv.version
client.set_registered_model_alias(full_name, "challenger", version)   # aliases replace the old "stages"
result = {"model": full_name, "version": version, "best_variant": best_name,
          "runs": {n: round(r["test_mae"], 3) for n, r in results.items()}, "baseline_mae": round(baseline_mae, 3)}
print(result)
dbutils.notebook.exit(json.dumps(result))

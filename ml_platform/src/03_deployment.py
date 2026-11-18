# Databricks notebook source
# MAGIC %md
# MAGIC # 3c. Deployment (deployment job)
# MAGIC Promotes the approved version: moves the **champion** alias to it. Batch inference always loads `@champion`, so
# MAGIC promotion and rollback are a single alias change, with no code change.

# COMMAND ----------

dbutils.widgets.text("model_name", "")
dbutils.widgets.text("model_version", "")
model_name, model_version = dbutils.widgets.get("model_name"), dbutils.widgets.get("model_version")

# COMMAND ----------

import mlflow
from mlflow import MlflowClient

mlflow.set_registry_uri("databricks-uc")
MlflowClient().set_registered_model_alias(model_name, "champion", model_version)
print(f"{model_name}@champion -> version {model_version}")

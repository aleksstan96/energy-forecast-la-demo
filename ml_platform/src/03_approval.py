# Databricks notebook source
# MAGIC %md
# MAGIC # 3b. Approval (deployment job)
# MAGIC The task passes only when the model version has the Unity Catalog tag named after this task (`approval_check`)
# MAGIC set to `Approved`. The first run always stops here. An approver reviews the evaluation tags on the model version
# MAGIC page and clicks **Approve**, which sets the tag and repairs the run.

# COMMAND ----------

dbutils.widgets.text("model_name", "")
dbutils.widgets.text("model_version", "")
model_name, model_version = dbutils.widgets.get("model_name"), dbutils.widgets.get("model_version")
TAG = "approval_check"     # must match the task name in the job

# COMMAND ----------

import mlflow
from mlflow import MlflowClient

mlflow.set_registry_uri("databricks-uc")
tags = MlflowClient().get_model_version(model_name, model_version).tags
if tags.get(TAG, "").lower() != "approved":
    raise Exception(f"{model_name} v{model_version} is waiting for approval (tag '{TAG}' = '{tags.get(TAG, '')}').")
print(f"{model_name} v{model_version} approved")

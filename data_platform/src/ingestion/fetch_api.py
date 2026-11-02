# Databricks notebook source
# MAGIC %md
# MAGIC # Fetch from a REST API and land the raw response
# MAGIC Writes the response **exactly as received** to
# MAGIC `/Volumes/<catalog>/raw/api_landing/<source>/<dataset>/ingest_date=YYYY-MM-DD/<request_ts>.json`.
# MAGIC No parsing or flattening here: that happens in bronze/silver, so a failed transformation never loses source data.

# COMMAND ----------

# MAGIC %md
# MAGIC trivial change

# COMMAND ----------

dbutils.widgets.text("catalog", "dev")
dbutils.widgets.text("source", "open_meteo")
dbutils.widgets.text("dataset", "weather_forecast")

catalog = dbutils.widgets.get("catalog")
source = dbutils.widgets.get("source")
dataset = dbutils.widgets.get("dataset")

# COMMAND ----------

import datetime as dt
import os

import requests

from sources import get_source   # same folder; bundle-deployed files are importable

cfg = get_source(source, dataset)
request_ts = dt.datetime.now(dt.timezone.utc)
run_date = request_ts.strftime("%Y-%m-%d")

params = {k: (v.format(run_date=run_date) if isinstance(v, str) else v) for k, v in cfg["params"].items()}

auth = None
if cfg.get("auth") and cfg["auth"]["type"] == "basic":
    a = cfg["auth"]
    auth = (
        dbutils.secrets.get(catalog=a["secret_catalog"], schema=a["secret_schema"], key=a["user_key"]),
        dbutils.secrets.get(catalog=a["secret_catalog"], schema=a["secret_schema"], key=a["password_key"]),
    )

resp = requests.get(cfg["url"], params=params, auth=auth, timeout=cfg["timeout_seconds"])
resp.raise_for_status()      # fail the task, so job retries and failure alerts apply

# COMMAND ----------

folder = f"/Volumes/{catalog}/raw/api_landing/{source}/{dataset}/ingest_date={run_date}"
os.makedirs(folder, exist_ok=True)
path = f"{folder}/{request_ts:%Y%m%dT%H%M%SZ}.json"

with open(path, "wb") as f:
    f.write(resp.content)    # bytes as received, not re-serialised

print(f"Landed {len(resp.content):,} bytes → {path}")
dbutils.jobs.taskValues.set(key="landed_path", value=path)
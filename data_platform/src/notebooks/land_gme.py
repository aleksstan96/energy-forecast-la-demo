# Databricks notebook source
# MAGIC %md
# MAGIC # Land simulated GME zonal prices (demo only)
# MAGIC Writes one file per delivery day, published the day before, to
# MAGIC `/Volumes/<catalog>/raw/api_landing/gme/zonal_prices/ingest_date=YYYY-MM-DD/<request_ts>.json`,
# MAGIC as the decoded content of the GME API response. One day is fetched twice, to show de-duplication in silver.
# MAGIC Refuses to write to `prod`.

# COMMAND ----------

dbutils.widgets.text("catalog", "dev")
dbutils.widgets.text("start_date", "2026-10-21")
dbutils.widgets.text("end_date", "2026-11-10")
catalog = dbutils.widgets.get("catalog")
if catalog == "prod":
    raise ValueError("Simulated data must never be written to prod")

# COMMAND ----------

import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.abspath(".."))
from simulation.gme import build_zonal_prices

base = f"/Volumes/{catalog}/raw/api_landing/gme/zonal_prices"
first = dt.date.fromisoformat(dbutils.widgets.get("start_date"))
last = dt.date.fromisoformat(dbutils.widgets.get("end_date"))


def land(day, request_ts):
    folder = f"{base}/ingest_date={request_ts:%Y-%m-%d}"
    os.makedirs(folder, exist_ok=True)
    path = f"{folder}/{request_ts:%Y%m%dT%H%M%SZ}.json"
    with open(path, "w") as f:
        json.dump(build_zonal_prices(day), f)
    return path


written = []
day = first
while day <= last:
    published = dt.datetime.combine(day - dt.timedelta(days=1), dt.time(11, 58), dt.timezone.utc)
    written.append(land(day, published))
    day += dt.timedelta(days=1)

# A second pull of the same delivery day (same content): bronze keeps both files, silver keeps one.
written.append(land(dt.date(2026, 11, 5), dt.datetime(2026, 11, 4, 14, 30, tzinfo=dt.timezone.utc)))
print(f"{len(written)} files under {base}")

# Databricks notebook source
# MAGIC %md
# MAGIC # Synthetic landing data for daily sources: DEMO ONLY
# MAGIC Stands in for the grid operator (Terna) and market operator (GME) APIs, which need credentials.
# MAGIC Writes realistically shaped responses to `/Volumes/<catalog>/raw/api_landing/<source>/<dataset>/ingest_date=YYYY-MM-DD/<request_ts>.json`,
# MAGIC the same layout as `src/ingestion/fetch_api.py`. The values are random; **the shape and the edge cases are the point**:
# MAGIC - **terna / load_forecast**: local Italian time, `hour` 1..N. **25 Oct 2026 (DST end) has 25 hours.**
# MAGIC - **gme / mgp_prices**: Italian keys, numbers as strings with a decimal comma. **31 Oct is re-published with corrected prices** (`versione: 2`).
# MAGIC
# MAGIC Deterministic (fixed seed and dates): re-running rewrites the same files rather than adding new ones.
# MAGIC Never point this at `prod`.

# COMMAND ----------

dbutils.widgets.text("catalog", "dev")
catalog = dbutils.widgets.get("catalog")
if catalog == "prod":
    raise ValueError("Synthetic data must never be written to prod")

base = f"/Volumes/{catalog}/raw/api_landing"

import datetime as dt
import json
import os
import random
from zoneinfo import ZoneInfo

random.seed(42)
ROME, UTC = ZoneInfo("Europe/Rome"), dt.timezone.utc
ZONES = ["NORD", "CNOR", "CSUD", "SUD", "CALA", "SICI", "SARD"]
DAYS = [dt.date(2026, 10, 24) + dt.timedelta(days=i) for i in range(10)]   # 24 Oct .. 2 Nov


def land(source, dataset, payload, request_ts):
    folder = f"{base}/{source}/{dataset}/ingest_date={request_ts:%Y-%m-%d}"
    os.makedirs(folder, exist_ok=True)
    path = f"{folder}/{request_ts:%Y%m%dT%H%M%SZ}.json"
    with open(path, "w") as f:
        json.dump(payload, f)
    return path


def local_hours(day):
    """Number of local hours in an Italian calendar day (23, 24 or 25 around DST)."""
    start = dt.datetime.combine(day, dt.time(), ROME)
    end = dt.datetime.combine(day + dt.timedelta(days=1), dt.time(), ROME)
    return int((end.astimezone(UTC) - start.astimezone(UTC)).total_seconds() // 3600)


written = []

# COMMAND ----------

# Terna: daily load forecast per zone, published the afternoon before, in local hours
for day in DAYS:
    req = dt.datetime.combine(day - dt.timedelta(days=1), dt.time(16, 5), UTC)
    payload = {"result": {
        "meta": {"publisher": "terna", "publication_ts": f"{req:%Y-%m-%dT%H:%M:%S}Z", "timezone": "Europe/Rome", "unit": "MW"},
        "items": [{"zone": z, "date": f"{day:%Y-%m-%d}",
                   "values": [{"hour": h, "mw": round(random.uniform(1500, 18000), 1)} for h in range(1, local_hours(day) + 1)]}
                  for z in ZONES]}}
    written.append(land("terna", "load_forecast", payload, req))

# COMMAND ----------

# GME: daily day-ahead (MGP) prices per zone, plus one corrected re-publication
def mgp(day, bump=0.0):
    return [{"Data": f"{day:%Y%m%d}", "Ora": str(h),
             **{z: f"{random.uniform(60, 160) + bump:.2f}".replace(".", ",") for z in ZONES},
             "PUN": f"{random.uniform(80, 140) + bump:.2f}".replace(".", ",")}
            for h in range(1, local_hours(day) + 1)]


for day in DAYS:
    req = dt.datetime.combine(day - dt.timedelta(days=1), dt.time(12, 58), UTC)
    written.append(land("gme", "mgp_prices", {"MGP": {"Prezzi": mgp(day)}, "esito": "OK", "versione": 1}, req))

rev_day = dt.date(2026, 10, 31)
rev_req = dt.datetime.combine(rev_day, dt.time(9, 30), UTC)
written.append(land("gme", "mgp_prices", {"MGP": {"Prezzi": mgp(rev_day, bump=3.5)}, "esito": "RETTIFICA", "versione": 2}, rev_req))

# COMMAND ----------

print(f"{len(written)} files written under {base}")
for p in written[:2] + written[-2:]:
    print(p)

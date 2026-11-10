# Databricks notebook source
# MAGIC %md
# MAGIC # Land simulated Meteologica forecasts (demo only)
# MAGIC Writes forecast files in the provider's format to the raw landing volume, the same way the real fetch notebook
# MAGIC would after calling the API:
# MAGIC
# MAGIC `/Volumes/<catalog>/raw/api_landing/meteologica/<content_id>/ingest_date=YYYY-MM-DD/<content_id>_<yyyyMMddHHmm>.json`
# MAGIC
# MAGIC - Four issues a day per series, each forecasting the next 48 hours, so issues overlap (revisions).
# MAGIC - The date range includes 25 Oct 2026, when DST ends and the UTC offset changes from +0200 to +0100.
# MAGIC - Deterministic: re-running rewrites identical files, so it never adds duplicates.
# MAGIC - Refuses to write to `prod`.

# COMMAND ----------

# Parameters: set by the job (base_parameters) or edited here when running interactively.
dbutils.widgets.text("catalog", "dev")
dbutils.widgets.text("start_date", "2026-10-20")
dbutils.widgets.text("end_date", "2026-11-09")

catalog = dbutils.widgets.get("catalog")
start_date = dbutils.widgets.get("start_date")
end_date = dbutils.widgets.get("end_date")

# Guardrail: simulated data must never reach the production catalog.
if catalog == "prod":
    raise ValueError("Simulated data must never be written to prod")

# COMMAND ----------

# Make the bundle's src/ folder importable, so the notebook uses the same tested module as the unit tests.
# A notebook's working directory is its own folder (src/notebooks), so src/ is one level up.
import os
import sys

sys.path.insert(0, os.path.abspath(".."))

import datetime as dt
import json

from simulation.meteologica import CONTENTS, build_forecast, file_name

# COMMAND ----------

# Issue times (UTC). The minute is fixed so file names look like the provider's (e.g. ..._202611051323.json).
ISSUE_TIMES_UTC = [dt.time(5, 23), dt.time(11, 23), dt.time(17, 23), dt.time(23, 23)]

base = f"/Volumes/{catalog}/raw/api_landing/meteologica"
first_day = dt.date.fromisoformat(start_date)
days = (dt.date.fromisoformat(end_date) - first_day).days + 1

written, total_bytes = 0, 0
for d in range(days):
    day = first_day + dt.timedelta(days=d)
    for t in ISSUE_TIMES_UTC:
        issued_at = dt.datetime.combine(day, t, dt.timezone.utc)
        for content_id in CONTENTS:
            # One folder per series and landing date, as the real fetch code would write it.
            folder = f"{base}/{content_id}/ingest_date={issued_at:%Y-%m-%d}"
            os.makedirs(folder, exist_ok=True)
            payload = json.dumps(build_forecast(content_id, issued_at)).encode()
            with open(f"{folder}/{file_name(content_id, issued_at)}", "wb") as f:
                f.write(payload)                  # one JSON document per file, as received from the API
            written += 1
            total_bytes += len(payload)

print(f"{written} files, {total_bytes / 1e6:.1f} MB written under {base}")

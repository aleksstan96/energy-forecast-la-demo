"""Simulated Meteologica forecast files (demo only).

Reproduces the response format observed in the customer's landing volume:

    {"content_id": 7872,
     "content_name": "Italy CNOR day ahead power price forecast Meteologica 15min",
     "data": [{"From yyyy-mm-dd hh:mm": "2026-11-05 14:00",
               "To yyyy-mm-dd hh:mm": "2026-11-05 14:15",
               "UTC offset from (UTC+/-hhmm)": "UTC+0100",
               "UTC offset to (UTC+/-hhmm)": "UTC+0100",
               "forecast": "242.49"}, ...]}

Format traits the pipelines must handle (that's the point of simulating them):
  - one file per forecast series ("content") and issue, named <content_id>_<yyyyMMddHHmm>.json;
  - 15-minute rows in *local* Italian time, with the UTC offset carried per row (it changes on DST days);
  - values are strings, and field names contain spaces and parentheses (invalid as Delta column names);
  - every issue re-forecasts the next 48 hours, so consecutive issues overlap (revisions).
Values are dummy numbers with plausible shapes, not real forecasts.
"""
import datetime as dt
import math
import random
import zlib

from simulation.local_time import ROME, UTC, local_str, offset_hhmm
from simulation.zones import meteologica_area

# Forecast series ("contents"). 7872 and its name are the one real example seen in the customer's
# data; the other IDs and names are invented in the same style.
CONTENTS = {
    7872: {"zone": "CNOR", "kind": "price"},
    9101: {"zone": "SUD", "kind": "solar"},
    9102: {"zone": "SICI", "kind": "wind"},
    9103: {"zone": "NORD", "kind": "solar"},
}

_KIND_LABEL = {
    "price": "day ahead power price forecast",
    "solar": "solar photovoltaic power production forecast",
    "wind": "wind power production forecast",
}

HORIZON_HOURS = 48       # each issue covers the next 48 hours
STEP_MINUTES = 15        # 15-minute resolution


def content_name(content_id: int) -> str:
    """Human-readable series name, e.g. "Italy CNOR day ahead power price forecast Meteologica 15min"."""
    c = CONTENTS[content_id]
    return f"{meteologica_area(c['zone'])} {_KIND_LABEL[c['kind']]} Meteologica 15min"


def file_name(content_id: int, issued_at: dt.datetime) -> str:
    """Provider file naming: <content_id>_<yyyyMMddHHmm>.json (issue time, UTC)."""
    return f"{content_id}_{issued_at.astimezone(UTC):%Y%m%d%H%M}.json"


def _seeded(*parts) -> random.Random:
    """Deterministic random generator: the same inputs always give the same numbers.

    zlib.crc32 is used instead of hash(), because Python randomises hash() per process.
    """
    return random.Random(zlib.crc32("|".join(map(str, parts)).encode()))


def _value(kind: str, start_local: dt.datetime, rng: random.Random) -> float:
    """Dummy value with a plausible daily shape for each kind of series."""
    hour = start_local.hour + start_local.minute / 60
    if kind == "solar":                      # MW: zero at night, bell curve around 13:00 local
        daylight = max(0.0, math.sin(math.pi * (hour - 6) / 14)) if 6 <= hour <= 20 else 0.0
        return max(0.0, 1800 * daylight + rng.uniform(-60, 60) * daylight)
    if kind == "wind":                       # MW: slow daily wave plus noise, never negative
        return max(0.0, 600 + 250 * math.sin(2 * math.pi * hour / 24) + rng.uniform(-80, 80))
    # price, EUR/MWh: morning and evening peaks
    peaks = 25 * math.exp(-((hour - 8.5) ** 2) / 4) + 40 * math.exp(-((hour - 19.5) ** 2) / 5)
    return 95 + peaks + rng.uniform(-6, 6)


def build_forecast(content_id: int, issued_at: dt.datetime) -> dict:
    """One Meteologica response: the 48-hour forecast issued at `issued_at` (an aware datetime)."""
    kind = CONTENTS[content_id]["kind"]
    # The forecast starts at the first quarter-hour at or after the issue time.
    first = issued_at.astimezone(UTC).replace(second=0, microsecond=0)
    first += dt.timedelta(minutes=(-first.minute) % STEP_MINUTES)
    step = dt.timedelta(minutes=STEP_MINUTES)

    rows = []
    for i in range(HORIZON_HOURS * 60 // STEP_MINUTES):
        start = (first + i * step).astimezone(ROME)        # step in UTC, display in local time
        end = (first + (i + 1) * step).astimezone(ROME)
        # Seeded by series, interval and issue: re-running gives identical files, while a later
        # issue forecasts the same interval slightly differently (a revision).
        rng = _seeded(content_id, start.isoformat(), issued_at.isoformat())
        rows.append({
            "From yyyy-mm-dd hh:mm": local_str(start),
            "To yyyy-mm-dd hh:mm": local_str(end),
            "UTC offset from (UTC+/-hhmm)": f"UTC{offset_hhmm(start)}",
            "UTC offset to (UTC+/-hhmm)": f"UTC{offset_hhmm(end)}",
            "forecast": f"{_value(kind, start, rng):.2f}",   # values are strings in the provider format
        })
    return {"content_id": content_id, "content_name": content_name(content_id), "data": rows}

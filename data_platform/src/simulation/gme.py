"""Simulated GME (Italian market operator) MGP zonal prices (demo only).

Records follow the documented ME_ZonalPrices fields (FlowDate, Hour, Period, Market, Zone, Price) as the
decoded API content, at 15-minute granularity (MGP has quarter-hour periods since October 2025).
Values are dummy numbers: a daily price shape shared with the simulated price forecast, a daily level
shift, a solar effect (lower prices at midday) and noise, so forecasts are informative but not perfect.
"""
import datetime as dt
import math
import random
import zlib

from simulation.local_time import day_intervals
from simulation.zones import GME_PUN, ZONES

ZONE_OFFSETS = {"NORD": 0.0, "CNOR": 2.0, "CSUD": 3.0, "SUD": -4.0, "CALA": -6.0, "SICI": 8.0, "SARD": 5.0}


def _seeded(*parts) -> random.Random:
    return random.Random(zlib.crc32("|".join(map(str, parts)).encode()))


def _shape(hour: float) -> float:
    """Same daily shape as the simulated Meteologica price forecast (EUR/MWh)."""
    return 95 + 25 * math.exp(-((hour - 8.5) ** 2) / 4) + 40 * math.exp(-((hour - 19.5) ** 2) / 5)


def _solar_mw(hour: float) -> float:
    return 1800 * math.sin(math.pi * (hour - 6) / 14) if 6 <= hour <= 20 else 0.0


def build_zonal_prices(day: dt.date) -> list[dict]:
    """All MGP zonal price records for one delivery day (local Italian day), one per zone and quarter-hour."""
    shift = _seeded("gme-day", day.isoformat()).uniform(-12, 12)
    records = []
    for i, (start, _end) in enumerate(day_intervals(day, 15)):
        hour = start.hour + start.minute / 60
        base = _shape(hour) + shift - 0.012 * _solar_mw(hour)
        zone_prices = {}
        for zone in ZONES:
            noise = _seeded("gme", day.isoformat(), i, zone).uniform(-4, 4)
            zone_prices[zone] = round(base + ZONE_OFFSETS[zone] + noise, 2)
        zone_prices[GME_PUN] = round(sum(zone_prices.values()) / len(ZONES), 2)
        for zone, price in zone_prices.items():
            records.append({
                "FlowDate": int(day.strftime("%Y%m%d")),
                "Hour": i // 4 + 1,              # 1..23/24/25
                "Period": str(i + 1),            # 1..92/96/100
                "Market": "MGP",
                "Zone": zone,
                "Price": price,
            })
    return records

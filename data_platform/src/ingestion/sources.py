"""Source registry: one entry per (source, dataset). Fetch code stays generic; only this file grows.

Each entry defines how to build the request. Credentials are never stored here; sources that
need them name a Unity Catalog secret (catalog.schema.key), read at runtime with dbutils.secrets.
"""

# Representative coordinates per Italian market zone (one weather point per zone).
ZONE_POINTS = {
    "NORD": (45.46, 9.19),   # Milan
    "CNOR": (43.77, 11.25),  # Florence
    "CSUD": (41.90, 12.50),  # Rome
    "SUD":  (41.12, 16.87),  # Bari
    "CALA": (38.91, 16.59),  # Catanzaro
    "SICI": (38.12, 13.36),  # Palermo
    "SARD": (39.22, 9.12),   # Cagliari
}

SOURCES = {
    ("open_meteo", "weather_forecast"): {
        "url": "https://api.open-meteo.com/v1/forecast",
        "params": {
            "latitude": ",".join(str(lat) for lat, _ in ZONE_POINTS.values()),
            "longitude": ",".join(str(lon) for _, lon in ZONE_POINTS.values()),
            "hourly": "temperature_2m,shortwave_radiation,wind_speed_10m,cloud_cover",
            "forecast_days": 3,
            "timezone": "UTC",
        },
        "auth": None,             # public API, no credentials
        "timeout_seconds": 60,
    },
    # Example for a source with credentials (Terna / GME style):
    # ("terna", "load_forecast"): {
    #     "url": "https://<terna-api>/load/forecast",
    #     "params": {"dateFrom": "{run_date}", "dateTo": "{run_date}"},
    #     "auth": {"type": "basic", "secret_catalog": "secrets", "secret_schema": "terna",
    #              "user_key": "username", "password_key": "password"},
    #     "timeout_seconds": 120,
    # },
}


def get_source(source: str, dataset: str) -> dict:
    try:
        return SOURCES[(source, dataset)]
    except KeyError:
        raise ValueError(f"Unknown source/dataset: {source}/{dataset}. Register it in sources.py") from None

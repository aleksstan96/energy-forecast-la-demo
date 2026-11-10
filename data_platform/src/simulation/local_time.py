"""Italian local-time helpers.

Market and grid data are published per *local* calendar day (Europe/Rome), so a day has 23, 24 or 25
hours around daylight saving time changes. Intervals are built by stepping in UTC from local midnight,
which gives the correct number of intervals on DST days.
"""
import datetime as dt
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
UTC = dt.timezone.utc


def day_intervals(day: dt.date, minutes: int) -> list[tuple[dt.datetime, dt.datetime]]:
    """(start, end) intervals covering one local calendar day, as Europe/Rome-aware datetimes."""
    start = dt.datetime.combine(day, dt.time(), ROME).astimezone(UTC)
    end = dt.datetime.combine(day + dt.timedelta(days=1), dt.time(), ROME).astimezone(UTC)
    step = dt.timedelta(minutes=minutes)
    out = []
    t = start
    while t < end:
        out.append((t.astimezone(ROME), (t + step).astimezone(ROME)))
        t += step
    return out


def offset_hhmm(t: dt.datetime) -> str:
    """UTC offset as "+0100" (Meteologica style: prefixed with "UTC" by the caller)."""
    return t.strftime("%z")


def offset_colon(t: dt.datetime) -> str:
    """UTC offset as "+01:00" (Terna style)."""
    z = t.strftime("%z")
    return f"{z[:3]}:{z[3:]}"


def local_str(t: dt.datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Local wall-clock time without offset. Ambiguous on the DST-end hour, so the offset travels separately."""
    return t.astimezone(ROME).strftime(fmt)

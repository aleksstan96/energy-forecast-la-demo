import datetime as dt

from simulation.meteologica import CONTENTS, build_forecast, content_name, file_name

UTC = dt.timezone.utc
ISSUE = dt.datetime(2026, 11, 5, 13, 23, tzinfo=UTC)


def test_file_name_matches_provider_convention():
    assert file_name(7872, ISSUE) == "7872_202611051323.json"


def test_known_content_name_matches_observed_example():
    assert content_name(7872) == "Italy CNOR day ahead power price forecast Meteologica 15min"


def test_response_shape_and_string_values():
    r = build_forecast(7872, ISSUE)
    assert set(r) == {"content_id", "content_name", "data"}
    assert len(r["data"]) == 48 * 4                       # 48 hours of quarter-hours
    row = r["data"][0]
    assert set(row) == {"From yyyy-mm-dd hh:mm", "To yyyy-mm-dd hh:mm",
                        "UTC offset from (UTC+/-hhmm)", "UTC offset to (UTC+/-hhmm)", "forecast"}
    assert isinstance(row["forecast"], str)
    assert row["From yyyy-mm-dd hh:mm"] == "2026-11-05 14:30"   # 13:30 UTC = 14:30 local (UTC+1)


def test_offset_changes_across_dst_end():
    rows = build_forecast(9101, dt.datetime(2026, 10, 24, 12, 0, tzinfo=UTC))["data"]
    offsets = [r["UTC offset from (UTC+/-hhmm)"] for r in rows]
    assert offsets[0] == "UTC+0200" and offsets[-1] == "UTC+0100"
    # 02:00 local appears twice on 25 Oct: once at +0200, once at +0100
    two_am = [r["UTC offset from (UTC+/-hhmm)"] for r in rows if r["From yyyy-mm-dd hh:mm"] == "2026-10-25 02:00"]
    assert two_am == ["UTC+0200", "UTC+0100"]


def test_deterministic_and_revisions_differ():
    assert build_forecast(9102, ISSUE) == build_forecast(9102, ISSUE)
    later = build_forecast(9102, ISSUE + dt.timedelta(hours=6))
    first_overlap = later["data"][0]["From yyyy-mm-dd hh:mm"]
    earlier_row = next(r for r in build_forecast(9102, ISSUE)["data"] if r["From yyyy-mm-dd hh:mm"] == first_overlap)
    assert earlier_row["forecast"] != later["data"][0]["forecast"]


def test_solar_is_zero_at_night():
    rows = build_forecast(9103, ISSUE)["data"]
    night = [float(r["forecast"]) for r in rows if r["From yyyy-mm-dd hh:mm"].endswith(("02:00", "03:00"))]
    assert night and all(v == 0.0 for v in night)
    assert set(CONTENTS) == {7872, 9101, 9102, 9103}

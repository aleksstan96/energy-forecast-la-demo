import datetime as dt

from simulation.gme import build_zonal_prices


def test_fields_and_types():
    r = build_zonal_prices(dt.date(2026, 11, 5))[0]
    assert set(r) == {"FlowDate", "Hour", "Period", "Market", "Zone", "Price"}
    assert r["FlowDate"] == 20261105 and isinstance(r["Hour"], int) and isinstance(r["Period"], str)
    assert r["Market"] == "MGP" and isinstance(r["Price"], float)


def test_quarter_hours_and_hours_on_dst_end_day():
    recs = [r for r in build_zonal_prices(dt.date(2026, 10, 25)) if r["Zone"] == "CNOR"]
    assert len(recs) == 100
    assert max(r["Hour"] for r in recs) == 25 and recs[-1]["Period"] == "100"


def test_all_zones_and_pun():
    zones = {r["Zone"] for r in build_zonal_prices(dt.date(2026, 11, 5))}
    assert zones == {"NORD", "CNOR", "CSUD", "SUD", "CALA", "SICI", "SARD", "PUN"}


def test_deterministic():
    assert build_zonal_prices(dt.date(2026, 11, 1)) == build_zonal_prices(dt.date(2026, 11, 1))

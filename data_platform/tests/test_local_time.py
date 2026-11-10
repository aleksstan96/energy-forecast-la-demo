import datetime as dt

import pytest

from simulation.local_time import day_intervals, local_str, offset_colon, offset_hhmm


@pytest.mark.parametrize(
    "day, hours",
    [
        (dt.date(2026, 3, 29), 23),   # DST starts: 02:00 -> 03:00
        (dt.date(2026, 6, 15), 24),
        (dt.date(2026, 10, 25), 25),  # DST ends: 03:00 -> 02:00
    ],
)
def test_day_length_in_hours_and_quarter_hours(day, hours):
    assert len(day_intervals(day, 60)) == hours
    assert len(day_intervals(day, 15)) == hours * 4


def test_intervals_are_contiguous_and_cover_the_local_day():
    iv = day_intervals(dt.date(2026, 10, 25), 15)
    assert local_str(iv[0][0]) == "2026-10-25 00:00"
    assert local_str(iv[-1][1]) == "2026-10-26 00:00"
    assert all(a[1] == b[0] for a, b in zip(iv, iv[1:]))


def test_dst_end_repeats_the_local_hour_with_different_offsets():
    iv = day_intervals(dt.date(2026, 10, 25), 60)
    two_am = [s for s, _ in iv if local_str(s) == "2026-10-25 02:00"]
    assert [offset_hhmm(s) for s in two_am] == ["+0200", "+0100"]


def test_offset_formats():
    winter = dt.datetime(2026, 1, 10, 12, tzinfo=dt.timezone.utc)
    summer = dt.datetime(2026, 7, 10, 12, tzinfo=dt.timezone.utc)
    rome_w = day_intervals(winter.date(), 60)[12][0]
    rome_s = day_intervals(summer.date(), 60)[12][0]
    assert (offset_hhmm(rome_w), offset_colon(rome_w)) == ("+0100", "+01:00")
    assert (offset_hhmm(rome_s), offset_colon(rome_s)) == ("+0200", "+02:00")

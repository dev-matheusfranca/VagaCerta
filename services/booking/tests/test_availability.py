from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from hypothesis import given
from hypothesis import strategies as st

from booking.domain import SLOT_STEP, available_slots

TZ = ZoneInfo("America/Sao_Paulo")
DAY = date(2030, 1, 7)
LONG_AGO = datetime(2000, 1, 1, tzinfo=UTC)
PERIODS = [(time(9), time(12)), (time(13), time(18))]


def at(hour: int, minute: int = 0) -> datetime:
    return datetime.combine(DAY, time(hour, minute), TZ)


def test_slots_fit_entirely_inside_each_working_period():
    slots = available_slots(
        DAY, TZ, [(time(14), time(15)), (time(9), time(11))], timedelta(hours=1), [], LONG_AGO
    )

    assert slots == [at(9), at(9, 30), at(10), at(14)]


def test_busy_interval_blocks_every_overlapping_slot():
    slots = available_slots(
        DAY, TZ, [(time(9), time(12))], timedelta(minutes=30), [(at(10), at(11))], LONG_AGO
    )

    assert slots == [at(9), at(9, 30), at(11), at(11, 30)]


def test_slots_that_already_started_are_not_offered():
    slots = available_slots(
        DAY, TZ, [(time(9), time(11))], timedelta(minutes=30), [], now=at(9, 45)
    )

    assert slots == [at(10), at(10, 30)]


def test_day_without_working_hours_has_no_slots():
    assert available_slots(DAY, TZ, [], timedelta(minutes=30), [], LONG_AGO) == []


busy_intervals = st.lists(
    st.tuples(st.integers(0, 47), st.integers(1, 12)).map(
        lambda t: (
            at(8) + t[0] * timedelta(minutes=15),
            at(8) + (t[0] + t[1]) * timedelta(minutes=15),
        )
    ),
    max_size=6,
)


@given(busy=busy_intervals, minutes=st.sampled_from([15, 30, 45, 60, 90]))
def test_no_slot_overlaps_busy_time_or_leaves_working_hours(busy, minutes):
    duration = timedelta(minutes=minutes)

    slots = available_slots(DAY, TZ, PERIODS, duration, busy, LONG_AGO)

    for slot in slots:
        assert any(at(s.hour) <= slot and slot + duration <= at(e.hour) for s, e in PERIODS)
        assert all(slot + duration <= b_start or b_end <= slot for b_start, b_end in busy)
        assert (slot - at(9)) % SLOT_STEP == timedelta(0)

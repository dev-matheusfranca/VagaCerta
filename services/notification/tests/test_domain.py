from datetime import UTC, datetime, timedelta

from notification.domain import remind_at

STARTS_AT = datetime(2030, 1, 9, 12, tzinfo=UTC)


def test_reminds_one_day_before():
    assert remind_at(STARTS_AT, STARTS_AT - timedelta(days=3)) == STARTS_AT - timedelta(hours=24)


def test_last_minute_booking_is_reminded_two_hours_before():
    assert remind_at(STARTS_AT, STARTS_AT - timedelta(hours=10)) == STARTS_AT - timedelta(hours=2)


def test_booking_starting_soon_gets_no_reminder():
    assert remind_at(STARTS_AT, STARTS_AT - timedelta(hours=1)) is None

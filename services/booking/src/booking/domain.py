from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

SLOT_STEP = timedelta(minutes=30)


def available_slots(
    day: date,
    tz: ZoneInfo,
    periods: list[tuple[time, time]],
    duration: timedelta,
    busy: list[tuple[datetime, datetime]],
    now: datetime,
) -> list[datetime]:
    slots = []
    for start, end in sorted(periods):
        slot, limit = datetime.combine(day, start, tz), datetime.combine(day, end, tz)
        while slot + duration <= limit:
            free = all(slot + duration <= b_start or b_end <= slot for b_start, b_end in busy)
            if slot > now and free:
                slots.append(slot)
            slot += SLOT_STEP
    return slots

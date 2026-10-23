from datetime import datetime, timedelta

REMINDER_LEADS = (timedelta(hours=24), timedelta(hours=2))


def remind_at(starts_at: datetime, now: datetime) -> datetime | None:
    """Lembrete 24h antes; se o agendamento foi feito em cima da hora, 2h antes; senão, nenhum."""
    return next((starts_at - lead for lead in REMINDER_LEADS if starts_at - lead > now), None)

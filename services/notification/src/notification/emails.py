from email.message import EmailMessage
from email.utils import formataddr
from html import escape
from importlib.resources import files
from string import Template
from zoneinfo import ZoneInfo

from notification.config import WEB_URL
from notification.events import BookingDetails, OfferDetails

HTML = Template(files("notification").joinpath("email.html").read_text("utf-8"))
SENDER = formataddr(("VagaCerta", "agendamentos@vagacerta.dev"))
WEEKDAYS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")
MONTHS = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)  # fmt: skip


def confirmation(booking: BookingDetails) -> EmailMessage:
    return _email(
        booking,
        subject=f"Agendamento confirmado: {booking.service_name} · {booking.business_name}",
        label="Agendamento confirmado",
        title=f"Tudo certo, {_first_name(booking)}!",
        intro="Seu horário está reservado. Confira os detalhes abaixo.",
        accent="#168373",
    )


def reminder(booking: BookingDetails) -> EmailMessage:
    start = booking.starts_at.astimezone(ZoneInfo(booking.timezone))
    return _email(
        booking,
        subject=f"Lembrete: {booking.service_name} {WEEKDAYS[start.weekday()]} às {start:%H:%M}",
        label="Lembrete",
        title=f"Falta pouco, {_first_name(booking)}!",
        intro="Passando para lembrar do seu horário. Se não puder ir, cancele pelo botão abaixo "
        "para liberar a vaga para outra pessoa.",
        accent="#b45309",
    )


def cancellation(booking: BookingDetails) -> EmailMessage:
    return _email(
        booking,
        subject=f"Agendamento cancelado: {booking.service_name} · {booking.business_name}",
        label="Agendamento cancelado",
        title=f"Seu horário foi cancelado, {_first_name(booking)}",
        intro="O horário abaixo foi liberado. Quando quiser, é só agendar de novo.",
        accent="#64748b",
    )


def offer(details: OfferDetails) -> EmailMessage:
    tz = ZoneInfo(details.timezone)
    start, deadline = details.starts_at.astimezone(tz), details.expires_at.astimezone(tz)
    return _email(
        details,
        subject=f"Uma vaga abriu: {details.service_name} {WEEKDAYS[start.weekday()]} às "
        f"{start:%H:%M}",
        label="Vaga liberada",
        title=f"Uma vaga abriu pra você, {_first_name(details)}!",
        intro=f"Alguém cancelou e guardamos este horário para você até as {deadline:%H:%M}. "
        "Confirme antes disso, ou ele passa para a próxima pessoa da fila.",
        accent="#b45309",
        cta="Quero esse horário",
        link=f"{WEB_URL}/ofertas/{details.offer_id}",
    )


def _first_name(booking: BookingDetails) -> str:
    return booking.customer_name.split()[0]


def _email(
    booking: BookingDetails,
    *,
    subject: str,
    label: str,
    title: str,
    intro: str,
    accent: str,
    cta: str = "Ver agendamento",
    link: str | None = None,
) -> EmailMessage:
    tz = ZoneInfo(booking.timezone)
    start, end = booking.starts_at.astimezone(tz), booking.ends_at.astimezone(tz)
    price = booking.price_cents / 100
    details = {
        "Serviço": booking.service_name,
        "Profissional": booking.professional_name,
        "Quando": f"{WEEKDAYS[start.weekday()]}, {start.day} de {MONTHS[start.month - 1]}, "
        f"das {start:%H:%M} às {end:%H:%M}".capitalize(),
        "Local": f"{booking.business_name} · {booking.business_address}",
        "Valor": f"R$ {price:.2f}".replace(".", ",") if price else "Grátis",
    }
    link = link or f"{WEB_URL}/agendamentos/{booking.booking_id}"

    message = EmailMessage()
    message["From"] = SENDER
    message["To"] = formataddr((booking.customer_name, booking.customer_email))
    message["Subject"] = subject
    message.set_content(
        "\n".join([title, "", intro, "", *(f"{k}: {v}" for k, v in details.items()), "", link, ""])
    )
    rows = "".join(
        f'<tr><td style="padding:12px 0 0;width:110px;vertical-align:top;font-size:12px;'
        f'letter-spacing:.06em;text-transform:uppercase;color:#8a9a9c">{escape(k)}</td>'
        f'<td style="padding:12px 0 0;font-size:15px;font-weight:600">{escape(v)}</td></tr>'
        for k, v in details.items()
    )
    message.add_alternative(
        HTML.substitute(
            accent=accent,
            label=escape(label),
            title=escape(title),
            intro=escape(intro),
            rows=rows,
            link=escape(link),
            cta=escape(cta),
        ),
        subtype="html",
    )
    return message

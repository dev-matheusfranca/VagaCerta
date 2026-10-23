from datetime import timedelta
from uuid import uuid4

from notification import emails
from notification.events import OfferDetails


def test_confirmation_goes_to_the_customer_with_local_time_and_link(details):
    message = emails.confirmation(details)
    text = message.get_body(("plain",)).get_content()

    assert message["To"] == "Maria Silva <maria@example.com>"
    assert message["Subject"] == "Agendamento confirmado: Corte · Barbearia Teste"
    assert "Quarta, 9 de janeiro, das 09:00 às 09:30" in text
    assert "R$ 45,00" in text
    assert f"/agendamentos/{details.booking_id}" in text


def test_reminder_subject_names_the_day_and_time(details):
    assert emails.reminder(details)["Subject"] == "Lembrete: Corte quarta às 09:00"


def test_free_service_is_shown_as_free(details):
    message = emails.cancellation(details.model_copy(update={"price_cents": 0}))

    assert "Valor: Grátis" in message.get_body(("plain",)).get_content()


def test_customer_input_is_escaped_in_html(details):
    hostile = details.model_copy(update={"customer_name": "<script>alert(1)</script> Silva"})

    html = emails.confirmation(hostile).get_body(("html",)).get_content()

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_offer_links_to_the_claim_page_and_states_the_deadline(details):
    offer = OfferDetails(
        **details.model_dump(),
        offer_id=uuid4(),
        expires_at=details.starts_at - timedelta(hours=20),
    )

    message = emails.offer(offer)
    text = message.get_body(("plain",)).get_content()

    assert message["Subject"] == "Uma vaga abriu: Corte quarta às 09:00"
    assert "até as 13:00" in text
    assert f"/ofertas/{offer.offer_id}" in text
    assert "Quero esse horário" in message.get_body(("html",)).get_content()

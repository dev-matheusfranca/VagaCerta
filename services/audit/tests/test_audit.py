from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from audit.chain import GENESIS
from audit.main import create_app
from audit.models import AuditRecord
from audit.recorder import record
from vagacerta_auth import AUDIENCE, TokenVerifier

ISSUER = "http://keycloak.test/realms/vagacerta"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
BUSINESS, BOOKING = uuid4(), uuid4()


def token(*roles: str, businesses: tuple[str, ...] = ()) -> dict[str, str]:
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "realm_access": {"roles": list(roles)},
        "businesses": list(businesses),
    }
    return {"Authorization": f"Bearer {jwt.encode(claims, KEY, algorithm='RS256')}"}


def event(type: str, booking_id=BOOKING) -> dict:
    return {
        "event_id": str(uuid4()),
        "type": type,
        "occurred_at": datetime.now(UTC).isoformat(),
        "data": {"booking_id": str(booking_id), "business_id": str(BUSINESS)},
    }


@pytest.fixture(scope="module")
def app(database_url):
    return create_app(database_url, TokenVerifier(ISSUER, lambda _: KEY.public_key()))


@pytest.fixture
async def session(app):
    async with app.state.sessionmaker() as session:
        yield session
    # Só o superusuário, desligando os gatilhos, consegue limpar o registro entre os testes.
    async with app.state.sessionmaker() as session:
        await session.execute(text("ALTER TABLE audit_log DISABLE TRIGGER USER"))
        await session.execute(text("TRUNCATE audit_log"))
        await session.execute(text("ALTER TABLE audit_log ENABLE TRIGGER USER"))
        await session.commit()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client


async def test_each_event_is_chained_to_the_previous_one_and_recorded_once(session, client):
    created = event("booking.created")

    assert await record(session, "booking.events", created)
    assert not await record(session, "booking.events", created)
    assert await record(session, "booking.events", event("booking.cancelled"))

    first, second = (await session.scalars(select(AuditRecord).order_by(AuditRecord.seq))).all()
    verification = await client.get("/verify", headers=token("admin"))

    assert (first.prev_hash, second.prev_hash) == (GENESIS, first.hash)
    assert verification.json() == {"records": 2, "valid": True, "broken_at": None}


@pytest.mark.parametrize(
    "statement", ["UPDATE audit_log SET type = 'x'", "DELETE FROM audit_log", "TRUNCATE audit_log"]
)
async def test_the_database_refuses_to_change_the_log(session, statement):
    await record(session, "booking.events", event("booking.created"))

    with pytest.raises(DBAPIError, match="só aceita inserções"):
        await session.execute(text(statement))
    await session.rollback()


async def test_a_tampered_record_breaks_the_chain_from_that_point(session, client):
    for type in ("booking.created", "booking.completed", "booking.cancelled"):
        await record(session, "booking.events", event(type))
    seqs = (await session.scalars(select(AuditRecord.seq).order_by(AuditRecord.seq))).all()

    # Alguém com acesso ao banco troca o comparecimento registrado por uma falta.
    await session.execute(text("ALTER TABLE audit_log DISABLE TRIGGER audit_log_no_changes"))
    await session.execute(
        text(
            "UPDATE audit_log SET payload = jsonb_set(payload, '{type}', '\"booking.no_show\"') "
            "WHERE seq = :seq"
        ),
        {"seq": seqs[1]},
    )
    await session.execute(text("ALTER TABLE audit_log ENABLE TRIGGER audit_log_no_changes"))
    await session.commit()
    verification = await client.get("/verify", headers=token("admin"))

    assert verification.json() == {"records": 3, "valid": False, "broken_at": seqs[1]}


async def test_the_owner_follows_what_happened_to_a_booking(session, client):
    for type in ("booking.created", "booking.cancelled"):
        await record(session, "booking.events", event(type))
    await record(session, "booking.events", event("booking.created", booking_id=uuid4()))

    owner = await client.get(
        f"/bookings/{BOOKING}/trail", headers=token("owner", businesses=(str(BUSINESS),))
    )
    stranger = await client.get(
        f"/bookings/{BOOKING}/trail", headers=token("owner", businesses=(str(uuid4()),))
    )
    unknown = await client.get(
        f"/bookings/{uuid4()}/trail", headers=token("owner", businesses=(str(BUSINESS),))
    )

    assert [entry["type"] for entry in owner.json()] == ["booking.created", "booking.cancelled"]
    assert (stranger.status_code, unknown.status_code) == (403, 404)

from uuid import uuid4

import httpx

from waitlist.booking_client import BookingClient, ClientCredentials


def fake_keycloak_and_booking(seen: list[str]) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/token":
            seen.append(f"token {request.content.decode()}")
            return httpx.Response(200, json={"access_token": "service-token", "expires_in": 300})
        seen.append(f"{request.url.path} {request.headers['Authorization']}")
        return httpx.Response(409 if request.url.path.endswith("/release") else 200)

    return httpx.MockTransport(handle)


async def test_service_token_is_fetched_once_and_sent_on_every_call():
    seen: list[str] = []
    auth = ClientCredentials("http://keycloak/token", "waitlist-service", "secret")
    http = httpx.AsyncClient(
        base_url="http://booking", transport=fake_keycloak_and_booking(seen), auth=auth
    )
    booking = BookingClient(http)
    booking_id = uuid4()

    confirmed = await booking.confirm(booking_id)
    released = await booking.release(booking_id)

    assert (confirmed, released) == (True, False)
    assert seen == [
        "token grant_type=client_credentials&client_id=waitlist-service&client_secret=secret",
        f"/bookings/{booking_id}/confirm Bearer service-token",
        f"/bookings/{booking_id}/release Bearer service-token",
    ]

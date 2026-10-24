import httpx
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from mcp_server.config import BOOKING_URL, CATALOG_URL, WAITLIST_URL, WEB_URL
from mcp_server.server import create_server

server = create_server(
    httpx.AsyncClient(base_url=CATALOG_URL, timeout=5),
    httpx.AsyncClient(base_url=BOOKING_URL, timeout=5),
    httpx.AsyncClient(base_url=WAITLIST_URL, timeout=5),
    WEB_URL,
)


@server.custom_route("/health", methods=["GET"])  # type: ignore[untyped-decorator]
async def health(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


# Sem estado entre requisições, qualquer réplica atende; o Host é conferido contra DNS rebinding.
app = server.streamable_http_app(
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        allowed_hosts=["localhost:*", "127.0.0.1:*", "mcp-server:*"],
        allowed_origins=["http://localhost:*", "http://127.0.0.1:*"],
    ),
)

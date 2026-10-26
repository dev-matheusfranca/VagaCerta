import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from booking.api import router
from booking.catalog_client import CatalogClient
from vagacerta_auth import TokenVerifier, keycloak_verifier
from vagacerta_http import ResilientTransport

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://vagacerta:vagacerta@localhost:5434/booking"
)
CATALOG_URL = os.environ.get("CATALOG_URL", "http://localhost:8001")
KEYCLOAK_ISSUER = os.environ.get("KEYCLOAK_ISSUER", "http://localhost:8080/auth/realms/vagacerta")
KEYCLOAK_JWKS_URL = os.environ.get(
    "KEYCLOAK_JWKS_URL", f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"
)


def create_app(database_url: str, catalog: CatalogClient, tokens: TokenVerifier) -> FastAPI:
    app = FastAPI(title="VagaCerta · Booking")
    app.state.sessionmaker = async_sessionmaker(
        create_async_engine(database_url), expire_on_commit=False
    )
    app.state.catalog = catalog
    app.state.tokens = tokens
    app.include_router(router)

    @app.exception_handler(httpx.HTTPError)
    async def dependency_unavailable(request: Request, error: httpx.HTTPError) -> JSONResponse:
        return JSONResponse(
            {"detail": "Serviço indisponível no momento, tente de novo"}, status_code=503
        )

    return app


app = create_app(
    DATABASE_URL,
    CatalogClient(
        httpx.AsyncClient(base_url=CATALOG_URL, timeout=2, transport=ResilientTransport())
    ),
    keycloak_verifier(KEYCLOAK_ISSUER, KEYCLOAK_JWKS_URL),
)

import os

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from catalog.api import router
from vagacerta_auth import TokenVerifier, keycloak_verifier

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://vagacerta:vagacerta@localhost:5433/catalog"
)
KEYCLOAK_ISSUER = os.environ.get("KEYCLOAK_ISSUER", "http://localhost:8080/auth/realms/vagacerta")
KEYCLOAK_JWKS_URL = os.environ.get(
    "KEYCLOAK_JWKS_URL", f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"
)


def create_app(database_url: str, tokens: TokenVerifier) -> FastAPI:
    app = FastAPI(title="VagaCerta · Catalog")
    app.state.sessionmaker = async_sessionmaker(
        create_async_engine(database_url), expire_on_commit=False
    )
    app.state.tokens = tokens
    app.include_router(router)
    return app


app = create_app(DATABASE_URL, keycloak_verifier(KEYCLOAK_ISSUER, KEYCLOAK_JWKS_URL))

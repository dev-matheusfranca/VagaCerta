from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from vagacerta_auth import TokenVerifier, keycloak_verifier
from webhooks.api import router
from webhooks.config import (
    ALLOW_PRIVATE_TARGETS,
    DATABASE_URL,
    KEYCLOAK_ISSUER,
    KEYCLOAK_JWKS_URL,
)


def create_app(database_url: str, tokens: TokenVerifier, allow_private_targets: bool) -> FastAPI:
    app = FastAPI(title="VagaCerta · Webhooks")
    app.state.sessionmaker = async_sessionmaker(
        create_async_engine(database_url), expire_on_commit=False
    )
    app.state.tokens = tokens
    app.state.allow_private_targets = allow_private_targets
    app.include_router(router)
    return app


app = create_app(
    DATABASE_URL, keycloak_verifier(KEYCLOAK_ISSUER, KEYCLOAK_JWKS_URL), ALLOW_PRIVATE_TARGETS
)

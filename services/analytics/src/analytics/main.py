from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from analytics.api import router
from analytics.config import DATABASE_URL, KEYCLOAK_ISSUER, KEYCLOAK_JWKS_URL
from vagacerta_auth import TokenVerifier, keycloak_verifier


def create_app(database_url: str, tokens: TokenVerifier) -> FastAPI:
    app = FastAPI(title="VagaCerta · Analytics")
    app.state.sessionmaker = async_sessionmaker(
        create_async_engine(database_url), expire_on_commit=False
    )
    app.state.tokens = tokens
    app.include_router(router)
    return app


app = create_app(DATABASE_URL, keycloak_verifier(KEYCLOAK_ISSUER, KEYCLOAK_JWKS_URL))

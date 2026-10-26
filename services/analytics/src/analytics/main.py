import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from analytics.api import router
from analytics.catalog_client import CatalogClient
from analytics.config import CATALOG_URL, DATABASE_URL, KEYCLOAK_ISSUER, KEYCLOAK_JWKS_URL
from vagacerta_auth import TokenVerifier, keycloak_verifier
from vagacerta_http import ResilientTransport


def create_app(database_url: str, tokens: TokenVerifier, catalog: CatalogClient) -> FastAPI:
    app = FastAPI(title="VagaCerta · Analytics")
    app.state.sessionmaker = async_sessionmaker(
        create_async_engine(database_url), expire_on_commit=False
    )
    app.state.tokens = tokens
    app.state.catalog = catalog
    app.include_router(router)
    return app


app = create_app(
    DATABASE_URL,
    keycloak_verifier(KEYCLOAK_ISSUER, KEYCLOAK_JWKS_URL),
    CatalogClient(
        httpx.AsyncClient(base_url=CATALOG_URL, timeout=2, transport=ResilientTransport())
    ),
)

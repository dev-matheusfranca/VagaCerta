import os

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from catalog.api import router

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://vagacerta:vagacerta@localhost:5433/catalog"
)


def create_app(database_url: str) -> FastAPI:
    app = FastAPI(title="VagaCerta · Catalog")
    app.state.sessionmaker = async_sessionmaker(
        create_async_engine(database_url), expire_on_commit=False
    )
    app.include_router(router)
    return app


app = create_app(DATABASE_URL)

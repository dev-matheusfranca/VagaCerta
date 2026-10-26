import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from waitlist.api import router
from waitlist.booking_client import BookingClient, booking_client
from waitlist.catalog_client import CatalogClient
from waitlist.config import CATALOG_URL, DATABASE_URL


def create_app(database_url: str, catalog: CatalogClient, booking: BookingClient) -> FastAPI:
    app = FastAPI(title="VagaCerta · Waitlist")
    app.state.sessionmaker = async_sessionmaker(
        create_async_engine(database_url), expire_on_commit=False
    )
    app.state.catalog = catalog
    app.state.booking = booking
    app.include_router(router)

    @app.exception_handler(httpx.HTTPError)
    async def dependency_unavailable(request: Request, error: httpx.HTTPError) -> JSONResponse:
        return JSONResponse(
            {"detail": "Serviço indisponível no momento, tente de novo"}, status_code=503
        )

    return app


app = create_app(DATABASE_URL, CatalogClient(CATALOG_URL), booking_client())

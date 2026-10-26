import asyncio
from time import monotonic

import httpx

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class CircuitOpenError(httpx.TransportError):
    """O destino falhou demais seguidas vezes: a chamada nem sai até o circuito testar de novo."""


class ResilientTransport(httpx.AsyncBaseTransport):
    """Repete consultas que falham e para de chamar um destino que não responde.

    Só métodos seguros são repetidos: refazer um POST poderia duplicar o efeito. Depois de
    `failure_threshold` falhas seguidas, o circuito abre e as chamadas falham na hora por
    `reset_after` segundos; a primeira chamada depois disso testa o destino de novo.
    """

    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,
        *,
        retries: int = 2,
        backoff: float = 0.1,
        failure_threshold: int = 5,
        reset_after: float = 10.0,
    ) -> None:
        self._transport = transport or httpx.AsyncHTTPTransport()
        self._retries = retries
        self._backoff = backoff
        self._failure_threshold = failure_threshold
        self._reset_after = reset_after
        self._failures = 0
        self._opened_at: float | None = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if self._opened_at is not None and monotonic() - self._opened_at < self._reset_after:
            raise CircuitOpenError(f"Circuito aberto para {request.url.host}", request=request)
        retries = self._retries if request.method in SAFE_METHODS else 0
        attempt = 0
        while True:
            try:
                response = await self._transport.handle_async_request(request)
            except httpx.TransportError:
                if attempt == retries:
                    self._record(failed=True)
                    raise
            else:
                if response.status_code < 500 or attempt == retries:
                    self._record(failed=response.status_code >= 500)
                    return response
                await response.aclose()
            await asyncio.sleep(self._backoff * 2**attempt)
            attempt += 1

    def _record(self, *, failed: bool) -> None:
        self._failures = self._failures + 1 if failed else 0
        self._opened_at = monotonic() if self._failures >= self._failure_threshold else None

    async def aclose(self) -> None:
        await self._transport.aclose()

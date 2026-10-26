FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /bin/uv

ARG SERVICE
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH" SERVICE=$SERVICE

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY services ./services
COPY libs ./libs
# Tudo foi instalado pelo uv: o pip (e as libs que ele embute) não precisa ir para produção.
RUN uv sync --frozen --no-dev --package $SERVICE \
    && pip uninstall --yes pip \
    && useradd --system --uid 10001 app

WORKDIR /app/services/$SERVICE
EXPOSE 8000
USER 10001
CMD alembic upgrade head && opentelemetry-instrument uvicorn $SERVICE.main:app --host 0.0.0.0 --port 8000

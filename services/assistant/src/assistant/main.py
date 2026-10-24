from collections.abc import Callable
from typing import Any, Literal

import httpx
from fastapi import FastAPI, HTTPException
from mcp import Client
from pydantic import BaseModel, Field

from assistant.agent import reply
from assistant.config import MCP_URL, OLLAMA_MODEL, OLLAMA_URL, TIMEZONE


class Message(BaseModel):
    role: Literal["user", "assistant", "tool"]
    content: str = ""
    tool_calls: list[dict[str, Any]] | None = None
    tool_name: str | None = None


class Conversation(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=80)


def create_app(llm: httpx.AsyncClient, model: str, mcp: Callable[[], Client]) -> FastAPI:
    app = FastAPI(title="VagaCerta · Assistant")

    # A conversa inteira vem do navegador a cada turno: o serviço não guarda estado.
    @app.post("/chat", response_model=Conversation, response_model_exclude_none=True)
    async def chat(conversation: Conversation) -> dict[str, Any]:
        history = [m.model_dump(exclude_none=True) for m in conversation.messages]
        try:
            # O cliente MCP roda num task group: os erros chegam agrupados.
            async with mcp() as tools:
                return {"messages": await reply(history, llm, model, tools, TIMEZONE)}
        except* httpx.HTTPError:
            raise HTTPException(503, "O assistente está indisponível no momento") from None

    return app


app = create_app(
    httpx.AsyncClient(base_url=OLLAMA_URL, timeout=180), OLLAMA_MODEL, lambda: Client(MCP_URL)
)

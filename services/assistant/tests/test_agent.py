import json

import httpx
from httpx import ASGITransport, AsyncClient
from mcp import Client
from mcp.server.mcpserver import MCPServer

from assistant.agent import MAX_STEPS, reply
from assistant.main import create_app

tools = MCPServer("fake")


@tools.tool()
def find_slots(day: str) -> dict[str, list[str]]:
    """Horários livres de um dia."""
    return {"slots": ["10:00", "14:30"]}


def llm(*answers: dict) -> tuple[httpx.AsyncClient, list[dict]]:
    """Modelo de mentira: devolve as respostas na ordem e guarda o que recebeu."""
    received: list[dict] = []

    def handle(request: httpx.Request) -> httpx.Response:
        received.append(json.loads(request.content))
        answer = answers[min(len(received), len(answers)) - 1]
        return httpx.Response(200, json={"message": {"role": "assistant", **answer}})

    transport = httpx.MockTransport(handle)
    return httpx.AsyncClient(base_url="http://ollama", transport=transport), received


def call(name: str, **arguments) -> dict:
    return {"content": "", "tool_calls": [{"function": {"name": name, "arguments": arguments}}]}


async def test_tool_results_go_back_to_the_model():
    model, received = llm(call("find_slots", day="2030-01-08"), {"content": "Tenho 10:00 e 14:30."})

    async with Client(tools) as mcp:
        messages = await reply(
            [{"role": "user", "content": "Tem horário dia 8?"}], model, "qwen3:4b", mcp, "UTC"
        )

    assert [m["role"] for m in messages] == ["user", "assistant", "tool", "assistant"]
    assert json.loads(messages[2]["content"]) == {"slots": ["10:00", "14:30"]}
    assert received[0]["tools"][0]["function"]["name"] == "find_slots"
    assert received[1]["messages"][-1] == messages[2]
    assert messages[-1]["content"] == "Tenho 10:00 e 14:30."


async def test_a_model_stuck_on_tools_gets_a_way_out():
    model, received = llm(call("find_slots", day="2030-01-08"))

    async with Client(tools) as mcp:
        messages = await reply([{"role": "user", "content": "Oi"}], model, "qwen3:4b", mcp, "UTC")

    assert len(received) == MAX_STEPS
    assert messages[-1]["role"] == "assistant"


async def test_an_unreachable_model_is_reported():
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    model = httpx.AsyncClient(base_url="http://ollama", transport=httpx.MockTransport(down))
    app = create_app(model, "qwen3:4b", lambda: Client(tools))

    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = await client.post(
            "/chat", json={"messages": [{"role": "user", "content": "Oi"}]}
        )

    assert response.status_code == 503

import json
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from mcp import Client
from mcp.types import CallToolResult
from opentelemetry import trace

MAX_STEPS = 8
WEEKDAYS = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]
SYSTEM = """Você é a assistente do VagaCerta, app de agendamento de barbearias, salões, clínicas e
espaços de bem-estar. Use exatamente estas datas (a primeira é hoje):
{days}

- Use as ferramentas para descobrir estabelecimentos, profissionais, serviços e horários. Nunca
  invente ids, horários ou preços.
- Chame as ferramentas que precisar antes de responder: não diga que vai verificar, verifique.
- Para agendar, peça o nome e o e-mail da pessoa e confirme serviço, profissional, dia e horário
  antes de chamar book_appointment.
- Se o dia estiver lotado, ofereça outro dia ou a lista de espera.
- Responda em português do Brasil, em poucas frases. Não mostre ids. Ao agendar, envie o link."""

tracer = trace.get_tracer("assistant")


def system_prompt(today: date) -> str:
    # Modelos pequenos erram a conta de "terça que vem": as datas vão prontas.
    days = (today + timedelta(days=i) for i in range(8))
    return SYSTEM.format(days="\n".join(f"- {WEEKDAYS[d.weekday()]}: {d}" for d in days))


def tool_output(result: CallToolResult) -> str:
    if result.structured_content is not None and not result.is_error:
        return json.dumps(result.structured_content, ensure_ascii=False)
    return "\n".join(block.text for block in result.content if block.type == "text")


async def reply(
    history: list[dict[str, Any]], llm: httpx.AsyncClient, model: str, mcp: Client, timezone: str
) -> list[dict[str, Any]]:
    """Conversa com o modelo até ele responder sem pedir ferramentas; devolve a conversa toda."""
    tools = [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema,
            },
        }
        for t in (await mcp.list_tools()).tools
    ]
    today = datetime.now(ZoneInfo(timezone)).date()
    messages = [{"role": "system", "content": system_prompt(today)}, *history]
    for _ in range(MAX_STEPS):
        with tracer.start_as_current_span(f"chat {model}") as span:
            response = await llm.post(
                "/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "stream": False,
                    "think": False,
                    # 6k tokens cabem uma conversa de agendamento e ainda deixam o modelo numa GPU
                    # de 4 GB; temperatura baixa deixa as chamadas de ferramenta mais previsíveis.
                    "options": {"num_ctx": 6144, "temperature": 0.2},
                },
            )
            response.raise_for_status()
            body = response.json()
            span.set_attributes(
                {
                    "gen_ai.operation.name": "chat",
                    "gen_ai.provider.name": "ollama",
                    "gen_ai.request.model": model,
                    "gen_ai.usage.input_tokens": body.get("prompt_eval_count", 0),
                    "gen_ai.usage.output_tokens": body.get("eval_count", 0),
                }
            )
        message = body["message"]
        messages.append(message)
        if not message.get("tool_calls"):
            return messages[1:]
        for call in message["tool_calls"]:
            name, arguments = call["function"]["name"], call["function"]["arguments"]
            with tracer.start_as_current_span(f"execute_tool {name}") as span:
                span.set_attribute("gen_ai.tool.name", name)
                result = await mcp.call_tool(name, arguments)
            messages.append({"role": "tool", "tool_name": name, "content": tool_output(result)})
    messages.append(
        {"role": "assistant", "content": "Não consegui concluir agora. Pode me dar mais detalhes?"}
    )
    return messages[1:]

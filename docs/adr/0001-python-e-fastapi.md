# ADR 0001 — Python e FastAPI nos serviços

**Status:** aceita

## Contexto

Os serviços passam a maior parte do tempo esperando I/O (HTTP, PostgreSQL, Kafka e RabbitMQ), e o
roadmap prevê recursos de IA (LLM local e servidor MCP) nas próximas fases.

## Decisão

Usar Python 3.13 com FastAPI, SQLAlchemy 2 assíncrono e Pydantic v2, organizados como um único
**workspace do uv**, com um pacote por serviço.

## Consequências

- Assíncrono de ponta a ponta: um processo atende muitas requisições que estão esperando I/O.
- O Pydantic valida toda entrada na borda e gera a documentação OpenAPI automaticamente.
- O ecossistema Python cobre as fases de IA sem introduzir outra linguagem.
- Um único lock file para o repositório; cada serviço ainda gera a própria imagem só com as suas
  dependências (`uv sync --package <serviço>`).

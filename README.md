<h1 align="center">VagaCerta</h1>

<p align="center">
  <strong>O horário certo, sem troca de mensagens.</strong><br />
  Agendamento online para pequenos negócios, construído com microsserviços orientados a eventos.
</p>

<p align="center">
  <a href="https://github.com/dev-matheusfranca/VagaCerta/actions/workflows/ci.yml"><img src="https://github.com/dev-matheusfranca/VagaCerta/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <img src="https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white" alt="Python 3.13" />
  <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Apache%20Kafka-4-231F20?logo=apachekafka&logoColor=white" alt="Apache Kafka 4" />
  <img src="https://img.shields.io/badge/RabbitMQ-4-FF6600?logo=rabbitmq&logoColor=white" alt="RabbitMQ 4" />
  <img src="https://img.shields.io/badge/Keycloak-26-4D4D4D?logo=keycloak&logoColor=white" alt="Keycloak 26" />
  <img src="https://img.shields.io/badge/Traefik-3-24A1C1?logo=traefikproxy&logoColor=white" alt="Traefik 3" />
  <img src="https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL 17" />
  <img src="https://img.shields.io/badge/OpenTelemetry-425CC7?logo=opentelemetry&logoColor=white" alt="OpenTelemetry" />
  <img src="https://img.shields.io/badge/Grafana-F46800?logo=grafana&logoColor=white" alt="Grafana" />
  <img src="https://img.shields.io/badge/Pact-contratos-0B7285" alt="Pact" />
  <img src="https://img.shields.io/badge/Kubernetes-kind%20%2B%20Helm-326CE5?logo=kubernetes&logoColor=white" alt="Kubernetes com kind e Helm" />
  <img src="https://img.shields.io/badge/Ollama-LLM%20local-000000?logo=ollama&logoColor=white" alt="Ollama" />
  <img src="https://img.shields.io/badge/MCP-servidor-6E56CF" alt="Servidor MCP" />
  <img src="https://img.shields.io/badge/Vue-3-4FC08D?logo=vuedotjs&logoColor=white" alt="Vue 3" />
  <img src="https://img.shields.io/badge/licen%C3%A7a-MIT-green" alt="Licença MIT" />
</p>

<p align="center">
  <img src="docs/screenshots/home.png" alt="Página inicial do VagaCerta" width="900" />
</p>

## Sumário

- [Sobre o projeto](#sobre-o-projeto)
- [Funcionalidades](#funcionalidades)
- [Telas](#telas)
- [Arquitetura](#arquitetura)
- [Tecnologias](#tecnologias)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Como rodar](#como-rodar)
- [Roteiro de demonstração](#roteiro-de-demonstração)
- [API](#api)
- [Eventos](#eventos)
- [Observabilidade](#observabilidade)
- [Assistente com IA](#assistente-com-ia)
- [Testes](#testes)
- [Desempenho](#desempenho)
- [Roadmap](#roadmap)
- [Como contribuir](#como-contribuir)
- [Licença](#licença)
- [Autor](#autor)

## Sobre o projeto

Barbearias, salões, clínicas e espaços de bem-estar ainda marcam a maioria dos horários à mão, pelo
WhatsApp. Isso gera três problemas do dia a dia:

1. **Troca de mensagens** só para achar um horário que sirva para os dois lados.
2. **Horário duplicado** quando duas pessoas recebem a promessa da mesma vaga.
3. **Faltas e cadeira vazia** quando alguém esquece ou cancela em cima da hora e ninguém fica sabendo.

O VagaCerta deixa o cliente escolher serviço, profissional e horário em poucos cliques, a qualquer hora.
O sistema **garante que um horário nunca é reservado duas vezes**, mesmo com muita gente tentando ao mesmo
tempo; avisa por e-mail na confirmação, no cancelamento e antes do atendimento; e, quando alguém cancela,
**oferece o horário automaticamente para a próxima pessoa da lista de espera**.

O projeto evolui em fases, até uma arquitetura completa orientada a eventos. Veja o [roadmap](#roadmap).

## Funcionalidades

**Para o cliente**

- Lista de estabelecimentos com serviços (duração e preço) e profissionais.
- Disponibilidade em tempo real, calculada a partir do expediente de cada profissional.
- Agendamento sem conflito, mesmo sob concorrência; cancelamento que libera o horário na hora.
- E-mails de confirmação, cancelamento e lembrete (24 h antes, ou 2 h para quem agendou em cima da hora).
- **Lista de espera:** em dia lotado, o cliente entra na fila; se alguém cancelar, o horário fica
  reservado para ele por 15 minutos e chega um e-mail com o botão "Quero esse horário".
- **Assistente:** o cliente agenda conversando ("quero cortar o cabelo na terça à tarde"). O assistente
  procura os horários e agenda, com um modelo de IA que roda localmente.

**Para o estabelecimento**

- **Painel com login** (Keycloak): agenda do dia por profissional, totais, reservas da lista de espera e
  cancelamento com um clique, que já repassa a vaga para a fila.
- **Próximos 14 dias:** agendamentos confirmados, cancelamentos, receita prevista, ocupação da agenda e
  quanto a lista de espera recuperou, dia a dia.
- **Comparecimento:** depois do horário, o dono marca se a pessoa veio ou faltou. O painel mostra os
  últimos 30 dias: atendimentos, taxa de faltas, ocupação média e um mapa dos horários mais procurados.

**Por baixo**

- Microsserviços com banco próprio, eventos no Kafka com outbox transacional e e-mails no RabbitMQ com
  retry e dead-letter queue.
- API gateway com rate limit, autenticação OIDC, tokens de serviço entre microsserviços.
- Serviço de Analytics com CQRS: read models montados a partir dos eventos.
- Traces, métricas e logs com OpenTelemetry e Grafana: um cancelamento vira um único trace, do clique ao
  e-mail.
- Testes de contrato com Pact entre todos os serviços, inclusive nos eventos do Kafka.
- Servidor MCP com as ferramentas de agendamento, usado pelo assistente e por qualquer cliente MCP.
- Kubernetes com Helm e kind: o CI sobe o sistema inteiro num cluster e roda o teste de carga nele.
- Resiliência: novas tentativas e circuit breaker entre serviços. O Booking continua respondendo com o
  Catalog fora do ar, e os eventos esperam no outbox enquanto o Kafka está fora.
- Segurança na esteira: gitleaks antes de cada commit, Trivy nas imagens, dependências e chart, e imagens
  que rodam sem root.
- Teste de carga no CI e documentação interativa (OpenAPI/Swagger) em todos os serviços.

## Telas

| Escolha de serviço, profissional e horário | Agendamento confirmado |
|---|---|
| <img src="docs/screenshots/business.png" alt="Página do estabelecimento com serviços, profissionais e horários" /> | <img src="docs/screenshots/booking.png" alt="Página do agendamento confirmado" /> |

| Oferta da lista de espera | Painel do estabelecimento |
|---|---|
| <img src="docs/screenshots/offer.png" alt="Oferta de vaga com contagem regressiva" /> | <img src="docs/screenshots/painel.png" alt="Painel com a agenda do dia por profissional" /> |

| Painel: próximos 14 dias (Analytics) |
|---|
| <img src="docs/screenshots/painel-analytics.png" alt="Painel com agendamentos, cancelamentos, receita, ocupação e recuperação pela fila nos próximos 14 dias" /> |

| Painel: últimos 30 dias (faltas, ocupação e horários de pico) |
|---|
| <img src="docs/screenshots/painel-30-dias.png" alt="Painel com atendimentos, faltas, ocupação média e mapa de calor dos horários mais procurados" /> |

| E-mail de confirmação | E-mail da lista de espera | Login (Keycloak com tema próprio) |
|---|---|---|
| <img src="docs/screenshots/email.png" alt="E-mail de confirmação" /> | <img src="docs/screenshots/offer-email.png" alt="E-mail de vaga liberada" /> | <img src="docs/screenshots/login.png" alt="Tela de login" /> |

## Arquitetura

```mermaid
flowchart LR
    client((Cliente)) --> gateway
    owner((Dono)) --> gateway
    gateway["API Gateway<br/>Traefik"] --> web["Web<br/>Vue 3"]
    gateway -->|/auth| keycloak["Keycloak"]
    gateway -->|/api/catalog| catalog["Catalog"]
    gateway -->|/api/booking| booking["Booking"]
    gateway -->|/api/waitlist| waitlist["Waitlist"]
    gateway -->|/api/analytics| analytics["Analytics"]
    gateway -->|/api/assistant| assistant["Assistant"]
    gateway -->|/mcp| mcp["MCP server"]
    assistant -->|MCP| mcp
    assistant -->|LLM| ollama["Ollama"]
    mcp -->|REST| catalog & booking & waitlist
    booking -->|REST + cache| catalog
    waitlist -->|"REST + token de serviço"| booking
    booking -.->|outbox| relay["Outbox relay"]
    relay -->|booking.events| kafka{{Kafka}}
    kafka --> worker["Waitlist worker"]
    worker -->|waitlist.events| kafka
    kafka --> notification["Notification"]
    kafka --> projector["Analytics worker"]
    projector -.->|read models| analytics
    notification <-->|tarefas de e-mail| rabbitmq{{RabbitMQ}}
    notification -->|SMTP| mailpit["Mailpit"]
```

Cada serviço tem o próprio banco PostgreSQL, e todos os processos enviam traces, métricas e logs para o
Grafana LGTM (omitidos no diagrama).

| Componente | Responsabilidade |
|---|---|
| **gateway** | Ponto único de entrada: roteamento, rate limit e cabeçalhos de segurança |
| **catalog** | Estabelecimentos, profissionais, serviços e expediente semanal |
| **booking** | Disponibilidade, agendamentos, reservas temporárias e agenda do dono; publica eventos via outbox |
| **booking-relay** | Publica no Kafka os eventos gravados no outbox do Booking |
| **waitlist** | Fila de espera, ofertas e confirmação (API) |
| **waitlist-worker** | Orquestra a saga: consome cancelamentos, reserva horários, expira ofertas e publica eventos |
| **notification** | Consome eventos, agenda lembretes e envia e-mails pelo RabbitMQ |
| **analytics** | Números do painel por dia (API só de leitura) |
| **analytics-worker** | Projeta os eventos de agendamento e da lista de espera nos read models |
| **mcp-server** | Ferramentas MCP de agendamento: estabelecimentos, horários, agendar, lista de espera e cancelar |
| **assistant** | Agente que conversa com o modelo e executa as ferramentas MCP que ele pede |
| **ollama** | Roda o modelo de linguagem localmente (perfil `ai` do Compose) |
| **keycloak** | Identidade: login do dono (PKCE), conta de serviço do Waitlist, papéis e grupos |
| **lgtm** | OpenTelemetry Collector, Tempo, Prometheus, Loki e Grafana num só container |
| **web** | Front-end do cliente e do estabelecimento |

### Lista de espera: a saga

```mermaid
sequenceDiagram
    participant D as Dono ou cliente
    participant B as Booking
    participant K as Kafka
    participant W as Waitlist
    participant N as Notification
    participant P as Próximo da fila
    D->>B: cancela um agendamento
    B->>K: booking.cancelled (com o horário liberado)
    K->>W: booking.cancelled
    W->>B: POST /holds (token de serviço)
    B-->>W: horário reservado por 15 min
    W->>K: waitlist.offer_created
    K->>N: waitlist.offer_created
    N->>P: e-mail "Uma vaga abriu"
    alt confirma a tempo
        P->>W: POST /offers/{id}/claim
        W->>B: POST /bookings/{id}/confirm
        B->>K: booking.created
        K->>N: e-mail de confirmação
    else a oferta expira
        W->>B: POST /bookings/{id}/release (compensação)
        W->>B: POST /holds para o próximo da fila
    end
```

### Decisões de arquitetura

- **Banco por serviço.** Cada serviço é dono do seu schema e das suas migrações; eles só conversam por API
  e eventos.
- **Conflito resolvido no banco.** Uma exclusion constraint do PostgreSQL rejeita horários sobrepostos;
  quem chega depois recebe `409 Conflict`.
- **Outbox transacional.** Mudança e evento são gravados na mesma transação: sem escrita dupla.
- **Kafka para fatos, RabbitMQ para tarefas.** Eventos de domínio ficam num log reprocessável; e-mails são
  tarefas com retry e dead-letter.
- **Consumidores idempotentes.** Cada evento processado é registrado; reentregas não repetem efeitos.
- **Saga orquestrada com compensação.** A lista de espera reserva o horário antes de oferecê-lo e o libera
  se a oferta expirar.
- **Zero trust.** Todo serviço valida o JWT (assinatura, emissor, audiência, papéis); o Waitlist chama o
  Booking com token próprio de serviço.
- **Domínio sem framework.** Regras de disponibilidade e de lembrete são funções puras; um teste de
  arquitetura impede que importem frameworks ou brokers.
- **Otimização guiada por medição.** Um teste de carga apontou o gargalo e um cache curto do catálogo
  triplicou a vazão.
- **Trace que atravessa o outbox.** O contexto do trace é gravado junto com o evento e restaurado pelo
  relay, então um cancelamento aparece inteiro num só trace, mesmo passando por Kafka e RabbitMQ.
- **CQRS.** O painel lê read models próprios do Analytics, atualizados pelos eventos, sem consultar os
  serviços de escrita.
- **Contratos dirigidos pelo consumidor.** Cada consumidor declara o que usa de uma API ou de um evento, e
  o provedor verifica esses contratos na própria suíte.
- **IA que age por ferramentas.** O modelo só agenda pelas ferramentas do servidor MCP, que chamam as
  mesmas APIs do site. Ele não inventa horários e não passa por cima da regra de conflito do banco.
- **O mesmo sistema no Compose e no Kubernetes.** As configurações viram imagens, e um chart Helm
  genérico descreve todos os serviços.
- **Falhar bem.** Consultas entre serviços são repetidas e um circuit breaker para de chamar quem não
  responde. Na falta de uma dependência, a resposta é um `503` claro ou um dado em cache, nunca um `500`.
- **Segurança desde o commit.** Segredos são barrados antes do commit, e uma vulnerabilidade alta com
  correção numa imagem própria quebra o build.

Cada decisão está registrada numa ADR:

| ADR | Decisão |
|---|---|
| [0001](docs/adr/0001-python-e-fastapi.md) | Python e FastAPI nos serviços |
| [0002](docs/adr/0002-conflito-de-horario-resolvido-no-banco.md) | O banco impede o conflito de horário |
| [0003](docs/adr/0003-outbox-transacional.md) | Outbox transacional para os eventos |
| [0004](docs/adr/0004-kafka-para-eventos-rabbitmq-para-tarefas.md) | Kafka para eventos, RabbitMQ para tarefas de e-mail |
| [0005](docs/adr/0005-lista-de-espera-como-saga.md) | Lista de espera como saga orquestrada com reservas temporárias |
| [0006](docs/adr/0006-keycloak-e-api-gateway.md) | Keycloak para identidade e Traefik como API gateway |
| [0007](docs/adr/0007-cache-do-catalogo.md) | Cache curto do catálogo no Booking |
| [0008](docs/adr/0008-observabilidade-com-opentelemetry.md) | Observabilidade com OpenTelemetry e a stack LGTM |
| [0009](docs/adr/0009-analytics-com-cqrs.md) | Serviço Analytics com CQRS |
| [0010](docs/adr/0010-testes-de-contrato-com-pact.md) | Testes de contrato com Pact |
| [0011](docs/adr/0011-assistente-com-llm-local-e-mcp.md) | Assistente com LLM local e servidor MCP |
| [0012](docs/adr/0012-kubernetes-com-kind-e-helm.md) | Kubernetes com kind e Helm |
| [0013](docs/adr/0013-resiliencia-entre-servicos.md) | Resiliência entre serviços |
| [0014](docs/adr/0014-qualidade-e-seguranca-na-esteira.md) | Qualidade e segurança na esteira |
| [0015](docs/adr/0015-comparecimento-faltas-e-ocupacao.md) | Comparecimento, faltas e ocupação |

## Tecnologias

| Camada | Tecnologias |
|---|---|
| Serviços | Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2 (assíncrono), asyncpg, Alembic |
| Mensageria | Apache Kafka 4 (KRaft) com aiokafka, RabbitMQ 4 com aio-pika |
| Identidade | Keycloak 26 (OIDC, PKCE, client credentials), PyJWT, keycloak-js |
| Gateway | Traefik 3 (roteamento, rate limit, cabeçalhos de segurança) |
| E-mail | aiosmtplib, templates HTML, Mailpit para entrega local |
| Banco de dados | PostgreSQL 17 (exclusion constraint com `btree_gist`, JSONB) |
| Observabilidade | OpenTelemetry (instrumentação automática e manual), Grafana, Tempo, Prometheus e Loki (`grafana/otel-lgtm`) |
| IA | Ollama (`qwen3:4b-instruct` por padrão), Model Context Protocol (SDK oficial em Python), atributos GenAI do OpenTelemetry |
| Front-end | Vue 3, TypeScript, Vite, Tailwind CSS 4, Vue Router, ícones Lucide |
| Testes | pytest, Testcontainers (PostgreSQL, Kafka, RabbitMQ), Pact, Hypothesis, Toxiproxy, WireMock, import-linter, k6, pytest-cov |
| Qualidade e segurança | ruff, mypy (strict), vue-tsc, pre-commit, gitleaks, Trivy, SonarCloud |
| Infraestrutura | Docker, Docker Compose, Kubernetes (kind), Helm, nginx, Kafka UI, GitHub Actions |
| Ferramentas | Workspace do uv (um lock file para todos os serviços Python) |

## Estrutura do projeto

```
VagaCerta/
├── services/
│   ├── Dockerfile              # imagem compartilhada dos serviços Python
│   ├── catalog/                # estabelecimentos, profissionais e serviços
│   ├── booking/                # disponibilidade, agendamentos, reservas, outbox e relay
│   ├── waitlist/               # lista de espera, ofertas e worker da saga
│   ├── analytics/              # read models do painel e worker que projeta os eventos
│   ├── mcp-server/             # ferramentas MCP de agendamento
│   ├── assistant/              # agente que conversa com o modelo no Ollama
│   └── notification/           # consumidor de eventos, lembretes, e-mails e worker do RabbitMQ
│       ├── migrations/         # (em cada serviço) migrações do Alembic
│       ├── src/                # (em cada serviço) código do serviço
│       └── tests/              # (em cada serviço) testes
├── libs/auth/                  # vagacerta-auth: validação dos tokens do Keycloak, usada pelos serviços
├── libs/http/                  # vagacerta-http: novas tentativas e circuit breaker entre serviços
├── pacts/                      # contratos gerados pelos consumidores e verificados pelos provedores
├── deploy/
│   ├── helm/vagacerta/         # chart Helm com todos os serviços
│   └── kind/                   # cluster kind e script de subida
├── web/                        # front-end em Vue 3, servido por nginx no Docker
├── gateway/dynamic.yml         # rotas e middlewares do Traefik
├── keycloak/                   # realm versionado e tema da tela de login
├── observability/              # dashboard do Grafana provisionado na subida
├── load/booking.js             # teste de carga com k6
├── docs/
│   ├── adr/                    # registros de decisões de arquitetura
│   └── screenshots/
├── .github/workflows/ci.yml    # lint, tipos, testes, build e teste de carga a cada push
├── docker-compose.yml
├── CHANGELOG.md
└── pyproject.toml              # workspace do uv e configuração das ferramentas
```

## Como rodar

### Pré-requisitos

| Ferramenta | Versão | Para quê |
|---|---|---|
| [Docker](https://docs.docker.com/get-docker/) com Compose | 24+ | Rodar tudo e os testes de integração |
| [uv](https://docs.astral.sh/uv/) | 0.13+ | Desenvolver os serviços localmente |
| [Node.js](https://nodejs.org/) | 24+ | Desenvolver o front-end localmente |
| [Ollama](https://ollama.com/) | 0.40+ | Opcional: rodar o modelo do assistente na sua GPU |
| [kind](https://kind.sigs.k8s.io/) e [Helm](https://helm.sh/) | 0.33+ e 4+ | Opcional: rodar no Kubernetes |

### Com Docker (recomendado)

```bash
git clone git@github.com:dev-matheusfranca/VagaCerta.git
cd VagaCerta
docker compose up --build
```

Na primeira vez, a subida leva alguns minutos (imagens e Keycloak). As migrações rodam sozinhas, e os
dados de exemplo são criados: quatro estabelecimentos e um dia lotado na Clínica Sorriso Pleno.

| Endereço | O que é |
|---|---|
| http://localhost:8080 | App (tudo passa pelo gateway) |
| http://localhost:8080/painel | Painel do estabelecimento |
| http://localhost:8080/assistente | Assistente (com o perfil `ai`) |
| http://localhost:8080/mcp | Servidor MCP, para qualquer cliente MCP |
| http://localhost:8025 | Mailpit: todos os e-mails enviados |
| http://localhost:3000 | Grafana: dashboard do VagaCerta, traces, métricas e logs |
| http://localhost:8090 | Kafka UI: tópicos `booking.events` e `waitlist.events` |
| http://localhost:15672 | RabbitMQ: filas de e-mail, retry e dead-letter (`guest` / `guest`) |
| http://localhost:8081 | Dashboard do Traefik |
| http://localhost:8080/auth/admin | Console do Keycloak (`admin` / `admin`) |
| http://localhost:8001/docs · :8002 · :8003 · :8004 · :8006 | Swagger do Catalog, Booking, Waitlist, Analytics e Assistant |

**Usuários de demonstração** (senha `vagacerta`):

| Usuário | Papel |
|---|---|
| `clinica` | Dona da Clínica Sorriso Pleno |
| `barbearia` | Dono da Barbearia Navalha de Ouro |
| `admin` | Administrador do catálogo |

> As credenciais e o segredo do cliente de serviço são de demonstração e ficam no realm versionado. Num
> ambiente real, viriam de um cofre de segredos.

### Com o assistente de IA

O assistente e o Ollama ficam no perfil `ai`. Na primeira subida, o modelo (cerca de 2,5 GB) é baixado:

```bash
docker compose --profile ai up --build
```

Com o Ollama instalado na máquina, o modelo roda direto na sua GPU. Nesse caso, suba só o assistente
apontando para ele:

```bash
ollama pull qwen3:4b-instruct
OLLAMA_URL=http://host.docker.internal:11434 docker compose up --build assistant
```

Em GPUs com pouca memória, `OLLAMA_FLASH_ATTENTION=1` e `OLLAMA_KV_CACHE_TYPE=q8_0` nas variáveis de
ambiente do Ollama reduzem pela metade a memória do cache de contexto. Outro modelo com suporte a
ferramentas pode ser usado com `OLLAMA_MODEL`.

### No Kubernetes (kind + Helm)

O script cria um cluster kind, constrói as imagens, carrega no nó e instala o chart. O gateway, o
Grafana e o Mailpit ficam nas mesmas portas do Compose, então pare o Compose antes:

```bash
docker compose stop
deploy/kind/up.sh                  # WITH_ASSISTANT=1 deploy/kind/up.sh inclui o assistente
kubectl get pods
```

Rodar o script de novo atualiza o cluster com as imagens novas. Para remover tudo:
`kind delete cluster --name vagacerta`.

No cluster, o assistente usa o Ollama da máquina em `http://host.docker.internal:11434`, endereço que
funciona no Docker Desktop. No Docker do Linux, troque o endereço com
`--set workloads.assistant.env.OLLAMA_URL=http://<ip-do-host>:11434`.

### Localmente, sem containers para os serviços

Suba só a infraestrutura com Docker e rode cada processo num terminal:

```bash
docker compose up -d catalog-db booking-db waitlist-db notification-db analytics-db kafka rabbitmq mailpit keycloak
uv sync

(cd services/catalog && uv run alembic upgrade head && uv run python -m catalog.seed)
(cd services/booking && uv run alembic upgrade head)
(cd services/waitlist && uv run alembic upgrade head)
(cd services/notification && uv run alembic upgrade head)
(cd services/analytics && uv run alembic upgrade head)

uv run uvicorn catalog.main:app --port 8001 --reload
uv run uvicorn booking.main:app --port 8002 --reload
uv run uvicorn waitlist.main:app --port 8003 --reload
uv run uvicorn analytics.main:app --port 8004 --reload
uv run uvicorn mcp_server.main:app --port 8005 --reload
uv run uvicorn assistant.main:app --port 8006 --reload
uv run python -m booking.outbox_relay
uv run python -m waitlist.worker
uv run python -m analytics.worker
uv run python -m notification

npm --prefix web install
npm --prefix web run dev
```

O front roda em http://localhost:5173 e encaminha `/api/*` para os serviços.

Para ver a telemetria rodando localmente, suba também o `lgtm` e troque `uv run` por
`uv run opentelemetry-instrument` com as variáveis `OTEL_*` do bloco `x-otel` do
[`docker-compose.yml`](docker-compose.yml), apontando para `http://localhost:4318`.

### Variáveis de ambiente

| Serviço | Variável | Padrão |
|---|---|---|
| catalog | `DATABASE_URL` | `postgresql+asyncpg://vagacerta:vagacerta@localhost:5433/catalog` |
| catalog, booking, analytics | `KEYCLOAK_ISSUER` | `http://localhost:8080/auth/realms/vagacerta` |
| catalog, booking, analytics | `KEYCLOAK_JWKS_URL` | `<KEYCLOAK_ISSUER>/protocol/openid-connect/certs` |
| booking | `DATABASE_URL` | `postgresql+asyncpg://vagacerta:vagacerta@localhost:5434/booking` |
| booking | `CATALOG_URL` | `http://localhost:8001` |
| booking relay | `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9094` |
| waitlist | `DATABASE_URL` | `postgresql+asyncpg://vagacerta:vagacerta@localhost:5436/waitlist` |
| waitlist | `CATALOG_URL` / `BOOKING_URL` | `http://localhost:8001` / `http://localhost:8002` |
| waitlist | `KEYCLOAK_TOKEN_URL` | `http://localhost:8080/auth/realms/vagacerta/protocol/openid-connect/token` |
| waitlist | `CLIENT_ID` / `CLIENT_SECRET` | `waitlist-service` / `waitlist-dev-secret` |
| waitlist | `OFFER_MINUTES` | `15` |
| notification | `DATABASE_URL` | `postgresql+asyncpg://vagacerta:vagacerta@localhost:5435/notification` |
| notification | `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` |
| notification | `SMTP_HOST` / `SMTP_PORT` | `localhost` / `1025` |
| notification | `WEB_URL` | `http://localhost:8080` (usada nos links dos e-mails) |
| analytics | `DATABASE_URL` | `postgresql+asyncpg://vagacerta:vagacerta@localhost:5437/analytics` |
| mcp-server | `CATALOG_URL` / `BOOKING_URL` / `WAITLIST_URL` | `http://localhost:8001` / `:8002` / `:8003` |
| mcp-server | `WEB_URL` | `http://localhost:8080` (usada nos links dos agendamentos) |
| assistant | `OLLAMA_URL` / `OLLAMA_MODEL` | `http://localhost:11434` / `qwen3:4b-instruct` |
| assistant | `MCP_URL` / `TIMEZONE` | `http://localhost:8005/mcp` / `America/Sao_Paulo` |
| relay, waitlist, notification, analytics | `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9094` |
| todos | `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT` e demais `OTEL_*` | definidas no `docker-compose.yml` |

## Roteiro de demonstração

Com a stack no ar (`docker compose up --build`):

1. **Agende um horário.** Em http://localhost:8080, escolha um estabelecimento, serviço, profissional e
   horário. O e-mail de confirmação aparece no [Mailpit](http://localhost:8025).
2. **Entre na lista de espera.** Abra a Clínica Sorriso Pleno, escolha a Dra. Fernanda Lima e o próximo
   dia útil: ele está lotado. Entre na fila com um e-mail qualquer.
3. **Cancele como dono.** Em http://localhost:8080/painel, entre com `clinica` / `vagacerta`, vá até esse
   dia e cancele um horário.
4. **Receba a oferta.** No Mailpit chega "Uma vaga abriu". O botão "Quero esse horário" abre a oferta
   com contagem regressiva; ao confirmar, o agendamento é criado e chega o e-mail de confirmação. No
   painel, enquanto a oferta está aberta, o horário aparece como "Oferta da fila".
5. **Veja os números.** No painel, "Próximos 14 dias" já mostra o cancelamento e o horário recuperado
   pela fila, com o valor que voltou para a agenda.
6. **Siga o cancelamento.** No [Grafana](http://localhost:3000), o dashboard **VagaCerta** lista os traces
   recentes. O do `POST /bookings/{booking_id}/cancel` mostra o caminho inteiro: Booking, relay, Kafka,
   worker da saga, reserva no Booking, Notification, RabbitMQ e o envio do e-mail.
7. **Veja os bastidores.** Os eventos no [Kafka UI](http://localhost:8090) e as filas no
   [RabbitMQ](http://localhost:15672).
8. **Agende conversando.** Com o perfil `ai`, abra http://localhost:8080/assistente e peça, por exemplo,
   "quero cortar o cabelo na barbearia na terça à tarde". Entre as mensagens aparecem as ferramentas que o
   modelo usou, e o trace do `POST /chat` no Grafana mostra cada chamada ao modelo com os tokens gastos.

## API

A documentação interativa completa fica em `/docs` em cada serviço.

### Catalog — `:8001` · `/api/catalog`

| Método | Endpoint | Acesso | Descrição |
|---|---|---|---|
| `GET` | `/businesses` | público | Lista os estabelecimentos |
| `GET` | `/businesses/{id}` | público | Estabelecimento com profissionais, expediente e serviços |
| `POST` | `/businesses` | `admin` | Cria um estabelecimento |
| `POST` | `/businesses/{id}/professionals` | `admin` | Adiciona um profissional com o expediente semanal |
| `POST` | `/businesses/{id}/services` | `admin` | Adiciona um serviço com duração e preço |

### Booking — `:8002` · `/api/booking`

| Método | Endpoint | Acesso | Descrição |
|---|---|---|---|
| `GET` | `/availability` | público | Horários livres de um profissional, serviço e dia |
| `POST` | `/bookings` | público | Agenda um horário |
| `GET` | `/bookings/{id}` | público | Detalhes do agendamento |
| `POST` | `/bookings/{id}/cancel` | público | Cancela; o horário volta a ficar livre |
| `POST` | `/bookings/{id}/outcome` | `owner` do estabelecimento | Registra, depois do horário, se a pessoa compareceu ou faltou |
| `GET` | `/businesses/{id}/agenda?date=` | `owner` do estabelecimento | Agenda do dia, com reservas da lista de espera |
| `POST` | `/holds` | `booking-holds` | Reserva temporária de um horário (saga) |
| `POST` | `/bookings/{id}/confirm` | `booking-holds` | Transforma a reserva em agendamento |
| `POST` | `/bookings/{id}/release` | `booking-holds` | Libera a reserva (compensação) |

### Waitlist — `:8003` · `/api/waitlist`

| Método | Endpoint | Acesso | Descrição |
|---|---|---|---|
| `POST` | `/entries` | público | Entra na lista de espera de um dia; responde a posição na fila |
| `GET` | `/offers/{id}` | link do e-mail | Detalhes da oferta |
| `POST` | `/offers/{id}/claim` | link do e-mail | Confirma a oferta antes de expirar |

### Analytics — `:8004` · `/api/analytics`

| Método | Endpoint | Acesso | Descrição |
|---|---|---|---|
| `GET` | `/businesses/{id}/stats?from=&to=` | `owner` do estabelecimento | Por dia: agendamentos, cancelamentos, receita, comparecimentos, faltas, minutos agendados, capacidade e ofertas da lista de espera |
| `GET` | `/businesses/{id}/peak-hours` | `owner` do estabelecimento | Agendamentos por dia da semana e hora |

### Assistant — `:8006` · `/api/assistant`

| Método | Endpoint | Acesso | Descrição |
|---|---|---|---|
| `POST` | `/chat` | público | Recebe a conversa e devolve a conversa com a resposta e as ferramentas usadas |

### MCP server — `:8005` · `/mcp`

Streamable HTTP, sem estado. Ferramentas:

| Ferramenta | O que faz |
|---|---|
| `list_businesses` | Lista os estabelecimentos com id, nome, categoria e endereço |
| `get_business` | Profissionais e serviços (duração e preço) de um estabelecimento |
| `find_slots` | Horários livres de um profissional para um serviço num dia, no fuso do estabelecimento |
| `book_appointment` | Agenda um horário e devolve o link do agendamento |
| `join_waitlist` | Põe a pessoa na fila de um dia lotado |
| `cancel_booking` | Cancela um agendamento confirmado |

Exemplo:

```bash
curl -X POST http://localhost:8080/api/booking/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "6384a99a-146a-4b11-8e9b-db99b79e8fd2",
    "professional_id": "<id do profissional>",
    "service_id": "<id do serviço>",
    "starts_at": "2026-10-27T10:00:00-03:00",
    "customer_name": "Maria Silva",
    "customer_email": "maria@example.com"
  }'
```

| Status | Significado |
|---|---|
| `201 Created` | Horário agendado |
| `401` / `403` | Sem token, token inválido ou sem o papel necessário |
| `404 Not Found` | Estabelecimento, profissional ou serviço inexistente |
| `409 Conflict` | O horário acabou de ser reservado por outra pessoa |
| `422 Unprocessable Entity` | Dados inválidos, horário fora do expediente ou no passado |
| `429 Too Many Requests` | Limite de gravações por cliente atingido (gateway) |

Para chamar os endpoints protegidos, gere um token com um usuário de demonstração:

```bash
curl -s http://localhost:8080/auth/realms/vagacerta/protocol/openid-connect/token \
  -d grant_type=password -d client_id=vagacerta-web -d username=admin -d password=vagacerta
```

## Eventos

| Tópico | Tipo | Publicado quando | Consumido por |
|---|---|---|---|
| `booking.events` | `booking.created` | Um agendamento é confirmado | Notification, Analytics |
| `booking.events` | `booking.cancelled` | Um agendamento confirmado é cancelado | Waitlist worker, Notification, Analytics |
| `booking.events` | `booking.completed` | O dono registra que a pessoa compareceu | Analytics |
| `booking.events` | `booking.no_show` | O dono registra que a pessoa faltou | Analytics |
| `waitlist.events` | `waitlist.offer_created` | Um horário é reservado para alguém da fila | Notification, Analytics |
| `waitlist.events` | `waitlist.offer_claimed` | A pessoa da fila confirma a oferta | Analytics |
| `waitlist.events` | `waitlist.offer_expired` | A oferta expira sem confirmação | Analytics |

`booking.created` traz horário, cliente, estabelecimento, profissional, serviço e preço;
`booking.cancelled`, o horário liberado; os eventos da lista de espera, os dados da oferta e o prazo. O
formato que cada consumidor usa está nos contratos em [`pacts/`](pacts).

As mensagens usam o id do agendamento (ou da oferta) como chave, então os eventos de um mesmo agendamento
chegam em ordem.

```json
{
  "event_id": "151a457a-5276-4a3f-896f-dd56508a0fb9",
  "type": "booking.created",
  "occurred_at": "2026-10-23T19:40:28.283996+00:00",
  "data": {
    "booking_id": "80be9d06-b39a-4212-963b-882a7a4ef6a0",
    "business_id": "6384a99a-146a-4b11-8e9b-db99b79e8fd2",
    "starts_at": "2026-10-24T10:00:00-03:00",
    "ends_at": "2026-10-24T10:30:00-03:00",
    "customer_name": "Ana Teste",
    "customer_email": "ana@example.com",
    "business_name": "Barbearia Navalha de Ouro",
    "business_address": "Av. Brasil, 1200 · Zona 01, Maringá/PR",
    "timezone": "America/Sao_Paulo",
    "professional_name": "Diego Almeida",
    "service_name": "Barba completa",
    "price_cents": 3500
  }
}
```

## Observabilidade

Todos os processos rodam com a instrumentação automática do OpenTelemetry e mandam traces, métricas e
logs para o container `grafana/otel-lgtm`. O Grafana sobe em http://localhost:3000 com o dashboard
**VagaCerta** já provisionado.

| Sinal | O que mostra |
|---|---|
| Traces (Tempo) | Cada requisição com as queries, as chamadas HTTP e as mensagens. O contexto passa pelo outbox e pelos cabeçalhos do Kafka e do RabbitMQ, então um cancelamento é um único trace de quatro serviços |
| Métricas (Prometheus) | Requisições por segundo, p95 e erros 5xx por serviço; agendamentos criados e cancelados, ofertas da fila por resultado e e-mails enviados, repetidos ou na dead-letter |
| Logs (Loki) | Os logs de todos os serviços, cada um ligado ao trace e ao span em que foi escrito |

| Dashboard | Um cancelamento, do clique ao e-mail |
|---|---|
| <img src="docs/screenshots/grafana-dashboard.png" alt="Dashboard do VagaCerta no Grafana com métricas de negócio e dos serviços" /> | <img src="docs/screenshots/grafana-trace.png" alt="Trace de um cancelamento atravessando Booking, relay, Waitlist e Notification" /> |

## Assistente com IA

```mermaid
sequenceDiagram
    participant P as Pessoa
    participant A as Assistant
    participant O as Ollama
    participant M as MCP server
    participant B as Booking
    P->>A: "quero cortar o cabelo na terça à tarde"
    A->>M: lista as ferramentas
    A->>O: conversa + ferramentas
    O-->>A: chama find_slots
    A->>M: find_slots
    M->>B: GET /availability
    B-->>M: horários em UTC
    M-->>A: horários no fuso da barbearia
    A->>O: resultado da ferramenta
    O-->>A: "tenho 14:00 e 15:30, qual prefere?"
    A-->>P: resposta e passos usados
```

O assistente não conhece regras de negócio: ele repassa ao modelo as ferramentas do servidor MCP e
executa as que o modelo pedir, até o modelo responder sem chamar nenhuma (no máximo 8 passos). O modelo
recebe as datas dos próximos dias já calculadas, porque modelos pequenos erram a conta de "terça que
vem", e a instrução de confirmar os dados antes de agendar. A conversa fica no navegador, e o serviço não
guarda estado.

<p align="center">
  <img src="docs/screenshots/assistente.png" alt="Conversa real com o assistente: ele consulta estabelecimentos, serviços e horários, confirma os dados e agenda" width="560" />
</p>

Conversa real, com o `qwen3:4b-instruct` rodando localmente. Numa GTX 1650 (4 GB), com contexto de 6 mil
tokens e as variáveis de ambiente acima, cerca de 70% do modelo fica na GPU: cada chamada ao modelo leva
de 5 a 20 segundos, e uma resposta que consulta várias ferramentas leva perto de 1 minuto. Em testes
repetidos com três pedidos diferentes, o modelo começou pela ferramenta certa em 27 de 27 vezes.

O servidor MCP também atende outros clientes. Para explorar as ferramentas com o MCP Inspector:

```bash
npx @modelcontextprotocol/inspector
```

Conecte em `http://localhost:8080/mcp` com o transporte Streamable HTTP.

## Testes

```bash
uv run pytest --cov      # 106 testes, com cobertura (os de integração sobem containers com Docker)
uv run lint-imports      # regras de arquitetura
uv run mypy libs/*/src services/*/src
uv run pre-commit run --all-files               # ruff, checagens de arquivos e gitleaks
npm --prefix web run build                      # checa os tipos do front-end
docker compose --profile load run --rm k6       # teste de carga contra a stack no ar
helm lint deploy/helm/vagacerta                 # valida o chart
```

| Tipo | O que prova |
|---|---|
| Unitário | Regras de disponibilidade e de lembrete; conteúdo dos e-mails, fuso horário e escape de HTML |
| Baseado em propriedades | O Hypothesis gera agendas aleatórias: nenhum horário oferecido sobrepõe outro ou sai do expediente |
| Integração | API com PostgreSQL real via Testcontainers, usando as migrações de verdade |
| Concorrência | 40 requisições simultâneas para o mesmo horário: exatamente um `201` e 39 `409`, sem deadlock no banco |
| Outbox | O evento só existe se o agendamento foi gravado; o relay publica cada um uma vez, em ordem, num Kafka real |
| Mensageria | Num RabbitMQ real: e-mails entregues, repetidos com backoff e enviados à dead-letter após a última tentativa |
| Idempotência | Evento reentregue não gera segundo e-mail nem segunda oferta; lembrete sai uma vez só |
| Saga | Oferta ao primeiro da fila, pulo de quem não cabe no horário, confirmação e compensação por expiração |
| Projeções (CQRS) | Os read models do Analytics somam os eventos certos e ignoram reentregas |
| Contrato (Pact) | Cada consumidor declara o que usa das APIs e dos eventos; Catalog, Booking e Waitlist verificam esses contratos contra o código real |
| Rastreamento | O evento gravado no outbox leva o contexto do trace da requisição |
| Ferramentas MCP | Num cliente MCP em memória: horários no fuso do estabelecimento e erros esperados como mensagem para o modelo |
| Agente | Com um modelo falso: o resultado das ferramentas volta para o modelo, o loop para após 8 passos e um modelo fora do ar vira `503` |
| Kubernetes | O CI sobe tudo num cluster kind com o chart Helm e roda o teste de carga contra ele |
| Resiliência | O Toxiproxy injeta latência e queda entre o Booking e um Catalog simulado pelo WireMock: o circuito abre e o cache segura a disponibilidade. Com o Kafka pausado, o relay espera e publica tudo, em ordem, quando ele volta |
| Segurança | Trivy nas imagens próprias (falha com vulnerabilidade alta ou crítica corrigível), nas dependências e na configuração; gitleaks contra segredos |
| Segurança | Tokens RS256 assinados no teste: sem token `401`, papel errado `403`, token forjado `401`, dono de outro estabelecimento `403` |
| Arquitetura | Os módulos de domínio não dependem de frameworks nem de brokers |
| Carga (k6) | 50 pessoas disputam o mesmo horário: só uma consegue; a disponibilidade mantém p95 abaixo de 500 ms |

### Testes de contrato

Os contratos ficam em [`pacts/`](pacts), um arquivo por par consumidor e provedor:

| Consumidor | Provedor | Contrato |
|---|---|---|
| Booking | Catalog | Estabelecimento com expediente, duração e preço dos serviços; `404` para um inexistente |
| Waitlist | Catalog | Nomes e preços do estabelecimento, dos profissionais e dos serviços |
| Waitlist | Booking | Reserva de horário livre e ocupado; confirmação e liberação, inclusive de reserva vencida; evento `booking.cancelled` |
| Notification | Booking, Waitlist | `booking.created`, `booking.cancelled` e `waitlist.offer_created` |
| Analytics | Booking, Waitlist, Catalog | Eventos de agendamento, comparecimento e oferta; expediente para calcular a ocupação |
| MCP server | Catalog, Booking, Waitlist | Estabelecimentos, horários livres, agendamento, cancelamento e entrada na fila |

Os testes dos consumidores rodam os clientes reais contra o mock do Pact e regravam os contratos. Os dos
provedores sobem a API num PostgreSQL do Testcontainers, preparam os dados de cada *provider state* e
geram os eventos com as mesmas funções que gravam o outbox. Remover ou renomear um campo usado por algum
consumidor quebra a suíte do provedor.

A cada push na `main` e na `develop`, e em todo pull request, o GitHub Actions roda a suíte, confere se os
contratos versionados estão em dia e faz o build do front. Um job de segurança roda o Trivy, com os
achados na aba *Security* do GitHub, e a cobertura vai para o SonarCloud. Dois jobs de ponta a ponta sobem
o sistema inteiro, um com Docker Compose e outro num cluster kind com o chart Helm, e executam o k6.

## Desempenho

O cenário de carga ([`load/booking.js`](load/booking.js)) passa pelo gateway: 20 usuários consultam
disponibilidade sem pausa enquanto 50 tentam agendar o mesmo horário ao mesmo tempo.

| Métrica | Sem cache | Com cache do catálogo |
|---|---|---|
| Vazão | 47 req/s | **135 req/s** |
| p95 da disponibilidade | 935 ms | **~300 ms** |
| Agendamentos criados na disputa | 1 de 50 | 1 de 50 |

O teste mostrou que cada consulta chamava o Catalog por HTTP. Um cache de 30 segundos no Booking resolveu
o gargalo ([ADR 0007](docs/adr/0007-cache-do-catalogo.md)). Com o OpenTelemetry ligado em todos os
serviços, o mesmo cenário mediu 168 req/s e p95 de 205 ms: o custo da telemetria ficou dentro da variação
entre execuções. No cluster kind, com tudo no mesmo nó, foram 137 req/s e p95 de 280 ms. Números medidos
no Docker Desktop de uma máquina de desenvolvimento.

## Roadmap

- [x] **Fase 1** — Catalog e Booking, disponibilidade em tempo real, prevenção de conflito, front-end e CI
- [x] **Fase 2** — Eventos no Kafka com outbox transacional; serviço Notification com e-mails no RabbitMQ
      (retry e dead-letter queue) e lembretes
- [x] **Fase 3** — Lista de espera como saga; Keycloak com painel do estabelecimento e token de serviço;
      API gateway com Traefik; teste de carga com k6 no CI
- [x] **Fase 4** — Observabilidade com OpenTelemetry, Prometheus, Grafana e Loki; testes de contrato com
      Pact; serviço de Analytics com CQRS
- [x] **Fase 5** — Kubernetes com kind e Helm; agendamento em linguagem natural com LLM local (Ollama) e
      servidor MCP
- [ ] **Fase 6** — qualidade e segurança na esteira e resiliência entre serviços (v0.6.0);
      comparecimento, faltas e ocupação no Analytics (v0.7.0); trilha de auditoria e webhooks de saída

O que mudou em cada versão está no [CHANGELOG](CHANGELOG.md).

## Como contribuir

### Fluxo de branches

O repositório segue o **Gitflow**:

| Branch | Para quê |
|---|---|
| `main` | Código pronto para produção. Cada merge é uma versão, com tag `vX.Y.Z` |
| `develop` | Integração da próxima versão |
| `feature/<nome>` | Trabalho novo, criado a partir da `develop` e integrado de volta por pull request |
| `release/<versão>` | Preparação da versão, integrada na `main` e na `develop` |
| `hotfix/<nome>` | Correção urgente, criada a partir da `main` e integrada na `main` e na `develop` |

### Mensagens de commit

Os commits seguem o [Conventional Commits](https://www.conventionalcommits.org/pt-br/):

```
<tipo>(<escopo opcional>): <resumo curto no imperativo>
```

| Tipo | Uso |
|---|---|
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `perf` | Melhoria de desempenho |
| `test` | Testes novos ou alterados |
| `refactor` | Mudança de código que não corrige bug nem adiciona funcionalidade |
| `docs` | Só documentação |
| `ci` / `build` | Pipeline, Docker ou dependências |
| `chore` | Manutenção |

Exemplos do histórico: `feat(waitlist): add the waitlist service with an offer saga`,
`perf(booking): cache catalog lookups for 30 seconds`.

Para rodar as checagens a cada commit, instale os hooks uma vez com `uv run pre-commit install`. Antes de
abrir um pull request, confira se os [comandos de teste](#testes) passam.

## Licença

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE).

## Autor

**Matheus França Santana** — Desenvolvedor back-end

[![LinkedIn](https://img.shields.io/badge/LinkedIn-matheusfrancasantana-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/matheusfrancasantana/)
[![GitHub](https://img.shields.io/badge/GitHub-dev--matheusfranca-181717?logo=github&logoColor=white)](https://github.com/dev-matheusfranca)

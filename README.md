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

**Para o estabelecimento**

- **Painel com login** (Keycloak): agenda do dia por profissional, totais, reservas da lista de espera e
  cancelamento com um clique, que já repassa a vaga para a fila.

**Por baixo**

- Microsserviços com banco próprio, eventos no Kafka com outbox transacional e e-mails no RabbitMQ com
  retry e dead-letter queue.
- API gateway com rate limit, autenticação OIDC, tokens de serviço entre microsserviços.
- Teste de carga no CI e documentação interativa (OpenAPI/Swagger) em todos os serviços.

## Telas

| Escolha de serviço, profissional e horário | Agendamento confirmado |
|---|---|
| <img src="docs/screenshots/business.png" alt="Página do estabelecimento com serviços, profissionais e horários" /> | <img src="docs/screenshots/booking.png" alt="Página do agendamento confirmado" /> |

| Oferta da lista de espera | Painel do estabelecimento |
|---|---|
| <img src="docs/screenshots/offer.png" alt="Oferta de vaga com contagem regressiva" /> | <img src="docs/screenshots/painel.png" alt="Painel com a agenda do dia por profissional" /> |

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
    booking -->|REST + cache| catalog
    waitlist -->|"REST + token de serviço"| booking
    booking -.->|outbox| relay["Outbox relay"]
    relay -->|booking.events| kafka{{Kafka}}
    kafka --> worker["Waitlist worker"]
    worker -->|waitlist.events| kafka
    kafka --> notification["Notification"]
    notification <-->|tarefas de e-mail| rabbitmq{{RabbitMQ}}
    notification -->|SMTP| mailpit["Mailpit"]
```

Cada serviço tem o próprio banco PostgreSQL (omitidos no diagrama).

| Componente | Responsabilidade |
|---|---|
| **gateway** | Ponto único de entrada: roteamento, rate limit e cabeçalhos de segurança |
| **catalog** | Estabelecimentos, profissionais, serviços e expediente semanal |
| **booking** | Disponibilidade, agendamentos, reservas temporárias e agenda do dono; publica eventos via outbox |
| **booking-relay** | Publica no Kafka os eventos gravados no outbox do Booking |
| **waitlist** | Fila de espera, ofertas e confirmação (API) |
| **waitlist-worker** | Orquestra a saga: consome cancelamentos, reserva horários, expira ofertas e publica eventos |
| **notification** | Consome eventos, agenda lembretes e envia e-mails pelo RabbitMQ |
| **keycloak** | Identidade: login do dono (PKCE), conta de serviço do Waitlist, papéis e grupos |
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

## Tecnologias

| Camada | Tecnologias |
|---|---|
| Serviços | Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2 (assíncrono), asyncpg, Alembic |
| Mensageria | Apache Kafka 4 (KRaft) com aiokafka, RabbitMQ 4 com aio-pika |
| Identidade | Keycloak 26 (OIDC, PKCE, client credentials), PyJWT, keycloak-js |
| Gateway | Traefik 3 (roteamento, rate limit, cabeçalhos de segurança) |
| E-mail | aiosmtplib, templates HTML, Mailpit para entrega local |
| Banco de dados | PostgreSQL 17 (exclusion constraint com `btree_gist`, JSONB) |
| Front-end | Vue 3, TypeScript, Vite, Tailwind CSS 4, Vue Router, ícones Lucide |
| Testes | pytest, Testcontainers (PostgreSQL, Kafka, RabbitMQ), Hypothesis, import-linter, k6 |
| Qualidade | ruff (lint e formatação), mypy (strict), vue-tsc |
| Infraestrutura | Docker, Docker Compose, nginx, Kafka UI, GitHub Actions |
| Ferramentas | Workspace do uv (um lock file para todos os serviços Python) |

## Estrutura do projeto

```
VagaCerta/
├── services/
│   ├── Dockerfile              # imagem compartilhada dos serviços Python
│   ├── catalog/                # estabelecimentos, profissionais e serviços
│   ├── booking/                # disponibilidade, agendamentos, reservas, outbox e relay
│   ├── waitlist/               # lista de espera, ofertas e worker da saga
│   └── notification/           # consumidor de eventos, lembretes, e-mails e worker do RabbitMQ
│       ├── migrations/         # (em cada serviço) migrações do Alembic
│       ├── src/                # (em cada serviço) código do serviço
│       └── tests/              # (em cada serviço) testes
├── web/                        # front-end em Vue 3, servido por nginx no Docker
├── gateway/dynamic.yml         # rotas e middlewares do Traefik
├── keycloak/                   # realm versionado e tema da tela de login
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
| http://localhost:8025 | Mailpit: todos os e-mails enviados |
| http://localhost:8090 | Kafka UI: tópicos `booking.events` e `waitlist.events` |
| http://localhost:15672 | RabbitMQ: filas de e-mail, retry e dead-letter (`guest` / `guest`) |
| http://localhost:8081 | Dashboard do Traefik |
| http://localhost:8080/auth/admin | Console do Keycloak (`admin` / `admin`) |
| http://localhost:8001/docs · :8002/docs · :8003/docs | Swagger do Catalog, Booking e Waitlist |

**Usuários de demonstração** (senha `vagacerta`):

| Usuário | Papel |
|---|---|
| `clinica` | Dona da Clínica Sorriso Pleno |
| `barbearia` | Dono da Barbearia Navalha de Ouro |
| `admin` | Administrador do catálogo |

> As credenciais e o segredo do cliente de serviço são de demonstração e ficam no realm versionado. Num
> ambiente real, viriam de um cofre de segredos.

### Localmente, sem containers para os serviços

Suba só a infraestrutura com Docker e rode cada processo num terminal:

```bash
docker compose up -d catalog-db booking-db waitlist-db notification-db kafka rabbitmq mailpit keycloak
uv sync

(cd services/catalog && uv run alembic upgrade head && uv run python -m catalog.seed)
(cd services/booking && uv run alembic upgrade head)
(cd services/waitlist && uv run alembic upgrade head)
(cd services/notification && uv run alembic upgrade head)

uv run uvicorn catalog.main:app --port 8001 --reload
uv run uvicorn booking.main:app --port 8002 --reload
uv run uvicorn waitlist.main:app --port 8003 --reload
uv run python -m booking.outbox_relay
uv run python -m waitlist.worker
uv run python -m notification

npm --prefix web install
npm --prefix web run dev
```

O front roda em http://localhost:5173 e encaminha `/api/*` para os serviços.

### Variáveis de ambiente

| Serviço | Variável | Padrão |
|---|---|---|
| catalog | `DATABASE_URL` | `postgresql+asyncpg://vagacerta:vagacerta@localhost:5433/catalog` |
| catalog, booking | `KEYCLOAK_ISSUER` | `http://localhost:8080/auth/realms/vagacerta` |
| catalog, booking | `KEYCLOAK_JWKS_URL` | `<KEYCLOAK_ISSUER>/protocol/openid-connect/certs` |
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
| relay, waitlist, notification | `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9094` |

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
5. **Veja os bastidores.** Os eventos no [Kafka UI](http://localhost:8090) e as filas no
   [RabbitMQ](http://localhost:15672).

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

| Tópico | Tipo | Publicado quando | `data` |
|---|---|---|---|
| `booking.events` | `booking.created` | Um agendamento é confirmado | Horário, cliente, estabelecimento, profissional e serviço |
| `booking.events` | `booking.cancelled` | Um agendamento confirmado é cancelado | Id do agendamento, profissional e horário liberado |
| `waitlist.events` | `waitlist.offer_created` | Um horário é reservado para alguém da fila | Dados da oferta, prazo e link de confirmação |

As mensagens usam o id do agendamento (ou da oferta) como chave, então os eventos de um mesmo agendamento
chegam em ordem.

```json
{
  "event_id": "151a457a-5276-4a3f-896f-dd56508a0fb9",
  "type": "booking.created",
  "occurred_at": "2026-10-23T19:40:28.283996+00:00",
  "data": {
    "booking_id": "80be9d06-b39a-4212-963b-882a7a4ef6a0",
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

## Testes

```bash
uv run pytest            # 58 testes (os de integração sobem containers com Docker)
uv run lint-imports      # regras de arquitetura
uv run mypy services/catalog/src services/booking/src services/notification/src services/waitlist/src
uv run ruff check && uv run ruff format --check
npm --prefix web run build                      # checa os tipos do front-end
docker compose --profile load run --rm k6       # teste de carga contra a stack no ar
```

| Tipo | O que prova |
|---|---|
| Unitário | Regras de disponibilidade e de lembrete; conteúdo dos e-mails, fuso horário e escape de HTML |
| Baseado em propriedades | O Hypothesis gera agendas aleatórias: nenhum horário oferecido sobrepõe outro ou sai do expediente |
| Integração | API com PostgreSQL real via Testcontainers, usando as migrações de verdade |
| Concorrência | 10 requisições simultâneas para o mesmo horário: exatamente um `201` e nove `409` |
| Outbox | O evento só existe se o agendamento foi gravado; o relay publica cada um uma vez, em ordem, num Kafka real |
| Mensageria | Num RabbitMQ real: e-mails entregues, repetidos com backoff e enviados à dead-letter após a última tentativa |
| Idempotência | Evento reentregue não gera segundo e-mail nem segunda oferta; lembrete sai uma vez só |
| Saga | Oferta ao primeiro da fila, pulo de quem não cabe no horário, confirmação e compensação por expiração |
| Segurança | Tokens RS256 assinados no teste: sem token `401`, papel errado `403`, token forjado `401`, dono de outro estabelecimento `403` |
| Arquitetura | Os módulos de domínio não dependem de frameworks nem de brokers |
| Carga (k6) | 50 pessoas disputam o mesmo horário: só uma consegue; a disponibilidade mantém p95 abaixo de 500 ms |

A cada push na `main` e na `develop`, e em todo pull request, o GitHub Actions roda a suíte, o build do
front e um job de ponta a ponta que sobe a stack completa com Docker Compose e executa o k6.

## Desempenho

O cenário de carga ([`load/booking.js`](load/booking.js)) passa pelo gateway: 20 usuários consultam
disponibilidade sem pausa enquanto 50 tentam agendar o mesmo horário ao mesmo tempo.

| Métrica | Sem cache | Com cache do catálogo |
|---|---|---|
| Vazão | 47 req/s | **135 req/s** |
| p95 da disponibilidade | 935 ms | **~300 ms** |
| Agendamentos criados na disputa | 1 de 50 | 1 de 50 |

O teste mostrou que cada consulta chamava o Catalog por HTTP. Um cache de 30 segundos no Booking resolveu
o gargalo ([ADR 0007](docs/adr/0007-cache-do-catalogo.md)). Números medidos no Docker Desktop de uma
máquina de desenvolvimento.

## Roadmap

- [x] **Fase 1** — Catalog e Booking, disponibilidade em tempo real, prevenção de conflito, front-end e CI
- [x] **Fase 2** — Eventos no Kafka com outbox transacional; serviço Notification com e-mails no RabbitMQ
      (retry e dead-letter queue) e lembretes
- [x] **Fase 3** — Lista de espera como saga; Keycloak com painel do estabelecimento e token de serviço;
      API gateway com Traefik; teste de carga com k6 no CI
- [ ] **Fase 4** — Observabilidade com OpenTelemetry, Prometheus, Grafana e Loki; testes de contrato com
      Pact; serviço de Analytics com CQRS
- [ ] **Fase 5** — Kubernetes com kind e Helm; agendamento em linguagem natural com LLM local (Ollama) e
      servidor MCP

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

Antes de abrir um pull request, confira se os [comandos de teste](#testes) passam.

## Licença

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE).

## Autor

**Matheus França Santana** — Desenvolvedor back-end

[![LinkedIn](https://img.shields.io/badge/LinkedIn-matheusfrancasantana-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/matheusfrancasantana/)
[![GitHub](https://img.shields.io/badge/GitHub-dev--matheusfranca-181717?logo=github&logoColor=white)](https://github.com/dev-matheusfranca)

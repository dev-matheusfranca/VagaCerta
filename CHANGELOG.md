# Changelog

Todas as mudanças relevantes do projeto ficam registradas neste arquivo.

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e o projeto usa
[Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [0.8.0] - 2026-10-26

### Adicionado

- Serviço Audit: grava cada evento de agendamento e da lista de espera num registro só de inserção, com
  cada linha encadeada à anterior por hash; o banco recusa alteração e exclusão, e `GET /verify` aponta o
  primeiro registro adulterado.
- Histórico do agendamento no painel: clicando no nome do cliente, o dono vê cada passo, com data e hash.
- Serviço Webhooks: o dono cadastra endereços e eventos, e cada evento é entregue assinado com
  HMAC-SHA256, com novas tentativas e dead-letter pelo RabbitMQ e recusa de endereços internos (SSRF).
- Card "Integrações" no painel, com o cadastro, o segredo mostrado uma vez e o status de cada entrega.
- Demonstração com n8n no perfil `integrations` do Compose: um fluxo pronto transforma cada agendamento
  num e-mail para a equipe.
- Audit e Webhooks no chart Helm, no gateway e na varredura do Trivy.
- Contratos Pact dos eventos lidos pela auditoria e pelos webhooks.
- ADRs 0016 (trilha de auditoria), 0017 (webhooks de saída) e 0018 (o que ficou fora do escopo).

## [0.7.0] - 2026-10-26

### Adicionado

- Registro de comparecimento: depois do horário, o dono marca no painel se a pessoa compareceu ou
  faltou, e o Booking publica `booking.completed` ou `booking.no_show`.
- O Analytics mede comparecimentos, faltas, minutos agendados e capacidade de cada dia, com o expediente
  lido do Catalog, e os horários de pico por dia da semana e hora.
- Card "Últimos 30 dias" no painel, com atendimentos, taxa de faltas, ocupação média e mapa de calor dos
  horários mais procurados; o card dos próximos 14 dias mostra a ocupação da agenda.
- A clínica de demonstração sobe com 30 dias de atendimentos já registrados.
- Contratos Pact dos eventos de comparecimento e da leitura do expediente pelo Analytics.
- ADR 0015 (comparecimento, faltas e ocupação).

### Alterado

- A API de números do Analytics devolve todos os dias do período, inclusive os vazios.
- A agenda do dia mostra os atendimentos que já aconteceram, com o desfecho registrado.

### Corrigido

- O RabbitMQ podia não subir no Docker Compose: o healthcheck, rodando como root, criava o cookie do
  Erlang antes do servidor.

## [0.6.0] - 2026-10-26

### Adicionado

- pre-commit com ruff, checagens de arquivos e gitleaks, também no CI.
- Cobertura de testes com pytest-cov e configuração do SonarCloud, que roda quando o token estiver
  cadastrado no repositório.
- Job de segurança no CI com o Trivy: dependências e configuração na aba *Security* do GitHub, e build
  quebrado por vulnerabilidade alta ou crítica com correção nas imagens próprias.
- Biblioteca `vagacerta-http`: novas tentativas com espera exponencial para consultas e circuit breaker por
  destino, usada por Booking, Waitlist e servidor MCP.
- Testes de resiliência com Toxiproxy e WireMock (latência e queda do Catalog) e com o Kafka pausado.
- ADRs 0013 (resiliência entre serviços) e 0014 (qualidade e segurança na esteira).

### Alterado

- As imagens próprias rodam sem root e as imagens Python não levam mais o `pip`. O front usa o nginx sem
  root e o gateway roda como usuário comum.
- Bases atualizadas: nginx 1.30, Traefik 3.7, Keycloak 26.8 e otel-lgtm 0.38.
- No Kubernetes, as imagens próprias rodam com `securityContext` restrito.
- Com o Catalog fora do ar, o Booking usa o expediente em cache; sem cache, Booking e Waitlist respondem
  `503`. As chamadas entre serviços têm timeout de 2 segundos.
- No Docker Compose, os workers reiniciam sozinhos em caso de falha.
- O teste de concorrência disputa o mesmo horário com 40 requisições.

### Corrigido

- Agendamentos simultâneos no mesmo horário podiam entrar em deadlock no PostgreSQL, devolver `500` e
  deixar a disponibilidade lenta sob carga. Era a causa da falha intermitente no teste de carga do CI.
- O relay do outbox e o worker da lista de espera paravam no primeiro erro do Kafka ou do Booking.
- No Kubernetes, a probe de prontidão do gateway conferia a página do site em vez do ping do Traefik.

## [0.5.0] - 2026-10-24

### Adicionado

- Servidor MCP com as ferramentas de agendamento (listar estabelecimentos, ver serviços e profissionais,
  buscar horários livres, agendar, entrar na lista de espera e cancelar), também exposto no gateway em
  `/mcp`.
- Assistente que agenda conversando: um modelo local no Ollama (`qwen3:4b-instruct`) usa as ferramentas
  MCP, e o site ganhou a página "Agende conversando".
- Spans com os atributos GenAI do OpenTelemetry para cada chamada ao modelo e cada ferramenta executada.
- Testes de contrato do servidor MCP com Catalog, Booking e Waitlist, e verificação HTTP do Waitlist como
  provedor.
- Chart Helm com o sistema inteiro e script que sobe tudo num cluster kind.
- Job no CI que cria o cluster kind, instala o chart e roda o teste de carga contra ele.
- Assistente e Ollama no perfil `ai` do Docker Compose.
- ADRs 0011 (assistente com LLM local e MCP) e 0012 (Kubernetes com kind e Helm).

### Alterado

- Realm e tema do Keycloak, rotas do Traefik e dashboard do Grafana são construídos em imagens, usadas
  pelo Docker Compose e pelo Kubernetes.
- O projeto do Docker Compose tem nome fixo (`vagacerta`), para as imagens terem sempre o mesmo nome.
- As verificações de contrato dos provedores compartilham a subida do servidor de teste.

## [0.4.0] - 2026-10-24

### Adicionado

- Observabilidade com OpenTelemetry em todos os processos: traces, métricas e logs enviados ao
  `grafana/otel-lgtm` (Tempo, Prometheus, Loki e Grafana), com um dashboard versionado.
- O contexto do trace é gravado no outbox e segue pelos cabeçalhos do Kafka e do RabbitMQ: um
  cancelamento vira um único trace, do clique ao e-mail.
- Métricas de negócio: agendamentos criados e cancelados, ofertas da lista de espera por resultado e
  e-mails enviados, repetidos ou na dead-letter.
- Serviço Analytics com CQRS: um worker projeta os eventos em read models diários, e a API entrega os
  números ao dono do estabelecimento.
- "Próximos 14 dias" no painel: agendamentos, cancelamentos, receita prevista e receita recuperada pela
  lista de espera.
- Eventos `waitlist.offer_claimed` e `waitlist.offer_expired`; `booking.created` passa a trazer o
  `business_id`.
- Testes de contrato com Pact nas APIs REST e nos eventos do Kafka, com os contratos versionados em
  `pacts/` e verificados pelos provedores.
- Biblioteca `vagacerta-auth` no workspace, com a validação dos tokens do Keycloak usada por Catalog,
  Booking e Analytics.
- ADRs 0008 (observabilidade), 0009 (Analytics com CQRS) e 0010 (testes de contrato).

### Alterado

- Os dados de demonstração do Booking são gravados pelo outbox, para o painel já abrir com números.
- O CI falha se os contratos versionados estiverem desatualizados.
- Limites de memória da JVM para Kafka, Keycloak e Kafka UI.

### Corrigido

- Depois de um novo deploy do front, o navegador podia usar um `index.html` em cache que apontava para
  arquivos que não existem mais e mostrar a página em branco.

## [0.3.0] - 2026-10-23

### Adicionado

- API gateway com Traefik: ponto único de entrada, rate limit nas gravações e cabeçalhos de segurança.
- Serviço Waitlist: lista de espera como saga orquestrada, com reserva temporária do horário, oferta por
  e-mail, confirmação e compensação quando a oferta expira.
- Reservas temporárias no Booking (`/holds`, `/confirm`, `/release`); `booking.cancelled` passa a trazer o
  horário liberado.
- E-mail "Uma vaga abriu" e página da oferta com contagem regressiva.
- Keycloak com realm versionado, tema de login próprio, login do dono com PKCE e token de serviço
  (client credentials) para o Waitlist chamar o Booking.
- Painel do estabelecimento com a agenda do dia por profissional, totais e cancelamento.
- Dados de demonstração: um dia lotado na Clínica Sorriso Pleno e usuários de exemplo.
- Teste de carga com k6 e job de ponta a ponta no CI, que sobe a stack completa.
- ADRs 0005 (saga da lista de espera), 0006 (Keycloak e gateway) e 0007 (cache do catálogo).

### Alterado

- Criar estabelecimentos, profissionais e serviços exige o papel `admin`.
- O Booking guarda o catálogo em cache por 30 segundos: vazão de 47 para 135 req/s no teste de carga.
- Só agendamentos confirmados podem ser cancelados.
- README, ADRs e changelog em português.

## [0.2.1] - 2026-10-23

### Adicionado

- O pipeline de CI pode ser executado manualmente pela aba Actions.

## [0.2.0] - 2026-10-23

### Adicionado

- Eventos de agendamento (`booking.created`, `booking.cancelled`) gravados num outbox transacional e
  publicados no Kafka por um outbox relay.
- Serviço Notification com e-mails de confirmação, cancelamento e lembrete, em templates HTML com a
  identidade visual do app.
- Envio de e-mails pelo RabbitMQ com novas tentativas após 5 s, 30 s e 2 min, e dead-letter queue.
- Consumo idempotente de eventos e projeção local dos agendamentos no Notification.
- Kafka, Kafka UI, RabbitMQ e Mailpit no Docker Compose.
- A página do agendamento mostra para qual e-mail a confirmação foi enviada.
- ADR 0003 (outbox transacional) e ADR 0004 (Kafka para eventos, RabbitMQ para tarefas).

### Alterado

- Cancelar um agendamento já cancelado não faz nada e não emite evento.
- Os testes de integração rodam contra Kafka e RabbitMQ reais e usam os módulos `community` do
  Testcontainers.

## [0.1.0] - 2026-10-23

### Adicionado

- Serviço Catalog com estabelecimentos, profissionais, serviços e expediente, com dados de exemplo.
- Serviço Booking com disponibilidade em tempo real e prevenção de conflito de horário por exclusion
  constraint do PostgreSQL.
- Front-end em Vue 3 com o fluxo completo de agendamento.
- Testes unitários, baseados em propriedades, de integração, de concorrência e de arquitetura.
- Docker Compose, pipeline no GitHub Actions, README e ADRs 0001 e 0002.

[0.8.0]: https://github.com/dev-matheusfranca/VagaCerta/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/dev-matheusfranca/VagaCerta/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/dev-matheusfranca/VagaCerta/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/dev-matheusfranca/VagaCerta/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/dev-matheusfranca/VagaCerta/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/dev-matheusfranca/VagaCerta/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/dev-matheusfranca/VagaCerta/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/dev-matheusfranca/VagaCerta/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/dev-matheusfranca/VagaCerta/releases/tag/v0.1.0

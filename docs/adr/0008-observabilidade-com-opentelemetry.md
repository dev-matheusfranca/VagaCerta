# ADR 0008 — Observabilidade com OpenTelemetry e a stack LGTM

**Status:** aceita

## Contexto

Um cancelamento atravessa quatro serviços, dois brokers e dois outboxes até virar o e-mail "Uma vaga
abriu". Quando a oferta não chegava, a investigação era abrir os logs de cada container e cruzar horários
na mão. Também não havia como responder perguntas simples, como a latência do Booking sob carga ou
quantos e-mails foram para a dead-letter.

## Decisão

- **OpenTelemetry com instrumentação automática.** Cada processo sobe com `opentelemetry-instrument`, que
  instrumenta FastAPI, httpx, asyncpg, aiokafka, aio-pika e o `logging`. A configuração fica toda em
  variáveis de ambiente (`OTEL_*`) num bloco compartilhado do Docker Compose.
- **Contexto propagado pelo outbox.** A requisição que grava o evento também grava o `traceparent` numa
  coluna do outbox. O relay restaura esse contexto ao publicar no Kafka, então o trace não se quebra no
  intervalo entre a gravação e a publicação. Nos consumidores, o contexto vem dos cabeçalhos das
  mensagens do Kafka e do RabbitMQ.
- **Métricas de negócio** como contadores do OpenTelemetry: agendamentos criados e cancelados por origem,
  ofertas da lista de espera por resultado e e-mails por resultado (enviado, repetido, dead-letter).
- **`grafana/otel-lgtm`** como backend local: um único container com o OpenTelemetry Collector, Tempo
  (traces), Prometheus (métricas), Loki (logs) e Grafana, com um dashboard versionado em
  `observability/`.

## Consequências

- Um cancelamento vira **um único trace**, do `POST /cancel` ao envio do e-mail, passando pelo relay, pelo
  worker da saga, pela reserva no Booking e pelo RabbitMQ. Os logs de cada span ficam ligados ao trace.
- O código dos serviços quase não muda: só a propagação pelo outbox, os spans dos consumidores e os
  contadores de negócio são manuais.
- O `otel-lgtm` é feito para desenvolvimento e demonstração. Em produção, cada peça (Collector, Tempo,
  Prometheus, Loki) rodaria separada, com retenção e alta disponibilidade.
- Exportar a cada 5 segundos e instrumentar tudo tem custo: com o k6, a vazão ficou em 168 req/s e o p95
  em 205 ms, ainda dentro do limite de 500 ms.

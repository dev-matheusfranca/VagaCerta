# ADR 0013 — Resiliência entre serviços

**Status:** aceita

## Contexto

Booking, Waitlist e o servidor MCP chamam outros serviços por HTTP, e os relays publicam o outbox no
Kafka. Até a fase 5, qualquer falha passageira virava erro: com o Catalog fora do ar, o Booking respondia
`500`, mesmo tendo o expediente em cache havia poucos segundos. O relay do outbox morria no primeiro erro
do Kafka, e no Docker Compose nada o reiniciava: os eventos ficavam parados até alguém subir o processo
de novo.

## Decisão

- **Biblioteca `vagacerta-http`**, um transporte do httpx usado por todos os clientes entre serviços:
  - repete só **métodos seguros** (`GET`, `HEAD`, `OPTIONS`), com espera exponencial, em erro de conexão
    e em respostas `5xx`. Escritas saem uma vez só, porque repetir um `POST` poderia duplicar o efeito;
  - tem um **circuit breaker** por destino: depois de 5 falhas seguidas, as chamadas falham na hora por
    10 segundos, e a primeira chamada depois disso testa o destino de novo.
- **Timeouts de 2 segundos** nas chamadas internas, que levam milissegundos quando tudo está bem.
- **Degradação no Booking:** com o Catalog fora, o cache vencido continua servindo a disponibilidade.
  Sem cache, Booking e Waitlist respondem `503` com uma mensagem clara, em vez de `500`.
- **Workers que não morrem:** os relays registram a falha do Kafka e tentam de novo, com os eventos
  esperando no outbox. O worker da lista de espera faz o mesmo quando o Booking não responde. No
  Compose, os workers têm `restart: on-failure` como última proteção; no Kubernetes isso já é padrão.
- **Testes com falhas de verdade:** o Toxiproxy fica entre o Booking e um Catalog simulado pelo
  WireMock, injetando latência e derrubando a conexão. Outro teste pausa o container do Kafka com o
  relay rodando.

## Consequências

- Com o Catalog fora, quem já estava em cache continua agendando. Na stack real, o Kafka ficou fora
  por quase um minuto, o agendamento foi aceito e o e-mail chegou quando ele voltou.
- As primeiras chamadas para um destino fora do ar ainda pagam os timeouts (cerca de 6 segundos com as
  repetições) até o circuito abrir.
- Enquanto o Catalog estiver fora, a disponibilidade pode usar um expediente desatualizado.
- O circuito é por processo: cada réplica decide sozinha quando abrir.
- Um envio interrompido no meio do lote pode publicar um evento duas vezes; os consumidores são
  idempotentes e descartam a repetição.

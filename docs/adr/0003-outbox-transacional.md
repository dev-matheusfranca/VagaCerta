# ADR 0003 — Outbox transacional para os eventos

**Status:** aceita

## Contexto

Outros serviços precisam reagir quando um agendamento é criado ou cancelado. Gravar no PostgreSQL e depois
publicar no Kafka é uma escrita dupla: se o processo cai entre as duas, ou o agendamento existe sem evento,
ou um evento anuncia um agendamento que foi desfeito (por exemplo, pela constraint de conflito).

## Decisão

O serviço grava o evento numa tabela `outbox` **na mesma transação** da mudança. Um processo separado, o
outbox relay, lê as linhas pendentes em ordem, publica no Kafka e as marca como publicadas. O Booking usa o
padrão para `booking.events`, e o Waitlist para `waitlist.events`.

- As linhas são lidas com `FOR UPDATE SKIP LOCKED`, então várias réplicas do relay podem rodar sem
  publicar o mesmo evento ao mesmo tempo.
- As mensagens usam o id do agendamento (ou da oferta) como chave, então os eventos de um mesmo agendamento
  caem na mesma partição, em ordem.
- Um índice parcial nas linhas pendentes mantém a leitura barata conforme a tabela cresce.

## Consequências

- Um evento é publicado se, e somente se, a mudança foi confirmada no banco.
- A entrega é **pelo menos uma vez**: se o relay cai depois de publicar e antes de marcar a linha, o evento
  sai de novo. Por isso os consumidores são idempotentes (tabela `processed_events`).
- Os eventos chegam ao Kafka com um pequeno atraso (o intervalo de leitura, 0,5 s quando ocioso).
- CDC com Debezium eliminaria a leitura periódica, ao custo de rodar o Kafka Connect; para este volume a
  leitura periódica basta.

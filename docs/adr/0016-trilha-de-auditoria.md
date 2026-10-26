# ADR 0016 — Trilha de auditoria encadeada por hash

**Status:** aceita

## Contexto

Quando um cliente diz "eu agendei e o horário sumiu", o dono não tem como saber o que aconteceu. Os
eventos passam pelo Kafka, mas cada serviço guarda só o estado atual, e um registro em banco comum pode
ser alterado sem deixar rastro. O sistema precisava de um histórico de cada agendamento que ninguém
conseguisse reescrever sem ser notado.

## Decisão

- **Um serviço Audit consome todos os eventos** de `booking.events` e `waitlist.events` e grava cada um,
  inteiro, numa tabela própria. Ele não depende dos outros serviços: o histórico sai só dos eventos.
- **Cada registro guarda o hash do anterior.** O hash é o SHA-256 do hash anterior, do tópico e do evento
  em JSON canônico. Mudar um registro antigo invalida todos os seguintes.
- **Um escritor por vez.** Um advisory lock do PostgreSQL serializa a gravação, para duas réplicas não
  encadearem no mesmo registro anterior. O `event_id` é único: reentrega não duplica a corrente.
- **O banco só aceita inserções.** Triggers rejeitam `UPDATE`, `DELETE` e `TRUNCATE` na tabela.
- **Duas leituras:** o dono vê o histórico de um agendamento no painel, clicando no nome do cliente; o
  administrador chama `GET /verify`, que recalcula a corrente e aponta o primeiro registro adulterado.

## Consequências

- O painel responde "o que aconteceu com esse horário" com data, hora e o hash de cada passo, inclusive
  quando o agendamento veio da lista de espera.
- A corrente detecta adulteração, mas não a impede: quem tem acesso de superusuário ao banco pode
  desligar o trigger e recalcular tudo. Ancorar o último hash fora do banco resolveria isso e ficou de
  fora.
- A gravação é sequencial. No volume de um pequeno negócio isso não pesa; em escala maior, a corrente
  poderia ser dividida por estabelecimento.
- O histórico guarda os dados pessoais que viajam nos eventos. Atender a um pedido de exclusão (LGPD)
  exigiria guardar só um resumo ou cifrar o conteúdo por cliente.

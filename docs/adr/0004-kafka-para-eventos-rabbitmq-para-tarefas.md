# ADR 0004 — Kafka para eventos, RabbitMQ para tarefas de e-mail

**Status:** aceita

## Contexto

O sistema precisa de dois tipos de mensageria:

1. **Eventos de domínio** (`booking.created`, `booking.cancelled`, `waitlist.offer_created`): fatos que
   vários serviços consomem ao longo do tempo (Notification e Waitlist hoje; Analytics numa próxima fase),
   possivelmente reprocessando o histórico.
2. **Tarefas de e-mail**: unidades de trabalho que precisam ser repetidas quando o servidor SMTP falha,
   com intervalos crescentes, e separadas para análise quando continuam falhando.

## Decisão

- Eventos de domínio vão para o **Kafka**. Cada grupo de consumidores mantém o próprio offset, e o log pode
  ser relido para construir novas projeções.
- Tarefas de e-mail vão para o **RabbitMQ**, com uma fila de retry por tentativa:

  | Fila | Papel |
  |---|---|
  | `notification.email` | E-mails prontos para envio |
  | `notification.email.retry.N` | Espera um TTL fixo (5 s, 30 s, 2 min) e devolve a mensagem para `notification.email` |
  | `notification.email.dead` | E-mails que falharam em todas as tentativas, guardados para análise |

  O worker confirma a mensagem original e a republica na próxima fila com o cabeçalho
  `x-failed-attempts`.

## Consequências

- Cada broker faz o que faz melhor: log reprocessável para fatos; confirmação por mensagem e
  dead-lettering para tarefas.
- Um TTL fixo por fila dá intervalos crescentes sem o plugin de mensagens atrasadas e sem bloqueio na
  cabeça da fila (numa fila única com TTLs diferentes por mensagem, só a primeira expira).
- Dois brokers para operar em vez de um. Aceitável aqui: o projeto também quer mostrar as duas
  ferramentas nos papéis em que elas brilham.
- A entrega de e-mail é pelo menos uma vez: uma queda depois de enviar e antes de confirmar reenvia o
  e-mail.

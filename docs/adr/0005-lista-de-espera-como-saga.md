# ADR 0005 — Lista de espera como saga orquestrada com reservas temporárias

**Status:** aceita

## Contexto

Quando alguém cancela, o horário deve ir para a primeira pessoa da lista de espera. Mas o horário também
fica visível para qualquer pessoa no site: se a oferta só avisasse por e-mail, outra pessoa poderia
agendá-lo antes de quem estava na fila. Além disso, quem recebe a oferta pode não responder, e o horário
não pode ficar preso.

O fluxo atravessa dois serviços (Waitlist e Booking) e não cabe numa transação de banco única.

## Decisão

O **Waitlist orquestra uma saga** com uma reserva temporária (*hold*) no Booking:

1. Ao consumir `booking.cancelled`, o Waitlist pede `POST /holds` no Booking para a primeira pessoa da fila
   para quem o horário serve. A reserva ocupa o horário por um tempo limitado (15 minutos por padrão) e entra
   na mesma constraint de conflito dos agendamentos.
2. O Waitlist grava a oferta e publica `waitlist.offer_created`; o Notification envia o e-mail com o link.
3. **Se a pessoa confirma a tempo**, o Waitlist chama `POST /bookings/{id}/confirm`; a reserva vira
   agendamento e o Booking emite `booking.created`.
4. **Se a oferta expira**, a compensação chama `POST /bookings/{id}/release` e oferece o mesmo horário à
   próxima pessoa da fila. Se o Booking responder que a reserva já foi confirmada (o Waitlist caiu entre a
   confirmação e o próprio commit), a oferta é marcada como aceita em vez de expirada.

Os comandos `holds`, `confirm` e `release` exigem o papel `booking-holds`, que só a conta de serviço do
Waitlist tem (ver [ADR 0006](0006-keycloak-e-api-gateway.md)).

## Consequências

- Quem está na fila tem a vaga garantida durante a oferta, sem disputar com o público.
- Toda falha tem uma saída definida: hold que não cabe (serviço mais longo) passa para o próximo; oferta
  vencida é compensada; confirmação repetida é idempotente.
- Reservas vencidas também são liberadas pelo próprio Booking antes de novas reservas, então um Waitlist
  fora do ar não deixa horários presos indefinidamente.
- Orquestração (e não coreografia) deixa o fluxo legível num único lugar
  ([`saga.py`](../../services/waitlist/src/waitlist/saga.py)), ao custo de o Waitlist conhecer a API do
  Booking.

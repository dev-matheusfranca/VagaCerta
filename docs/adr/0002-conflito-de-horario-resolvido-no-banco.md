# ADR 0002 — O banco impede o conflito de horário

**Status:** aceita

## Contexto

Duas pessoas podem tentar agendar o mesmo profissional em horários sobrepostos no mesmo instante. Checar na
aplicação ("o horário está livre?") e depois inserir é uma condição de corrida: as duas requisições passam
pela checagem e as duas inserem.

## Decisão

A tabela `bookings` tem uma **exclusion constraint** do PostgreSQL:

```sql
EXCLUDE USING gist (professional_id WITH =, tstzrange(starts_at, ends_at) WITH &&)
WHERE (status IN ('confirmed', 'held'))
```

A aplicação valida se o horário cabe no expediente, insere e transforma a violação da constraint em
`409 Conflict`. Reservas temporárias da lista de espera (`held`) também ocupam o horário (ver
[ADR 0005](0005-lista-de-espera-como-saga.md)).

## Consequências

- Correto sob qualquer concorrência, sem locks na aplicação nem locks distribuídos.
- Sob disputa forte, inserções simultâneas na exclusion constraint podem entrar em **deadlock** no
  PostgreSQL: cada transação grava sua linha e espera a outra para checar o conflito. No teste de carga,
  isso devolvia `500` e segurava conexões por 1 segundo, até o banco desfazer o ciclo. Antes de inserir,
  a transação pega um `pg_advisory_xact_lock` pelo profissional, liberado no commit: as tentativas de
  agendar com o mesmo profissional entram em fila e as perdedoras recebem `409` na hora. A constraint
  continua sendo a garantia; profissionais diferentes não esperam uns pelos outros.
- Detecta sobreposição de qualquer duração, não só horários de início iguais (um índice único deixaria
  passar 09:00–10:00 contra 09:30–10:30).
- Agendamentos cancelados ficam fora da constraint, então o horário pode ser reagendado na hora.
- Depende da extensão `btree_gist`, que já vem com o PostgreSQL.
- Coberto pelo teste `test_only_one_of_many_simultaneous_requests_gets_the_slot` e pelo teste de carga
  com k6 (50 pessoas disputando o mesmo horário).

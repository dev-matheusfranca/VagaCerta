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
- Detecta sobreposição de qualquer duração, não só horários de início iguais (um índice único deixaria
  passar 09:00–10:00 contra 09:30–10:30).
- Agendamentos cancelados ficam fora da constraint, então o horário pode ser reagendado na hora.
- Depende da extensão `btree_gist`, que já vem com o PostgreSQL.
- Coberto pelo teste `test_only_one_of_many_simultaneous_requests_gets_the_slot` e pelo teste de carga
  com k6 (50 pessoas disputando o mesmo horário).

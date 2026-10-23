# ADR 0007 — Cache curto do catálogo no Booking

**Status:** aceita

## Contexto

O teste de carga com k6 (20 usuários consultando disponibilidade sem pausa) mostrou p95 de **935 ms** e
vazão de **47 req/s**. Cada consulta de disponibilidade chamava o Catalog por HTTP para obter fuso
horário, expediente e duração do serviço, e o Catalog fazia três queries por chamada. Isoladas, as
requisições levavam de 15 a 60 ms: o gargalo era o volume de trabalho repetido.

## Decisão

O `CatalogClient` do Booking guarda cada estabelecimento em memória por **30 segundos**.

## Consequências

- Vazão de 47 para **135 req/s** (2,9×) e p95 de 935 ms para cerca de **300 ms** no mesmo cenário.
- Uma mudança de expediente ou de serviço leva até 30 segundos para valer no Booking. Aceitável para dados
  que mudam raramente.
- O cache é por processo; com várias réplicas, cada uma aquece o seu. Um cache compartilhado (Redis) ou
  invalidação por eventos do Catalog ficam para quando houver necessidade.
- A meta de p95 abaixo de 500 ms virou um threshold do k6, executado no CI a cada push.

# ADR 0009 — Serviço Analytics com CQRS

**Status:** aceita

## Contexto

O dono do estabelecimento quer ver os próximos dias de uma vez: quantos agendamentos, quantos
cancelamentos, a receita prevista e quanto a lista de espera recuperou. Calcular isso a cada acesso
exigiria consultar o Booking e o Waitlist e somar tudo na hora, acoplando o painel aos bancos e ao
desempenho dos serviços que atendem os clientes.

## Decisão

- **Um serviço só de leitura, o Analytics**, com banco próprio. Um worker consome `booking.events` e
  `waitlist.events` e mantém **read models** prontos para o painel: uma linha por estabelecimento e dia
  com agendamentos, cancelamentos, receita, ofertas feitas, aceitas e expiradas e receita recuperada.
- **Projeções idempotentes.** Cada evento é registrado como processado na mesma transação que atualiza os
  totais, e os incrementos usam `INSERT ... ON CONFLICT DO UPDATE`.
- **Eventos com o que a projeção precisa.** `booking.created` passou a trazer o `business_id`, e o Waitlist
  passou a publicar `waitlist.offer_claimed` e `waitlist.offer_expired`, além de `offer_created`.
- **Validação de token compartilhada.** O Analytics também exige o papel `owner` e o grupo do
  estabelecimento. Em vez de uma terceira cópia, a validação de JWT virou a biblioteca `vagacerta-auth`,
  um membro do workspace do uv usado por Catalog, Booking e Analytics.

## Consequências

- O painel faz uma única consulta simples, sem tocar nos serviços de escrita.
- Os números são **eventualmente consistentes**: aparecem alguns instantes depois do evento.
- O consumidor lê os tópicos desde o início (`earliest`). Para recalcular uma projeção ou criar outra, basta
  zerar as tabelas e reprocessar o log do Kafka.
- Os dados de demonstração passaram a ser gravados pelo outbox do Booking, para que o painel já abra com
  números.

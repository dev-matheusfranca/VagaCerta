# ADR 0015 — Comparecimento, faltas e ocupação

**Status:** aceita

## Contexto

Falta é o principal problema que o VagaCerta promete atacar: lembretes e lista de espera existem para
reduzir horário vazio. Mesmo assim, o sistema não sabia se a pessoa tinha vindo. O Analytics contava
agendamentos e cancelamentos, mas não respondia às perguntas que o dono faz: quantos faltaram, quanto da
agenda está ocupada e quais horários são mais procurados.

## Decisão

- **O dono registra o desfecho.** Depois que o horário começa, o painel mostra "Compareceu" e "Faltou".
  O Booking só aceita o registro para agendamentos confirmados, do próprio estabelecimento, e publica
  `booking.completed` ou `booking.no_show` pelo outbox.
- **Analytics mede três coisas novas:**
  - comparecimentos e faltas por dia, e a taxa de faltas sobre quem tinha horário;
  - **ocupação**: minutos agendados divididos pelos minutos de expediente. O expediente vem do Catalog na
    hora da consulta, com cache e o transporte resiliente; sem o Catalog, os números saem sem a
    capacidade em vez de falhar;
  - **horários de pico**: uma tabela por dia da semana e hora, no fuso do estabelecimento, que soma os
    agendamentos e desconta os cancelamentos.
- **A API de números devolve todos os dias do período**, inclusive os vazios. Sem isso, a ocupação média
  ignoraria os dias sem agendamento e pareceria maior do que é.
- **Dados de demonstração com histórico:** a clínica sobe com 30 dias de atendimentos, com mais procura
  cedo e no fim da tarde e cerca de 12% de faltas, sempre os mesmos (semente fixa).

## Consequências

- O painel responde de cara a "quantos faltaram" e "quando estou mais cheio", e os números vêm só de
  eventos, como o resto do Analytics.
- Registrar o desfecho depende do dono. Sem registro, a visita fica como confirmada e não entra em
  nenhuma das contas.
- Mudanças no expediente valem para toda a série, porque a capacidade é calculada com o expediente atual.
- Os horários de pico olham todo o histórico, sem janela de tempo.

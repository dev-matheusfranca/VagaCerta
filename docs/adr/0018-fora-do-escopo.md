# ADR 0018 — O que ficou fora do escopo

**Status:** aceita

## Contexto

O plano inicial do VagaCerta listava mais tecnologias do que o produto precisa. Ao fechar a fase 6, cada
item restante foi pesado pelo que ele resolve no produto e pelo que ele ensina no projeto. Esta ADR
registra o que não entrou, e por quê, para que a ausência seja uma escolha e não um esquecimento.

## Decisão

Ficam de fora, por ora:

| Item | Por que não agora |
|---|---|
| **Sinal antecipado com pagamento** | Adiado por decisão de produto. O desenho estava pronto: serviço Payment com provedor simulado tipo Pix, id do agendamento como chave de idempotência, reserva de 15 minutos, estorno se o pagamento chegar depois e reconciliação com o extrato. A reserva temporária da lista de espera e os webhooks assinados já são as peças que ele usaria |
| **gRPC entre Booking e Catalog** | A chamada é uma leitura com cache de 30 segundos (ADR 0007); o gargalo medido já foi resolvido. gRPC traria geração de código e um segundo protocolo sem ganho medido |
| **AsyncAPI e FastStream** | Os contratos Pact já documentam e verificam o formato de cada evento. Trocar aiokafka e aio-pika por FastStream mexeria em todos os consumidores sem mudar comportamento |
| **Testes de mutação** | Com o Hypothesis, os testes de concorrência e os contratos, a confiança na suíte já é alta. A mutação é lenta nos testes de integração, que são a maior parte |
| **Testes de ponta a ponta com Playwright** | O CI já sobe o sistema inteiro duas vezes (Compose e kind) e roda o k6. A tela é verificada à mão a cada mudança, com capturas no README |
| **Notificação pelo Telegram** | O e-mail cobre o fluxo. Com os webhooks (ADR 0017), um bot do Telegram vira um fluxo no n8n, sem código no VagaCerta |
| **Reescrever o Notification em Go** | Mostraria outra linguagem, mas sem ganho para o produto, e dobraria o ferramental do CI |
| **Previsão de faltas** | Pede um histórico real que o sistema ainda não tem; com dados da semente, o modelo só aprenderia o gerador aleatório. Os eventos de comparecimento (ADR 0015) já guardam o que ela usaria |
| **Redis** | O único cache é o do catálogo, em memória em cada réplica, e é suficiente. Redis faria sentido com cache compartilhado entre muitas réplicas ou rate limit distribuído |
| **Carga com 500 usuários** | O cenário de 70 usuários já mostra a disputa pelo horário e o gargalo. Mais carga no Docker Desktop mediria a máquina, não o sistema |

## Consequências

- O projeto fica menor e cada tecnologia presente resolve um problema que o produto tem.
- Os itens continuam possíveis: a arquitetura por eventos e os webhooks deixam a maioria deles como um
  consumidor novo, sem mudar os serviços existentes.

# ADR 0017 — Webhooks de saída

**Status:** aceita

## Contexto

Pequenos negócios já usam outras ferramentas: planilha, CRM, automação com n8n ou Zapier, mensagem no
celular da equipe. Integrar cada uma dentro do VagaCerta não escala. O padrão do mercado é o sistema
avisar por HTTP, a cada evento, o endereço que o cliente cadastrou.

## Decisão

- **Um serviço Webhooks** guarda as assinaturas (endereço e eventos escolhidos) de cada estabelecimento.
  O dono cadastra e remove pelo painel. O worker consome os eventos do Kafka e cria uma entrega por
  assinatura interessada; o par assinatura e evento é único, então reentrega não duplica envio.
- **Entrega pelo RabbitMQ, como os e-mails.** Cada entrega vira uma tarefa; falha (erro de rede ou
  resposta fora de 2xx) volta por filas de espera de 5 s, 30 s e 2 min e, depois da última tentativa, vai
  para a dead-letter. O painel mostra o status, as tentativas e o último código HTTP de cada entrega.
- **Assinatura HMAC-SHA256.** Cada assinatura tem um segredo, mostrado uma única vez no cadastro. O
  corpo vai assinado no cabeçalho `X-VagaCerta-Signature`, e o destino confere que o envio veio daqui e
  não foi alterado.
- **Proteção contra SSRF.** Só `http` e `https`, e o endereço precisa resolver para IPs públicos. A
  checagem acontece no cadastro e de novo antes de cada envio, para um DNS que muda de ideia não apontar
  para a rede interna; redirecionamentos não são seguidos. Só a demonstração local libera a rede do
  Docker, com `ALLOW_PRIVATE_TARGETS=true`.
- **Eventos só a partir do cadastro.** Uma assinatura nova não recebe eventos antigos.
- **Demonstração com n8n.** O perfil `integrations` do Compose sobe o n8n com um fluxo pronto, que recebe
  `booking.created` e manda um e-mail para a equipe pelo Mailpit.

## Consequências

- Qualquer ferramenta que receba HTTP integra com o VagaCerta sem código novo do nosso lado.
- A entrega é "pelo menos uma vez": o destino deve usar o `event_id` ou o `X-VagaCerta-Delivery` para
  ignorar repetições.
- A ordem entre eventos não é garantida, porque uma entrega que falhou pode chegar depois da seguinte.
- O segredo fica em texto no banco do serviço, porque é preciso para assinar. Num ambiente real, seria
  cifrado com uma chave de um cofre de segredos.
- Não há reenvio manual de uma entrega da dead-letter nem troca do segredo; hoje o caminho é remover e
  cadastrar de novo.

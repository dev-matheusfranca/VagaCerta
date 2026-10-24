# ADR 0011 — Assistente com LLM local e servidor MCP

**Status:** aceita

## Contexto

Agendar pelo site exige escolher estabelecimento, serviço, profissional, dia e horário, nessa ordem. Muita
gente prefere pedir do jeito que fala: "quero cortar o cabelo na terça à tarde". Um assistente com LLM
resolve isso, mas traz três questões: o modelo não pode inventar horários, o projeto só usa ferramentas
gratuitas, e o agendamento não deve ficar preso a um único cliente de IA.

## Decisão

- **Servidor MCP próprio** (`mcp-server`, SDK oficial do Model Context Protocol). Ele expõe o fluxo de
  agendamento como ferramentas: listar estabelecimentos, ver serviços e profissionais, buscar horários
  livres, agendar, entrar na lista de espera e cancelar. As ferramentas chamam as APIs que já existem, e os
  erros esperados (horário ocupado, dados inválidos) voltam como mensagem para o modelo explicar ou tentar
  outro horário. O transporte é Streamable HTTP sem estado, exposto também no gateway em `/mcp`, então
  qualquer cliente MCP pode usar as mesmas ferramentas.
- **Assistente separado** (`assistant`), que é um cliente MCP. A cada mensagem ele lista as ferramentas,
  conversa com o modelo e executa as chamadas de ferramenta até o modelo responder sem pedir nenhuma, com
  limite de passos. O navegador guarda a conversa e a envia a cada turno, e o serviço não guarda estado.
- **Modelo local com Ollama**, padrão `qwen3:4b-instruct`, configurável por `OLLAMA_MODEL`: gratuito, roda
  offline e roda numa GPU de entrada. A variante instruct responde direto; a tag `qwen3:4b` aponta para a
  que sempre raciocina antes e gastava centenas de tokens por resposta. O contexto fica em 6 mil tokens e
  a temperatura em 0,2. No Docker Compose, o assistente e o Ollama sobem no perfil `ai`; com o Ollama
  instalado na máquina, basta apontar `OLLAMA_URL` para ele.
- **O modelo não faz contas de calendário.** As datas dos próximos dias vão prontas nas instruções, e
  `find_slots` devolve o dia da semana da data consultada.
- **Observabilidade de IA.** Cada chamada ao modelo e cada execução de ferramenta vira um span com os
  atributos GenAI do OpenTelemetry (modelo e tokens de entrada e saída), no mesmo trace das chamadas às
  APIs.

## Consequências

- O modelo só vê horários e preços que vieram das ferramentas, e a regra de não haver conflito continua no
  banco: mesmo um modelo confuso não consegue agendar duas pessoas no mesmo horário.
- As ferramentas MCP têm testes de contrato com Catalog, Booking e Waitlist, como qualquer outro consumidor.
- O agente é testado com um modelo falso e um servidor MCP em memória. A qualidade das respostas de um
  modelo real depende do modelo e do hardware, e por isso não entra no CI.
- Modelos pequenos são mais lentos e erram mais que os de nuvem. Trocar o modelo é só uma variável de
  ambiente.

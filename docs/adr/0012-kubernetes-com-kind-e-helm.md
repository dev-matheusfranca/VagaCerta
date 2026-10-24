# ADR 0012 — Kubernetes com kind e Helm

**Status:** aceita

## Contexto

Até a fase 4, o VagaCerta rodava só no Docker Compose. Um ambiente real roda em Kubernetes, e é lá que
aparecem questões que o Compose esconde: ordem de subida, probes de prontidão, configuração por ambiente e
recriação de pods. O projeto não usa nuvem paga, então o cluster precisa rodar na máquina e no CI.

## Decisão

- **kind** como cluster local: um nó num container Docker, criado por `deploy/kind/up.sh`. O script
  constrói as imagens, carrega no nó e instala o chart. As NodePorts do gateway (8080), do Grafana (3000)
  e do Mailpit (8025) ficam nas mesmas portas do Compose.
- **Um chart Helm** (`deploy/helm/vagacerta`) com um template genérico: cada workload do `values.yaml`
  vira um Deployment e, se tiver portas, um Service. Um init container espera as dependências abrirem a
  porta, no papel do `depends_on`, e as probes de prontidão usam os mesmos endpoints dos healthchecks.
- **Configuração dentro das imagens.** Realm e tema do Keycloak, rotas do Traefik e dashboard do Grafana
  ganharam Dockerfiles próprios. O Compose passou a construir essas mesmas imagens, e a configuração fica
  num lugar só, sem cópia em ConfigMaps.
- **Um servidor PostgreSQL com um banco por serviço**, num StatefulSet com volume persistente. Cada serviço
  continua dono do seu banco e das suas migrações; só o processo do servidor é compartilhado, para caber
  na memória de uma máquina de desenvolvimento.
- **CI de ponta a ponta no cluster:** um job cria o kind no runner, instala o chart e roda o teste de carga
  do k6 contra o gateway.

## Consequências

- O mesmo `values.yaml` descreve todos os serviços. Adicionar um serviço é adicionar uma entrada.
- As migrações rodam na subida de cada API, como no Compose. Com mais de uma réplica, o certo seria um Job
  de migração antes do rollout.
- As credenciais são as de demonstração, em texto no `values.yaml`. Num ambiente real viriam de Secrets
  alimentados por um cofre.
- O assistente fica desligado por padrão no cluster, porque precisa de um Ollama alcançável
  (`WITH_ASSISTANT=1` liga).

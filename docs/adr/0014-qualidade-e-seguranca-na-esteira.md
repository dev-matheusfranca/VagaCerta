# ADR 0014 — Qualidade e segurança na esteira

**Status:** aceita

## Contexto

O CI conferia lint, tipos, testes e contratos, mas nada procurava segredos commitados, vulnerabilidades
conhecidas nas imagens e dependências ou problemas de configuração de containers. Todas as imagens
próprias rodavam como `root`, e a primeira varredura com o Trivy encontrou vulnerabilidades críticas no
Traefik, no Keycloak e no pacote do Grafana.

## Decisão

- **pre-commit** com ruff, checagens básicas de arquivos e **gitleaks**, que barra senhas e chaves antes
  do commit. O mesmo pre-commit roda no CI. O histórico inteiro foi varrido uma vez: nenhum segredo.
- **Cobertura de testes** com pytest-cov sobre todos os pacotes do workspace, inclusive módulos que
  nenhum teste importa, e análise estática e de cobertura no **SonarCloud**, gratuito para repositórios
  públicos.
- **Trivy** num job próprio:
  - dependências (`uv.lock`, `package-lock.json`) e configuração (Dockerfiles, Compose, chart Helm) vão
    para a aba *Security* do GitHub;
  - nas imagens que o projeto constrói, uma vulnerabilidade alta ou crítica com correção disponível
    quebra o build.
- **Imagens sem root:** os serviços Python rodam com um usuário próprio e sem o `pip` (ele embutia
  bibliotecas vulneráveis e não é usado em produção), o front usa a variante sem root do nginx e o
  gateway roda como usuário comum. No chart, as imagens próprias rodam com `securityContext` restrito:
  sem root, sem escalada de privilégio, sem capabilities do Linux e, nos serviços Python, com o sistema
  de arquivos somente leitura.
- **Bases atualizadas:** nginx 1.30 (o 1.29 saiu de suporte), Traefik 3.7, Keycloak 26.8 e otel-lgtm 0.38.
- **Actions de terceiros fixadas por commit**, para que uma tag movida não troque o código que roda no CI.

## Consequências

- As imagens próprias, o Traefik e o Keycloak ficaram sem vulnerabilidades altas ou críticas com
  correção. O pacote do Grafana caiu de 20 críticas e 607 altas para nenhuma crítica e 82 altas; ele é
  de terceiros e só para desenvolvimento, e por isso entra como exceção documentada em
  `.trivyignore.yaml`.
- Os alertas que restam no chart vêm das imagens de infraestrutura de terceiros (Kafka, RabbitMQ,
  PostgreSQL, Mailpit) rodando com o padrão delas e da falta de limites de CPU e memória. Ficam visíveis
  na aba *Security* como débito conhecido.
- Uma vulnerabilidade nova numa imagem base pode quebrar o build de um dia para o outro. O caminho é
  atualizar a base, que é o objetivo da regra.
- O SonarCloud depende de um token cadastrado nos secrets do repositório; sem ele, o passo é ignorado.

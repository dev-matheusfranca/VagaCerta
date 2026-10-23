# ADR 0006 — Keycloak para identidade e Traefik como API gateway

**Status:** aceita

## Contexto

A fase 3 trouxe usuários com permissões diferentes (donos de estabelecimento e administradores) e uma
chamada entre serviços que não pode ficar aberta ao público (a reserva de horários pelo Waitlist). O front
também passou a falar com quatro serviços e com o servidor de identidade.

## Decisão

- **Keycloak** é o provedor de identidade (OpenID Connect). O realm fica versionado em
  [`keycloak/vagacerta-realm.json`](../../keycloak/vagacerta-realm.json) e é importado na subida:
  - o front usa *authorization code* com **PKCE**, sem segredo no navegador;
  - o Waitlist usa *client credentials* com uma conta de serviço que tem só o papel `booking-holds`;
  - cada estabelecimento é um grupo, e o token traz os grupos do usuário na claim `businesses`;
  - os tokens incluem a audiência `vagacerta-api`.
- **Cada serviço valida o JWT** (assinatura RS256 pelas chaves públicas do realm, emissor, audiência e
  expiração) e checa papéis e grupos. Não há confiança implícita na rede interna.
- **Traefik** é o único ponto de entrada (porta 8080): serve o front, roteia `/api/<serviço>` e `/auth`,
  aplica cabeçalhos de segurança e limita gravações por cliente (rate limit).

## Consequências

- Mesmo uma requisição que chegue direto a um serviço, sem passar pelo gateway, precisa de um token válido
  com o papel certo.
- Front, APIs e Keycloak ficam na mesma origem, sem CORS.
- O emissor dos tokens é sempre a URL pública (`KC_HOSTNAME`), inclusive quando os serviços falam com o
  Keycloak pela rede interna, então todos validam o mesmo `iss`.
- O realm de demonstração tem senhas e segredo fixos; num ambiente real eles viriam de um cofre de
  segredos.

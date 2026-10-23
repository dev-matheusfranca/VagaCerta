from collections.abc import Callable
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

AUDIENCE = "vagacerta-api"
Claims = dict[str, Any]


class TokenVerifier:
    def __init__(self, issuer: str, signing_key: Callable[[str], Any]) -> None:
        self._issuer = issuer
        self._signing_key = signing_key

    def claims(self, token: str) -> Claims:
        return jwt.decode(
            token,
            self._signing_key(token),
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=self._issuer,
        )


def keycloak_verifier(issuer: str, jwks_url: str) -> TokenVerifier:
    jwks = jwt.PyJWKClient(jwks_url)
    return TokenVerifier(issuer, lambda token: jwks.get_signing_key_from_jwt(token).key)


def require_role(role: str) -> Callable[..., Claims]:
    # Dependência síncrona: o FastAPI a executa numa thread, e a busca das chaves não trava o loop.
    def dependency(
        request: Request,
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    ) -> Claims:
        try:
            claims: Claims = request.app.state.tokens.claims(credentials.credentials)
        except jwt.PyJWTError:
            raise HTTPException(401, "Token inválido ou expirado") from None
        if role not in claims.get("realm_access", {}).get("roles", []):
            raise HTTPException(403, "Acesso negado")
        return claims

    return dependency

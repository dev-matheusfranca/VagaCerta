import asyncio
import ipaddress
from urllib.parse import urlsplit


class ForbiddenTarget(ValueError):
    pass


async def check_target(url: str, allow_private: bool = False) -> None:
    """Recusa endereços da rede interna: o webhook não pode virar uma porta de entrada (SSRF).

    O nome é resolvido de novo a cada entrega, então um DNS que muda de ideia depois do cadastro
    também é barrado.
    """
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ForbiddenTarget("Use um endereço http ou https")
    if allow_private:
        return
    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(parts.hostname, parts.port or 443)
    except OSError:
        raise ForbiddenTarget("Não foi possível encontrar esse endereço") from None
    for *_, sockaddr in addresses:
        ip = ipaddress.ip_address(sockaddr[0])
        if not ip.is_global:
            raise ForbiddenTarget("Endereços da rede interna não são permitidos")

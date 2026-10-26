import hashlib
import json
from collections.abc import Iterable
from typing import Any

GENESIS = "0" * 64


def digest(prev_hash: str, topic: str, payload: dict[str, Any]) -> str:
    """Inclui o hash anterior, então alterar um registro invalida todos os seguintes."""
    content = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(f"{prev_hash}|{topic}|{content}".encode()).hexdigest()


def first_broken(records: Iterable[tuple[int, str, dict[str, Any], str, str]]) -> int | None:
    """Recalcula a corrente na ordem gravada e devolve o primeiro registro que não confere."""
    expected_prev = GENESIS
    for seq, topic, payload, prev_hash, stored_hash in records:
        if prev_hash != expected_prev or digest(prev_hash, topic, payload) != stored_hash:
            return seq
        expected_prev = stored_hash
    return None

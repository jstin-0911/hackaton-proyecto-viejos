"""Autenticación por token (un token por consumidor) y enmascarado de documentos."""

import hmac
import re

_BEARER = re.compile(r"^\s*Bearer\s+(\S+)\s*$", re.I)
_LONG_NUMBER = re.compile(r"\d{5,}")
VISIBLE_DIGITS = 4


def authenticate(header, tokens):
    """Devuelve el consumidor dueño del token o None. Compara en tiempo constante."""
    match = _BEARER.match(header or "")
    if not match:
        return None
    presented = match.group(1).encode("utf-8")
    found = None
    for consumer, token in tokens.items():
        if hmac.compare_digest(presented, token.encode("utf-8")):
            found = consumer
    return found


def mask_digits(text):
    """Enmascara todo número de 5 dígitos o más dejando visibles solo los últimos 4."""
    return _LONG_NUMBER.sub(lambda m: "*" * (len(m.group(0)) - VISIBLE_DIGITS) + m.group(0)[-VISIBLE_DIGITS:], text)

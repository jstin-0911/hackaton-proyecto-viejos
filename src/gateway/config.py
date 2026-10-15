"""Configuración del gateway: todo viene de variables de entorno (nada se escribe en el código)."""

import os
from dataclasses import dataclass, field
from typing import Dict, FrozenSet


def _float(name, default):
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return float(default)


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return int(default)


@dataclass(frozen=True)
class Settings:
    legacy_host: str
    legacy_port: int
    legacy_db: str
    legacy_user: str
    legacy_password: str
    connect_timeout: float
    tokens: Dict[str, str] = field(repr=False)
    write_consumers: FrozenSet[str]
    outbox_path: str
    outbox_interval: float
    max_pending: int
    audit_path: str
    state_dir: str
    default_mode: str
    breaker_cooldown: float
    legacy_deadline: float
    port: int

    @staticmethod
    def from_env():
        tokens = {
            "portal": os.environ.get("PORTAL_TOKEN", ""),
            "subsidios": os.environ.get("SUBSIDIOS_TOKEN", ""),
            "mobile": os.environ.get("MOBILE_TOKEN", ""),
        }
        writers = os.environ.get("GATEWAY_WRITE_CONSUMERS", "subsidios,portal")
        return Settings(
            legacy_host=os.environ.get("LEGACY_DB_HOST", "legacy-db"),
            legacy_port=_int("LEGACY_DB_PORT", 5432),
            legacy_db=os.environ.get("POSTGRES_DB", "legacy"),
            legacy_user=os.environ.get("POSTGRES_USER", "legacy"),
            legacy_password=os.environ.get("POSTGRES_PASSWORD", ""),
            connect_timeout=_float("LEGACY_CONNECT_TIMEOUT", 1),
            tokens={name: value for name, value in tokens.items() if value},
            write_consumers=frozenset(c.strip().lower() for c in writers.split(",") if c.strip() and c.strip().lower() != "mobile"),
            outbox_path=os.environ.get("OUTBOX_PATH", "/data/outbox.db"),
            outbox_interval=_float("OUTBOX_INTERVAL_SECONDS", 2),
            max_pending=_int("OUTBOX_MAX_PENDING", 10000),
            audit_path=os.environ.get("AUDIT_LOG_PATH", "/app/logs/audit.log"),
            state_dir=os.environ.get("STATE_DIR", "/state"),
            default_mode=os.environ.get("AFFILIATIONS_DEFAULT_MODE", "DUAL").upper(),
            breaker_cooldown=_float("BREAKER_COOLDOWN_SECONDS", 1),
            legacy_deadline=_float("LEGACY_DEADLINE_SECONDS", 2.5),
            port=_int("GATEWAY_INTERNAL_PORT", 8082),
        )

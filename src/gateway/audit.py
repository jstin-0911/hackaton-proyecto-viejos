"""Auditoría: una línea JSON por petición. Nunca se registran cuerpos ni documentos completos."""

import json
import threading
from datetime import datetime, timezone

from gateway.security import mask_digits


class AuditLog:
    def __init__(self, path):
        self._path = path
        self._lock = threading.Lock()

    def write(self, consumer, method, endpoint, status, latency_ms, request_id):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "consumer": consumer,
            "method": method,
            "endpoint": mask_digits(endpoint),
            "status": status,
            "latency_ms": latency_ms,
            "request_id": request_id,
        }
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        with self._lock:
            try:
                with open(self._path, "a", encoding="utf-8") as handle:
                    handle.write(line)
            except OSError:
                # La auditoría no debe tumbar el servicio; el fallo queda en stderr.
                import sys
                sys.stderr.write("AUDIT_WRITE_FAILED " + line)

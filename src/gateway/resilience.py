"""Interruptor de circuito + plazo máximo por llamada al legacy.

* Plazo: ninguna llamada espera más de `deadline` segundos (incluye resolución DNS y conexión, que el
  timeout del driver no cubre). Si vence, se responde como "legacy no disponible".
* Circuito: tras una falla, durante `cooldown` segundos se responde de inmediato sin tocar la base; pasado
  ese tiempo deja pasar UNA llamada de prueba. Así una caída no se convierte en una avalancha de conexiones.

Un plazo vencido puede dejar una escritura "en vuelo"; es seguro porque el registro de retiros es idempotente.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from gateway.errors import LegacyUnavailable


class LegacyGuard:
    def __init__(self, cooldown, deadline=2.5, workers=64):
        self._cooldown = cooldown
        self._deadline = deadline
        self._opened_at = None
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="legacy")

    def state(self):
        with self._lock:
            opened = self._opened_at is not None and (time.monotonic() - self._opened_at) < self._cooldown
            return "OPEN" if opened else "CLOSED"

    def _admit(self):
        with self._lock:
            if self._opened_at is None:
                return
            if (time.monotonic() - self._opened_at) < self._cooldown:
                raise LegacyUnavailable("circuito abierto")
            self._opened_at = time.monotonic()  # esta llamada es la de prueba; las demás siguen esperando

    def call(self, fn, *args):
        self._admit()
        future = self._pool.submit(fn, *args)
        try:
            result = future.result(timeout=self._deadline)
        except FutureTimeout:
            self._trip()
            raise LegacyUnavailable("plazo vencido")
        except LegacyUnavailable:
            self._trip()
            raise
        with self._lock:
            self._opened_at = None
        return result

    def _trip(self):
        with self._lock:
            self._opened_at = time.monotonic()

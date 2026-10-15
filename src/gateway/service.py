"""Casos de uso del gateway. Habla solo en modelo canónico; el adapter resuelve el legacy."""

import logging
import re
import threading
import time
from datetime import date as date_type

from gateway import outbox as ob
from gateway.canonical import CONFLICT, CREATED, DUPLICATE, NOT_FOUND
from gateway.errors import ApiError, LegacyError, LegacyUnavailable, not_found, validation

log = logging.getLogger("gateway")

_DOCUMENT = re.compile(r"^[0-9]{1,15}$")
_COMPANY = re.compile(r"^[0-9A-Za-z]{1,10}$")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:\-]{1,80}$")
MAX_ATTEMPTS = 20
LEGACY_DOWN_MESSAGE = "El sistema legacy no está disponible. Intente de nuevo en unos minutos."


def legacy_unavailable():
    return ApiError(503, "LEGACY_UNAVAILABLE", LEGACY_DOWN_MESSAGE)


class GatewayService:
    def __init__(self, repository, guard, outbox, migration, max_pending):
        self._repo = repository
        self._guard = guard
        self._outbox = outbox
        self._migration = migration
        self._max_pending = max_pending
        self._started = time.time()

    # ------------------------------------------------------------------ lecturas
    def health(self):
        try:
            self._guard.call(self._repo.ping)
            legacy = "UP"
        except (LegacyUnavailable, LegacyError):
            legacy = "DOWN"
        return {"status": "UP", "legacy": legacy}

    def _read(self, fn, *args):
        try:
            return self._guard.call(fn, *args)
        except LegacyUnavailable:
            raise legacy_unavailable()

    def member(self, document):
        if not _DOCUMENT.match(document):
            raise not_found("Afiliado no encontrado")
        member = self._read(self._repo.get_member, document)
        if member is None:
            raise not_found("Afiliado no encontrado")
        return member.to_dict()

    def beneficiaries(self, document):
        if not _DOCUMENT.match(document):
            raise not_found("Afiliado no encontrado")
        items = self._read(self._repo.list_beneficiaries, document)
        if items is None:
            raise not_found("Afiliado no encontrado")
        return [b.to_dict() for b in items]

    def company(self, company_id):
        if not _COMPANY.match(company_id):
            raise not_found("Empresa no encontrada")
        company = self._read(self._repo.get_company, company_id)
        if company is None:
            raise not_found("Empresa no encontrada")
        return company.to_dict()

    def migration_status(self):
        return self._migration.snapshot()

    # ------------------------------------------------------------------ retiros
    @staticmethod
    def _parse_retirement(body):
        if not isinstance(body, dict):
            raise validation("El cuerpo debe ser un objeto JSON con requestId, date y reason")
        request_id = body.get("requestId")
        if not isinstance(request_id, str) or not _REQUEST_ID.match(request_id):
            raise validation("requestId es obligatorio (1-80 caracteres: letras, números, . _ : -)")
        raw_date = body.get("date")
        try:
            parsed = date_type.fromisoformat(raw_date) if isinstance(raw_date, str) and len(raw_date) == 10 else None
        except ValueError:
            parsed = None
        if parsed is None:
            raise validation("date es obligatorio con formato AAAA-MM-DD")
        reason = body.get("reason", "RETIRO")
        if reason is None or reason == "":
            reason = "RETIRO"
        if not isinstance(reason, str) or len(reason) > 200:
            raise validation("reason debe ser texto de máximo 200 caracteres")
        return request_id, parsed.isoformat(), reason

    def retire(self, consumer, document, body):
        """Devuelve (http_status, cuerpo). Idempotente por requestId; si el legacy cae, encola (202)."""
        request_id, on_date, reason = self._parse_retirement(body)
        if not _DOCUMENT.match(document):
            raise not_found("Afiliado no encontrado")
        existing = self._outbox.get(request_id)
        fresh = existing is None
        if existing is not None and existing["status"] == ob.FAILED:
            self._outbox.delete(request_id)
            existing, fresh = None, True
        if existing is not None:
            same = (existing["document"], existing["retirement_date"], existing["reason"]) == (document, on_date, reason)
            if not same:
                raise ApiError(409, "REQUEST_ID_CONFLICT", "El requestId ya se usó con datos distintos")
            if existing["status"] == ob.APPLIED:
                return 200, self._applied_body(request_id, existing["movement_id"])
        else:
            self._outbox.add_pending(request_id, document, on_date, reason, consumer.upper())
        record = self._outbox.get(request_id)
        try:
            outcome = self._guard.call(self._repo.register_retirement, request_id, document, on_date, reason,
                                       record["actor"])
        except LegacyUnavailable:
            if fresh and self._outbox.counts()[ob.PENDING] > self._max_pending:
                self._outbox.delete(request_id)
                raise ApiError(503, "QUEUE_FULL", "La cola de retiros está llena; intente más tarde.")
            return 202, self._pending_body(request_id)
        except Exception:
            # Falla inesperada (no es una caída): no dejamos un pendiente que el cliente no sabe que existe.
            if fresh:
                self._outbox.delete(request_id)
            raise
        return self._settle(request_id, outcome, fresh)

    def _settle(self, request_id, outcome, fresh):
        if outcome.status in (CREATED, DUPLICATE):
            self._outbox.mark_applied(request_id, outcome.movement_id)
            return (201 if outcome.status == CREATED else 200), self._applied_body(request_id, outcome.movement_id)
        if fresh:
            self._outbox.delete(request_id)
        else:
            self._outbox.mark_failed(request_id, outcome.status)
        if outcome.status == NOT_FOUND:
            raise not_found("Afiliado no encontrado")
        raise ApiError(409, "REQUEST_ID_CONFLICT", "El requestId ya se usó con otro afiliado")

    @staticmethod
    def _applied_body(request_id, movement_id):
        return {"requestId": request_id, "status": ob.APPLIED, "movementId": movement_id}

    @staticmethod
    def _pending_body(request_id):
        return {"requestId": request_id, "status": ob.PENDING,
                "message": "El legacy no está disponible: el retiro quedó en cola y se aplicará una sola vez al recuperarse."}

    def retirement_status(self, request_id):
        record = self._outbox.get(request_id) if _REQUEST_ID.match(request_id) else None
        if record is None:
            raise not_found("Retiro no encontrado")
        body = {"requestId": request_id, "status": record["status"], "attempts": record["attempts"]}
        if record["movement_id"] is not None:
            body["movementId"] = record["movement_id"]
        if record["status"] == ob.FAILED:
            body["reason"] = record["last_error"]
        return body

    # ------------------------------------------------------------------ cola
    def drain_outbox(self):
        """Aplica los retiros en cola. Seguro de repetir: la idempotencia vive en el legacy."""
        applied = 0
        for record in self._outbox.pending(50):
            try:
                outcome = self._guard.call(self._repo.register_retirement, record["request_id"], record["document"],
                                           record["retirement_date"], record["reason"], record["actor"])
            except LegacyUnavailable:
                break
            except Exception as exc:
                # Retiro "venenoso": se reintenta unas veces y luego se aparta para no bloquear la cola.
                self._outbox.bump_attempt(record["request_id"], exc.__class__.__name__)
                log.error("outbox: fallo inesperado aplicando %s: %s", record["request_id"], exc.__class__.__name__)
                if record["attempts"] + 1 >= MAX_ATTEMPTS:
                    self._outbox.mark_failed(record["request_id"], "TOO_MANY_ATTEMPTS")
                continue
            if outcome.status in (CREATED, DUPLICATE):
                self._outbox.mark_applied(record["request_id"], outcome.movement_id)
                applied += 1
            else:
                self._outbox.mark_failed(record["request_id"], outcome.status)
                log.error("outbox: retiro %s descartado (%s)", record["request_id"], outcome.status)
        return applied

    def stats(self):
        return {"uptimeSeconds": int(time.time() - self._started), "circuit": self._guard.state(),
                "retirements": self._outbox.counts()}


class OutboxWorker(threading.Thread):
    def __init__(self, service, outbox, interval):
        super().__init__(name="outbox-worker", daemon=True)
        self._service, self._outbox, self._interval = service, outbox, interval
        self._stop_event = threading.Event()
        self._last_purge = 0.0

    def run(self):
        while not self._stop_event.wait(self._interval):
            try:
                self._service.drain_outbox()
                if time.time() - self._last_purge > 3600:
                    self._outbox.purge_applied()
                    self._last_purge = time.time()
            except Exception:  # el worker nunca debe morir
                log.exception("outbox worker")

    def stop(self):
        self._stop_event.set()

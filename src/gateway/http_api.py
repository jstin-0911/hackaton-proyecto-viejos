"""Borde HTTP: rutas, autenticación, errores uniformes y auditoría."""

import json
import logging
import re
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from gateway.errors import ApiError, LegacyError, validation
from gateway.security import authenticate

log = logging.getLogger("gateway")
MAX_BODY = 16 * 1024

# (método, expresión, nombre, requiere escritura)
ROUTES = [
    ("GET", re.compile(r"^/health$"), "health", False),
    ("GET", re.compile(r"^/api/v1/members/([^/]+)$"), "member", False),
    ("GET", re.compile(r"^/api/v1/members/([^/]+)/beneficiaries$"), "beneficiaries", False),
    ("GET", re.compile(r"^/api/v1/companies/([^/]+)$"), "company", False),
    ("POST", re.compile(r"^/api/v1/members/([^/]+)/retirements$"), "retire", True),
    ("GET", re.compile(r"^/api/v1/retirements/([^/]+)$"), "retirement_status", False),
    ("GET", re.compile(r"^/api/v1/migration/status$"), "migration", False),
    ("GET", re.compile(r"^/api/v1/ops/stats$"), "stats", False),
]


class Application:
    def __init__(self, settings, service, audit):
        self.settings = settings
        self.service = service
        self.audit = audit


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        timeout = 15
        server_version = "gateway"
        sys_version = ""

        # ------------------------------------------------------------ salida
        def _send(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._status = status
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Request-Id", self._request_id)
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _error(self, exc):
            error_id = uuid.uuid4().hex[:12]
            if exc.status >= 500:
                log.warning("error_id=%s code=%s", error_id, exc.code)
            self._send(exc.status, {"message": exc.message, "error_id": error_id, "code": exc.code})

        # ------------------------------------------------------------ entrada
        def _read_json(self):
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                raise validation("Content-Length inválido")
            if length > MAX_BODY:
                raise ApiError(413, "PAYLOAD_TOO_LARGE", "El cuerpo excede el máximo permitido")
            raw = self.rfile.read(length) if length else b""
            try:
                return json.loads(raw.decode("utf-8")) if raw else {}
            except (ValueError, UnicodeDecodeError):
                raise validation("El cuerpo no es un JSON válido")

        def _dispatch(self, method):
            started = time.perf_counter()
            self._status = 500
            self._request_id = self.headers.get("X-Request-Id", "")[:64] or uuid.uuid4().hex[:16]
            path = self.path.split("?", 1)[0]
            consumer = "anonymous"
            try:
                if path != "/health":
                    found = authenticate(self.headers.get("Authorization"), app.settings.tokens)
                    if found is None:
                        raise ApiError(401, "UNAUTHORIZED", "Credenciales ausentes o inválidas")
                    consumer = found
                handler = self._route(method, path, consumer)
                handler()
            except ApiError as exc:
                self._error(exc)
            except LegacyError:
                self._error(ApiError(500, "INTERNAL_ERROR", "Error interno del servicio"))
            except Exception:
                log.exception("error no controlado")
                self._error(ApiError(500, "INTERNAL_ERROR", "Error interno del servicio"))
            finally:
                latency = int((time.perf_counter() - started) * 1000)
                app.audit.write(consumer, method, path, self._status, latency, self._request_id)

        def _route(self, method, path, consumer):
            allowed = []
            for verb, pattern, name, writes in ROUTES:
                match = pattern.match(path)
                if not match:
                    continue
                allowed.append(verb)
                if verb != method:
                    continue
                if writes and consumer not in app.settings.write_consumers:
                    raise ApiError(403, "FORBIDDEN", "El consumidor no tiene permiso de escritura")
                return lambda: getattr(self, "_h_" + name)(*match.groups())
            if allowed:
                raise ApiError(405, "METHOD_NOT_ALLOWED", "Método no permitido")
            raise ApiError(404, "NOT_FOUND", "Ruta no encontrada")

        # ------------------------------------------------------------ rutas
        def _h_health(self):
            self._send(200, app.service.health())

        def _h_member(self, document):
            self._send(200, app.service.member(document))

        def _h_beneficiaries(self, document):
            self._send(200, app.service.beneficiaries(document))

        def _h_company(self, company_id):
            self._send(200, app.service.company(company_id))

        def _h_retire(self, document):
            consumer = authenticate(self.headers.get("Authorization"), app.settings.tokens)
            status, body = app.service.retire(consumer, document, self._read_json())
            self._send(status, body)

        def _h_retirement_status(self, request_id):
            self._send(200, app.service.retirement_status(request_id))

        def _h_migration(self):
            self._send(200, app.service.migration_status())

        def _h_stats(self):
            self._send(200, app.service.stats())

        # ------------------------------------------------------------ verbos
        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        def do_PUT(self):
            self._dispatch("PUT")

        def do_PATCH(self):
            self._dispatch("PATCH")

        def do_DELETE(self):
            self._dispatch("DELETE")

        def log_message(self, fmt, *args):
            return

    return Handler


def make_server(app, port):
    class Server(ThreadingHTTPServer):
        daemon_threads = True
        request_queue_size = 128

    return Server(("0.0.0.0", port), make_handler(app))

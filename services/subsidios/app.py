"""subsidios-app — registra retiros de afiliados (SÍ se puede modificar).

Dominio Afiliaciones en transición (LEGACY -> DUAL -> MODERN):
  * DUAL / MODERN: el retiro se registra por el gateway (POST /api/v1/members/{doc}/retirements)
    con SUBSIDIOS_TOKEN. El gateway es idempotente y, si el legacy está caído, lo encola (202).
  * LEGACY: camino original, directo a sp_registrar_retiro. Es el destino de ./rollback.sh y
    funciona aunque el gateway esté detenido.

El modo se lee del archivo de estado compartido en cada petición, por eso el rollback es inmediato.

POST /retiros  {"documento": "...", "fecha": "YYYY-MM-DD", "motivo": "...", "requestId": "(opcional)"}  (puerto 8091)
"""

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psycopg2

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://gateway:8082").rstrip("/")
TOKEN = os.environ.get("SUBSIDIOS_TOKEN", "")
MODE_FILE = os.environ.get("SUBSIDIOS_MODE_FILE", "/state/affiliations.mode")
DEFAULT_MODE = os.environ.get("AFFILIATIONS_DEFAULT_MODE", "DUAL").strip().upper()
GATEWAY_RETRIES = 3


def current_mode():
    try:
        with open(MODE_FILE, encoding="utf-8") as handle:
            value = handle.read().strip().upper()
    except OSError:
        value = DEFAULT_MODE
    return value if value in ("LEGACY", "DUAL", "MODERN") else "DUAL"


# --------------------------------------------------------------------------- camino legacy (rollback)
def connect():
    return psycopg2.connect(
        host=os.environ.get("LEGACY_DB_HOST", "legacy-db"),
        port=int(os.environ.get("LEGACY_DB_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "legacy"),
        user=os.environ.get("POSTGRES_USER", "legacy"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
        connect_timeout=2,
    )


def registrar_retiro_legacy(documento, fecha, motivo):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT sp_registrar_retiro(%s, %s, %s, %s)", (documento, fecha, motivo, "SUBSIDIOS"))
            movimiento = cur.fetchone()[0]
        conn.commit()
        return movimiento
    finally:
        conn.close()


# --------------------------------------------------------------------------- camino nuevo (gateway)
def request_id_for(data):
    """requestId estable: reintentar el mismo retiro nunca crea un segundo movimiento (incidente 2021-07)."""
    if data.get("requestId"):
        return str(data["requestId"])
    basis = "|".join([str(data.get("documento")), str(data.get("fecha")), str(data.get("motivo", "RETIRO"))])
    return "subsidios-" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32]


def registrar_retiro_gateway(data):
    payload = json.dumps({"requestId": request_id_for(data), "date": data["fecha"],
                          "reason": data.get("motivo", "RETIRO")}).encode("utf-8")
    url = "{0}/api/v1/members/{1}/retirements".format(GATEWAY_URL, data["documento"])
    last_error = None
    for attempt in range(GATEWAY_RETRIES):
        request = urllib.request.Request(url, data=payload, method="POST", headers={
            "Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=8) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read().decode("utf-8") or "{}")
            except ValueError:
                return exc.code, {}
        except (urllib.error.URLError, OSError) as exc:
            last_error = exc
            time.sleep(0.4 * (attempt + 1))
    return 502, {"message": "Gateway no disponible: {0}".format(last_error.__class__.__name__)}


def translate(status, body):
    """Mantiene la respuesta histórica {"movimiento": id} y agrega el estado del nuevo camino."""
    if status in (200, 201):
        return status, {"movimiento": body.get("movementId"), "requestId": body.get("requestId"), "via": "gateway"}
    if status == 202:
        return 202, {"estado": "PENDIENTE", "requestId": body.get("requestId"), "via": "gateway",
                     "mensaje": "Legacy no disponible: el retiro se aplicará automáticamente, una sola vez"}
    if status == 404:
        return 404, {"error": "afiliado no encontrado"}
    if status in (400, 409):
        return status, {"error": body.get("message", "solicitud inválida")}
    return (503 if status == 503 else 502), {"error": body.get("message", "servicio de retiros no disponible")}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "UP", "modo": "legacy" if current_mode() == "LEGACY" else "gateway",
                                    "affiliations": current_mode()})
        return self._send(404, {"error": "ruta no encontrada"})

    def do_POST(self):
        if self.path != "/retiros":
            return self._send(404, {"error": "ruta no encontrada"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(data, dict) or not data.get("documento") or not data.get("fecha"):
                raise ValueError("faltan documento y fecha")
        except (ValueError, TypeError) as exc:
            return self._send(400, {"error": "cuerpo inválido: " + str(exc)})
        if current_mode() == "LEGACY":
            try:
                movimiento = registrar_retiro_legacy(data["documento"], data["fecha"], data.get("motivo", "RETIRO"))
            except psycopg2.OperationalError:
                return self._send(503, {"error": "base legacy no disponible"})
            except psycopg2.Error as exc:
                if "AFI-404" in str(exc):
                    return self._send(404, {"error": "afiliado no encontrado"})
                return self._send(500, {"error": "no se pudo registrar el retiro"})
            return self._send(201, {"movimiento": movimiento, "via": "legacy"})
        status, body = registrar_retiro_gateway(data)
        return self._send(*translate(status, body))

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8091), Handler).serve_forever()

"""portal-client — portal de servicios (NO se modifica; solo se configura GATEWAY_URL).

GET /portal/afiliados/{documento}  (puerto 8092)
Consulta el gateway con PORTAL_TOKEN y arma la ficha del afiliado:
afiliado + beneficiarios + empresa. No conoce tablas, columnas ni códigos legacy.
"""

import json
import os
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://gateway:8082").rstrip("/")
TOKEN = os.environ.get("PORTAL_TOKEN", "")
ROUTE = re.compile(r"^/portal/afiliados/([0-9]+)$")


def call(path):
    request = urllib.request.Request(GATEWAY_URL + path, headers={"Authorization": "Bearer " + TOKEN})
    try:
        with urllib.request.urlopen(request, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        except ValueError:
            return exc.code, {}
    except Exception as exc:
        return 502, {"message": "Gateway no disponible: {0}".format(exc.__class__.__name__)}


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
            return self._send(200, {"status": "UP", "gateway": GATEWAY_URL})
        match = ROUTE.match(self.path)
        if not match:
            return self._send(404, {"message": "ruta no encontrada"})
        doc = match.group(1)
        status, member = call("/api/v1/members/" + doc)
        if status != 200:
            return self._send(status, member)
        _, beneficiaries = call("/api/v1/members/{0}/beneficiaries".format(doc))
        company = member.get("company") or {}
        _, company_detail = call("/api/v1/companies/{0}".format(company.get("id", "")))
        return self._send(200, {"afiliado": member, "beneficiarios": beneficiaries, "empresa": company_detail})

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8092), Handler).serve_forever()

"""Interfaz web del portal; el token de acceso permanece en el servidor."""

import json
import os
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

PORT = int(os.environ.get("PORTAL_UI_INTERNAL_PORT", "8093"))
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://gateway:8082").rstrip("/")
TOKEN = os.environ.get("PORTAL_TOKEN", "")
STATIC_DIR = Path(__file__).parent / "static"
MEMBER_ROUTE = re.compile(r"^/api/member/([0-9]{1,20})$")
ASSETS = {
    "/assets/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/assets/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


def call_gateway(path):
    request = urllib.request.Request(
        GATEWAY_URL + path,
        headers={"Authorization": "Bearer " + TOKEN, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return exc.code, {"message": "No fue posible completar la consulta."}
    except Exception:
        return 502, {"message": "El servicio no está disponible temporalmente."}


class Handler(BaseHTTPRequestHandler):
    server_version = "PortalUI"
    sys_version = ""

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ("/", "/index.html"):
            return self._static("index.html", "text/html; charset=utf-8")
        if path in ASSETS:
            filename, content_type = ASSETS[path]
            return self._static(filename, content_type)
        if path == "/api/health":
            status, health = call_gateway("/health")
            return self._json(200 if status == 200 else 503, health)

        match = MEMBER_ROUTE.fullmatch(path)
        if match:
            document = match.group(1)
            status, member = call_gateway("/api/v1/members/" + document)
            if status != 200:
                return self._json(status, member)
            _, beneficiaries = call_gateway(
                "/api/v1/members/{0}/beneficiaries".format(document)
            )
            company = member.get("company") or {}
            company_id = str(company.get("id", ""))
            _, company_detail = call_gateway("/api/v1/companies/" + company_id)
            return self._json(
                200,
                {
                    "member": member,
                    "beneficiaries": beneficiaries,
                    "company": company_detail,
                },
            )
        return self._json(404, {"message": "ruta no encontrada"})

    def _static(self, filename, content_type):
        try:
            body = (STATIC_DIR / filename).read_bytes()
        except OSError:
            return self._json(404, {"message": "recurso no encontrado"})
        self._send(200, body, content_type)

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

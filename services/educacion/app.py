"""educacion-app — aplicación de Educación (NO SE PUEDE MODIFICAR).

Lee los afiliados directamente de la base legacy, como lo ha hecho por años.
Expone lo que ve en GET /afiliados/{documento} (puerto 8090).
Tras el cambio de esquema el equipo de Educación recibió el aviso del DBA y su
consulta usa PERSON_MASTER si AFI_MAE ya no existe.
"""

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psycopg2

ESTADOS = {"A": "ACTIVO", "R": "RETIRADO", "S": "SUSPENDIDO"}
ROUTE = re.compile(r"^/afiliados/([0-9]+)$")
QUERIES = [
    "SELECT a.nro_doc, a.nom1, a.nom2, a.ape1, a.ape2, a.est_afi, e.nom_emp FROM afi_mae a LEFT JOIN empresa e ON e.cod_emp = a.cod_emp WHERE a.nro_doc = %s",
    "SELECT a.document_number, a.nom1, a.nom2, a.ape1, a.ape2, a.status_code, e.nom_emp FROM person_master a LEFT JOIN empresa e ON e.cod_emp = a.cod_emp WHERE a.document_number = %s",
]


def connect():
    return psycopg2.connect(
        host=os.environ.get("LEGACY_DB_HOST", "legacy-db"),
        port=int(os.environ.get("LEGACY_DB_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "legacy"),
        user=os.environ.get("POSTGRES_USER", "legacy"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
        connect_timeout=2,
    )


def find(documento):
    conn = connect()
    conn.autocommit = True
    try:
        for query in QUERIES:
            try:
                with conn.cursor() as cur:
                    cur.execute(query, (documento,))
                    return cur.fetchone()
            except psycopg2.errors.UndefinedTable:
                continue
        return None
    finally:
        conn.close()


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
            return self._send(200, {"status": "UP"})
        match = ROUTE.match(self.path)
        if not match:
            return self._send(404, {"error": "ruta no encontrada"})
        try:
            row = find(match.group(1))
        except psycopg2.OperationalError:
            return self._send(503, {"error": "base de datos no disponible"})
        if row is None:
            return self._send(404, {"error": "afiliado no encontrado"})
        nombre = " ".join(p for p in row[1:5] if p)
        return self._send(200, {"documento": row[0], "nombre": nombre, "estado": ESTADOS.get(row[5], row[5]), "empresa": row[6]})

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8090), Handler).serve_forever()

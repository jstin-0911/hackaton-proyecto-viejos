"""Fixtures de las pruebas del gateway.

Las pruebas hablan con la API en funcionamiento. Para verificar el efecto en el legacy (y limpiar lo
que escriben) usan una conexión directa: está permitido solo para el servicio `tests`.
Todo lo que modifican se restaura al terminar, para no alterar los datos de otras validaciones.
"""

import os
import uuid

import psycopg2
import pytest
import requests

GATEWAY = os.environ.get("GATEWAY_BASE_URL", "http://gateway:8082").rstrip("/")
SUBSIDIOS = os.environ.get("SUBSIDIOS_BASE_URL", "http://subsidios-app:8091").rstrip("/")
EDUCACION = os.environ.get("EDUCACION_BASE_URL", "http://educacion-app:8090").rstrip("/")
AUDIT_LOG = os.environ.get("AUDIT_LOG_PATH", "/logs/audit.log")


def pytest_configure(config):
    config.addinivalue_line("markers", "writes: la prueba registra retiros (se restauran al terminar)")


class Api:
    def __init__(self):
        self.tokens = {"portal": os.environ["PORTAL_TOKEN"], "subsidios": os.environ["SUBSIDIOS_TOKEN"],
                       "mobile": os.environ["MOBILE_TOKEN"]}

    def get(self, path, consumer="portal"):
        headers = {"Authorization": "Bearer " + self.tokens[consumer]} if consumer else {}
        return requests.get(GATEWAY + path, headers=headers, timeout=10)

    def post(self, path, body, consumer="subsidios"):
        headers = {"Authorization": "Bearer " + self.tokens[consumer]} if consumer else {}
        return requests.post(GATEWAY + path, json=body, headers=headers, timeout=10)


class Legacy:
    """Acceso directo de solo verificación y limpieza (esquema original o renombrado)."""

    def __init__(self):
        self.params = dict(host=os.environ.get("LEGACY_DB_HOST", "legacy-db"), port=int(os.environ.get("LEGACY_DB_PORT", "5432")),
                           dbname=os.environ.get("POSTGRES_DB", "legacy"), user=os.environ.get("POSTGRES_USER", "legacy"),
                           password=os.environ.get("POSTGRES_PASSWORD", ""), connect_timeout=5)

    def query(self, sql, args=(), commit=False):
        conn = psycopg2.connect(**self.params)
        try:
            with conn.cursor() as cur:
                cur.execute(sql, args)
                rows = cur.fetchall() if cur.description else []
            if commit:
                conn.commit()
            return rows
        finally:
            conn.close()

    def master(self):
        renamed = self.query("SELECT to_regclass('public.person_master') IS NOT NULL")[0][0]
        return ("person_master", "document_number", "status_code") if renamed else ("afi_mae", "nro_doc", "est_afi")

    def retirement_rows(self, document):
        return self.query("SELECT count(*) FROM logmov WHERE nro_doc = %s AND tip_mov = 'RET'", (document,))[0][0]

    def status_of(self, document):
        table, doc, status = self.master()
        return self.query("SELECT {0} FROM {1} WHERE {2} = %s".format(status, table, doc), (document,))[0][0]


@pytest.fixture(scope="session")
def api():
    return Api()


@pytest.fixture(scope="session")
def legacy():
    return Legacy()


@pytest.fixture(scope="session")
def sample_member(legacy):
    """Un afiliado activo con beneficiarios (solo lectura)."""
    table, doc, status = legacy.master()
    rows = legacy.query("SELECT m.{0} FROM {1} m JOIN afi_ben b ON b.nro_doc = m.{0} WHERE m.{2} = 'A' "
                        "ORDER BY m.{0} LIMIT 1".format(doc, table, status))
    return rows[0][0]


@pytest.fixture
def retirable(legacy):
    """Un afiliado ACTIVO distinto en cada prueba; se restaura al terminar."""
    table, doc, status = legacy.master()
    document = legacy.query("SELECT {0} FROM {1} WHERE {2} = 'A' ORDER BY {0} DESC OFFSET %s LIMIT 1".format(doc, table, status),
                            (int(uuid.uuid4().int % 20),))[0][0]
    original = legacy.query("SELECT {0}, fec_ret FROM {1} WHERE {2} = %s".format(status, table, doc), (document,))[0]
    max_before = legacy.query("SELECT coalesce(max(id_mov), 0) FROM logmov")[0][0]
    created = []
    yield document, created
    legacy.query("UPDATE {0} SET {1} = %s, fec_ret = %s WHERE {2} = %s".format(table, status, doc), (original[0], original[1], document), commit=True)
    legacy.query("DELETE FROM logmov WHERE id_mov > %s AND nro_doc = %s", (max_before, document), commit=True)
    if created:
        exists = legacy.query("SELECT to_regclass('public.gw_retiro_request') IS NOT NULL")[0][0]
        if exists:
            legacy.query("DELETE FROM gw_retiro_request WHERE request_id = ANY(%s)", (created,), commit=True)


def new_request_id(prefix="it"):
    return "{0}-{1}".format(prefix, uuid.uuid4().hex[:16])

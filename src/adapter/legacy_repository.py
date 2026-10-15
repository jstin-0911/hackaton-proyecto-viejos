"""Adapter hacia la base legacy: ÚNICO lugar que conoce tablas, columnas, códigos y procedimientos.

Traduce el esquema legacy (original o ya renombrado por el DBA) al modelo canónico.
Detecta el esquema en cada consulta, por eso el cambio de esquema no requiere reiniciar nada.
"""

import contextlib
from collections import namedtuple

import psycopg2

from gateway.canonical import (CONFLICT, CREATED, DUPLICATE, NOT_FOUND, Beneficiary, Company, CompanyRef, Member,
                               RetirementOutcome)
from gateway.errors import LegacyError, LegacyUnavailable

Schema = namedtuple("Schema", "master doc status")
ORIGINAL = Schema(master="afi_mae", doc="nro_doc", status="est_afi")
RENAMED = Schema(master="person_master", doc="document_number", status="status_code")

STATUS_FROM_LEGACY = {"A": "ACTIVE", "R": "RETIRED", "S": "SUSPENDED"}
RELATIONSHIP_FROM_LEGACY = {"C": "SPOUSE", "H": "CHILD", "P": "FATHER", "M": "MOTHER"}
ACTIVE_CODE = "A"

# Tabla propia del gateway para la idempotencia. Se escribe en la misma transacción que el
# procedimiento legacy, así "una sola vez" no depende de que el gateway sobreviva a un corte.
REQUEST_TABLE = "gw_retiro_request"
REQUEST_LOCK = 727401


def _full_name(*parts):
    return " ".join(p.strip() for p in parts if p and p.strip())


def _status(code):
    # Un código desconocido nunca se presenta como ACTIVE: se trata como no apto.
    return STATUS_FROM_LEGACY.get((code or "").strip().upper(), "SUSPENDED")


class LegacyRepository:
    def __init__(self, host, port, dbname, user, password, connect_timeout=1.0):
        self._params = dict(host=host, port=port, dbname=dbname, user=user, password=password,
                            connect_timeout=max(1, int(round(connect_timeout))),
                            options="-c statement_timeout=2500 -c lock_timeout=2000",
                            application_name="gateway-adapter", client_encoding="UTF8")

    # ------------------------------------------------------------------ conexión
    @contextlib.contextmanager
    def _session(self, autocommit=True):
        try:
            conn = psycopg2.connect(**self._params)
        except psycopg2.Error as exc:
            raise LegacyUnavailable(exc.__class__.__name__) from exc
        try:
            conn.autocommit = autocommit
            with conn.cursor() as cur:
                yield conn, cur
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as exc:
            raise LegacyUnavailable(exc.__class__.__name__) from exc
        except psycopg2.Error as exc:
            raise LegacyError(exc.__class__.__name__) from exc
        finally:
            conn.close()

    @staticmethod
    def _schema(cur):
        cur.execute("SELECT to_regclass('public.person_master') IS NOT NULL")
        return RENAMED if cur.fetchone()[0] else ORIGINAL

    # ------------------------------------------------------------------ consultas
    def ping(self):
        with self._session() as (_, cur):
            cur.execute("SELECT 1")
            return cur.fetchone()[0] == 1

    def get_member(self, document):
        with self._session() as (_, cur):
            s = self._schema(cur)
            cur.execute(
                "SELECT m.{doc}, m.nom1, m.nom2, m.ape1, m.ape2, m.{status}, e.cod_emp, e.nom_emp "
                "FROM {master} m LEFT JOIN empresa e ON e.cod_emp = m.cod_emp WHERE m.{doc} = %s".format(
                    doc=s.doc, status=s.status, master=s.master), (document,))
            row = cur.fetchone()
        if row is None:
            return None
        company = CompanyRef(id=row[6], name=row[7]) if row[6] is not None else None
        return Member(document=row[0], full_name=_full_name(row[1], row[2], row[3], row[4]),
                      status=_status(row[5]), company=company)

    def list_beneficiaries(self, document):
        """None si el afiliado no existe; lista (posiblemente vacía) si existe."""
        with self._session() as (_, cur):
            s = self._schema(cur)
            cur.execute("SELECT 1 FROM {master} WHERE {doc} = %s".format(master=s.master, doc=s.doc), (document,))
            if cur.fetchone() is None:
                return None
            cur.execute("SELECT nro_doc_ben, nom1, nom2, ape1, ape2, cod_par FROM afi_ben WHERE nro_doc = %s "
                        "ORDER BY nro_doc_ben", (document,))
            rows = cur.fetchall()
        return [Beneficiary(document=r[0], full_name=_full_name(r[1], r[2], r[3], r[4]),
                            relationship=RELATIONSHIP_FROM_LEGACY.get((r[5] or "").strip().upper(), "OTHER"))
                for r in rows]

    def get_company(self, company_id):
        with self._session() as (_, cur):
            s = self._schema(cur)
            cur.execute(
                "SELECT e.cod_emp, e.nom_emp, (SELECT count(*) FROM {master} m WHERE m.cod_emp = e.cod_emp "
                "AND m.{status} = %s) FROM empresa e WHERE e.cod_emp = %s".format(master=s.master, status=s.status),
                (ACTIVE_CODE, company_id))
            row = cur.fetchone()
        return Company(id=row[0], name=row[1], active_members=int(row[2])) if row else None

    # ------------------------------------------------------------------ escritura
    def register_retirement(self, request_id, document, on_date, reason, actor):
        """Aplica el retiro UNA sola vez por request_id, en una única transacción legacy."""
        with self._session(autocommit=False) as (conn, cur):
            cur.execute("SELECT to_regclass('public.{0}') IS NOT NULL".format(REQUEST_TABLE))
            if not cur.fetchone()[0]:
                cur.execute("SELECT pg_advisory_xact_lock(%s)", (REQUEST_LOCK,))
                cur.execute("CREATE TABLE IF NOT EXISTS {0} (request_id VARCHAR(80) PRIMARY KEY, "
                            "document VARCHAR(15) NOT NULL, movement_id INTEGER, "
                            "created_at TIMESTAMP NOT NULL DEFAULT now())".format(REQUEST_TABLE))
            s = self._schema(cur)
            cur.execute("INSERT INTO {0} (request_id, document) VALUES (%s, %s) ON CONFLICT (request_id) DO NOTHING "
                        "RETURNING request_id".format(REQUEST_TABLE), (request_id, document))
            if cur.fetchone() is None:
                cur.execute("SELECT document, movement_id FROM {0} WHERE request_id = %s".format(REQUEST_TABLE),
                            (request_id,))
                known_document, movement = cur.fetchone()
                conn.rollback()
                if known_document != document:
                    return RetirementOutcome(CONFLICT)
                return RetirementOutcome(DUPLICATE, movement)
            cur.execute("SELECT 1 FROM {master} WHERE {doc} = %s FOR UPDATE".format(master=s.master, doc=s.doc),
                        (document,))
            if cur.fetchone() is None:
                conn.rollback()
                return RetirementOutcome(NOT_FOUND)
            cur.execute("SELECT sp_registrar_retiro(%s, %s, %s, %s)", (document, on_date, reason[:200], actor))
            movement = cur.fetchone()[0]
            cur.execute("UPDATE {0} SET movement_id = %s WHERE request_id = %s".format(REQUEST_TABLE),
                        (movement, request_id))
            conn.commit()
            return RetirementOutcome(CREATED, movement)

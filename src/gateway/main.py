"""Punto de entrada: arma las piezas y sirve el gateway en el puerto 8082."""

import logging
import signal
import sys
import threading

from adapter.legacy_repository import LegacyRepository
from gateway.audit import AuditLog
from gateway.config import Settings
from gateway.http_api import Application, make_server
from gateway.migration import MigrationState
from gateway.outbox import Outbox
from gateway.resilience import LegacyGuard
from gateway.service import GatewayService, OutboxWorker


def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_env()
    if not settings.tokens:
        logging.warning("No hay tokens configurados: todas las rutas protegidas responderán 401")
    repository = LegacyRepository(settings.legacy_host, settings.legacy_port, settings.legacy_db, settings.legacy_user,
                                  settings.legacy_password, settings.connect_timeout)
    outbox = Outbox(settings.outbox_path)
    service = GatewayService(repository, LegacyGuard(settings.breaker_cooldown, settings.legacy_deadline), outbox,
                             MigrationState(settings.state_dir, settings.default_mode), settings.max_pending)
    worker = OutboxWorker(service, outbox, settings.outbox_interval)
    worker.start()
    server = make_server(Application(settings, service, AuditLog(settings.audit_path)), settings.port)

    def shutdown(*_):
        worker.stop()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    logging.info("gateway escuchando en :%s", settings.port)
    server.serve_forever()


if __name__ == "__main__":
    main()

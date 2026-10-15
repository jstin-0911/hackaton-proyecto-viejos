"""Estado de migración por dominio (LEGACY -> DUAL -> MODERN).

La fuente de verdad es un archivo por dominio en STATE_DIR (lo escribe scripts/set-mode.sh y
rollback.sh). Subsidios lee el mismo archivo, así el rollback funciona aunque el gateway esté caído.
"""

import os

STATES = ("LEGACY", "DUAL", "MODERN")
DOMAINS = ("affiliations", "companies", "contributions", "reports")
INITIAL = {"affiliations": None, "companies": "LEGACY", "contributions": "LEGACY", "reports": "LEGACY"}


class MigrationState:
    def __init__(self, state_dir, default_affiliations):
        self._dir = state_dir
        fallback = default_affiliations if default_affiliations in STATES else "DUAL"
        self._defaults = dict(INITIAL, affiliations=fallback)

    def _read(self, domain):
        try:
            with open(os.path.join(self._dir, domain + ".mode"), encoding="utf-8") as handle:
                value = handle.read().strip().upper()
        except OSError:
            return self._defaults[domain]
        return value if value in STATES else self._defaults[domain]

    def snapshot(self):
        return {"domains": {domain: self._read(domain) for domain in DOMAINS}}

#!/usr/bin/env bash
# Devuelve un dominio a LEGACY: Subsidios vuelve a sp_registrar_retiro y el estado queda LEGACY.
# Uso: ./rollback.sh affiliations
#
# No depende del gateway: escribe el estado compartido en ./state y Subsidios lo lee en la
# siguiente petición (menos de 1 segundo). Los retiros que el gateway ya aceptó (202) no se
# pierden: siguen en su cola y se aplican una sola vez cuando el legacy responde.
set -euo pipefail
cd "$(dirname "$0")"

domain="${1:-}"
if [ -z "$domain" ]; then
  echo "Uso: ./rollback.sh <dominio>   (por ejemplo: ./rollback.sh affiliations)" >&2
  exit 2
fi

bash scripts/set-mode.sh "$domain" LEGACY
echo "Rollback aplicado: ${domain} -> LEGACY"

# Verificación informativa (nunca hace fallar el rollback: el gateway puede estar caído a propósito).
if command -v curl >/dev/null 2>&1; then
  port="$(grep -E '^GATEWAY_PORT=' .env 2>/dev/null | head -1 | cut -d= -f2 || true)"
  token="$(grep -E '^PORTAL_TOKEN=' .env 2>/dev/null | head -1 | cut -d= -f2- || true)"
  sub_port="$(grep -E '^SUBSIDIOS_PORT=' .env 2>/dev/null | head -1 | cut -d= -f2 || true)"
  status="$(curl -fsS --max-time 3 -H "Authorization: Bearer ${token}" "http://localhost:${port:-8082}/api/v1/migration/status" 2>/dev/null || true)"
  echo "Gateway migration/status: ${status:-no disponible (no importa: Subsidios ya usa el camino legacy)}"
  health="$(curl -fsS --max-time 3 "http://localhost:${sub_port:-8091}/health" 2>/dev/null || true)"
  echo "Subsidios /health: ${health:-no disponible}"
fi
exit 0

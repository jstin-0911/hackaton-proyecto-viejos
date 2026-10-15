#!/usr/bin/env bash
# Cambia el estado de migración de un dominio: LEGACY -> DUAL -> MODERN (y de vuelta).
# Uso: scripts/set-mode.sh <affiliations|companies|contributions|reports> <LEGACY|DUAL|MODERN>
# El estado vive en state/<dominio>.mode; el gateway y Subsidios lo leen en cada petición,
# así el cambio aplica en menos de un segundo y sin reiniciar nada.
set -euo pipefail
cd "$(dirname "$0")/.."

domain="${1:-}"
mode="${2:-}"
case "$domain" in
  affiliations|companies|contributions|reports) ;;
  *) echo "Dominio inválido: '${domain}'. Use: affiliations, companies, contributions o reports" >&2; exit 2 ;;
esac
case "$mode" in
  LEGACY|DUAL|MODERN) ;;
  *) echo "Estado inválido: '${mode}'. Use: LEGACY, DUAL o MODERN" >&2; exit 2 ;;
esac

mkdir -p state
tmp="$(mktemp "state/.${domain}.XXXXXX")"
echo "$mode" > "$tmp"
chmod 644 "$tmp"
mv -f "$tmp" "state/${domain}.mode"
echo "state/${domain}.mode = ${mode}"

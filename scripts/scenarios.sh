#!/usr/bin/env bash
# Recorrido de punta a punta de los tres eventos del reto + rollback, con verificación automática.
#
#   1. App móvil (evento 3): lee con MOBILE_TOKEN, no puede escribir.
#   2. Falla del legacy (evento 2): docker compose stop legacy-db -> 503 rápido, retiros en cola,
#      al recuperarse se aplican UNA sola vez (por el gateway y por Subsidios).
#   3. Cambio de esquema (evento 1): scripts/schema-change.sh -> las respuestas no cambian.
#   4. Rollback: ./rollback.sh affiliations -> Subsidios vuelve a sp_registrar_retiro.
#
# ATENCIÓN: modifica datos y aplica el cambio de esquema. Úselo en un entorno recién levantado
# y termine con ./reset.sh. Requiere: docker compose, curl, jq.
set -uo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a

GATEWAY="http://localhost:${GATEWAY_PORT:-8082}"
SUBSIDIOS="http://localhost:${SUBSIDIOS_PORT:-8091}"
EDUCACION="http://localhost:${EDUCACION_PORT:-8090}"
PASS=0; FAIL=0

check() { # check "descripción" comando...
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then PASS=$((PASS+1)); echo "  [OK]   $label"; else FAIL=$((FAIL+1)); echo "  [FAIL] $label"; fi
}
sql() { docker compose exec -T legacy-db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "$0"' "$1" | tr -d '[:space:]'; }
api() { curl -sS --max-time 10 -H "Authorization: Bearer ${PORTAL_TOKEN}" "$GATEWAY$1"; }
code() { curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$@"; }
post_retirement() { # token documento requestId
  curl -s -w '\n%{http_code}' --max-time 10 -X POST -H "Authorization: Bearer $1" -H 'Content-Type: application/json' \
    -d "{\"requestId\":\"$3\",\"date\":\"2026-10-05\",\"reason\":\"escenario\"}" "$GATEWAY/api/v1/members/$2/retirements"
}
wait_for() { # segundos comando...
  local limit="$1"; shift; local t=0
  while ! "$@" >/dev/null 2>&1; do t=$((t+1)); [ "$t" -ge "$limit" ] && return 1; sleep 1; done
}
mode_is() { [ "$(api /api/v1/migration/status | jq -r .domains.affiliations)" = "$1" ]; }
pending_is_zero() { [ "$(api /api/v1/ops/stats | jq -r .retirements.PENDING)" = "0" ]; }

echo "== 0. Estado inicial"
read -r D1 D2 D3 <<<"$(docker compose exec -T legacy-db sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -tAc \"SELECT nro_doc FROM afi_mae WHERE est_afi='A' ORDER BY nro_doc DESC LIMIT 3\"" | tr '\n' ' ')"
echo "  afiliados de prueba: ${D1: -4} ${D2: -4} ${D3: -4} (terminan en)"
check "gateway UP y legacy UP" bash -c "[ \"\$(curl -s $GATEWAY/health | jq -r '.status+.legacy')\" = UPUP ]"
BEFORE_MEMBER="$(api /api/v1/members/$D1)"; BEFORE_COMPANY="$(api /api/v1/companies/$(echo "$BEFORE_MEMBER" | jq -r .company.id))"

echo "== 1. Nuevo consumidor: app móvil (solo lectura)"
check "móvil lee afiliado (200)" [ "$(code -H "Authorization: Bearer $MOBILE_TOKEN" "$GATEWAY/api/v1/members/$D1")" = 200 ]
check "móvil lee beneficiarios (200)" [ "$(code -H "Authorization: Bearer $MOBILE_TOKEN" "$GATEWAY/api/v1/members/$D1/beneficiaries")" = 200 ]
check "móvil NO puede escribir (403)" [ "$(post_retirement "$MOBILE_TOKEN" "$D1" mov-1 | tail -1)" = 403 ]
check "sin token (401)" [ "$(code "$GATEWAY/api/v1/members/$D1")" = 401 ]

echo "== 2. Falla del legacy: docker compose stop legacy-db"
docker compose stop legacy-db >/dev/null 2>&1
START=$(date +%s.%N); DOWN_CODE="$(code -H "Authorization: Bearer $PORTAL_TOKEN" "$GATEWAY/api/v1/members/$D1")"; ELAPSED="$(awk -v a="$START" -v b="$(date +%s.%N)" 'BEGIN{printf "%.2f", b-a}')"
check "consulta -> 503 LEGACY_UNAVAILABLE" bash -c "[ '$DOWN_CODE' = 503 ] && [ \"\$(curl -s -H 'Authorization: Bearer $PORTAL_TOKEN' $GATEWAY/api/v1/members/$D1 | jq -r .code)\" = LEGACY_UNAVAILABLE ]"
check "respuesta en < 3 s (${ELAPSED}s)" bash -c "awk 'BEGIN{exit !($ELAPSED < 3)}'"
check "/health sigue 200 con legacy DOWN" bash -c "[ \"\$(curl -s $GATEWAY/health | jq -r .legacy)\" = DOWN ]"
OUT="$(post_retirement "$SUBSIDIOS_TOKEN" "$D2" caida-1)"
check "retiro durante la caída -> 202" [ "$(echo "$OUT" | tail -1)" = 202 ]
check "mismo requestId durante la caída -> 202 (sin duplicar cola)" [ "$(post_retirement "$SUBSIDIOS_TOKEN" "$D2" caida-1 | tail -1)" = 202 ]
SUBS="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 -X POST -d "{\"documento\":\"$D3\",\"fecha\":\"2026-10-05\",\"motivo\":\"subs caida\"}" "$SUBSIDIOS/retiros")"
check "Subsidios durante la caída -> 202" [ "$SUBS" = 202 ]
docker compose start legacy-db >/dev/null 2>&1
check "el legacy se recupera" wait_for 60 bash -c "[ \"\$(curl -s $GATEWAY/health | jq -r .legacy)\" = UP ]"
check "la cola se vacía sola" wait_for 60 pending_is_zero
check "retiro del gateway aplicado UNA vez" [ "$(sql "SELECT count(*) FROM logmov WHERE nro_doc='$D2' AND tip_mov='RET'")" = 1 ]
check "retiro de Subsidios aplicado UNA vez" [ "$(sql "SELECT count(*) FROM logmov WHERE nro_doc='$D3' AND tip_mov='RET'")" = 1 ]
check "reintento posterior no duplica (200)" [ "$(post_retirement "$SUBSIDIOS_TOKEN" "$D2" caida-1 | tail -1)" = 200 ]
check "Educación ve el retiro" bash -c "curl -s $EDUCACION/afiliados/$D2 | jq -e '.estado==\"RETIRADO\"'"

echo "== 3. Cambio de esquema: scripts/schema-change.sh"
bash scripts/schema-change.sh >/dev/null
check "la tabla ahora se llama person_master" [ "$(sql "SELECT to_regclass('person_master') IS NOT NULL")" = t ]
check "afiliado idéntico tras el cambio" bash -c "[ \"\$(curl -s -H 'Authorization: Bearer $PORTAL_TOKEN' $GATEWAY/api/v1/members/$D1)\" = '$BEFORE_MEMBER' ]"
check "empresa idéntica tras el cambio" bash -c "[ \"\$(curl -s -H 'Authorization: Bearer $PORTAL_TOKEN' $GATEWAY/api/v1/companies/$(echo "$BEFORE_MEMBER" | jq -r .company.id))\" = '$BEFORE_COMPANY' ]"
check "portal sigue funcionando" [ "$(code "http://localhost:${PORTAL_PORT:-8092}/portal/afiliados/$D1")" = 200 ]
OUT="$(post_retirement "$SUBSIDIOS_TOKEN" "$D1" esquema-1)"
check "retiro tras el cambio -> 201" [ "$(echo "$OUT" | tail -1)" = 201 ]
check "retiro tras el cambio repetido -> 200" [ "$(post_retirement "$SUBSIDIOS_TOKEN" "$D1" esquema-1 | tail -1)" = 200 ]
check "sp_registrar_retiro sigue existiendo" [ "$(sql "SELECT count(*) FROM pg_proc WHERE proname='sp_registrar_retiro'")" = 1 ]

echo "== 4. Rollback: ./rollback.sh affiliations"
check "rollback termina con código 0" ./rollback.sh affiliations
check "migration/status -> LEGACY" mode_is LEGACY
D4="$(sql "SELECT document_number FROM person_master WHERE status_code='A' ORDER BY document_number LIMIT 1")"
SUBS="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 -X POST -d "{\"documento\":\"$D4\",\"fecha\":\"2026-10-05\",\"motivo\":\"rollback\"}" "$SUBSIDIOS/retiros")"
check "Subsidios (camino legacy) registra el retiro -> 201" [ "$SUBS" = 201 ]
check "queda en la base legacy" [ "$(sql "SELECT count(*) FROM logmov WHERE nro_doc='$D4' AND tip_mov='RET'")" = 1 ]
bash scripts/set-mode.sh affiliations DUAL >/dev/null
check "vuelta a DUAL" mode_is DUAL

echo
echo "Resultado: ${PASS} OK, ${FAIL} FAIL.  Para dejar el entorno limpio: ./reset.sh"
[ "$FAIL" -eq 0 ]

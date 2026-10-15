# Legacy Escape — Gateway de transición para la Caja de Compensación

## Descripción

Capa de transición que permite modernizar el sistema de una Caja de Compensación sin apagarlo. Un **gateway** HTTP expone un
modelo canónico (afiliados, beneficiarios, empresas y retiros) y oculta la base legacy mediante un **adapter**; el portal, Subsidios y
la app móvil consumen solo la API. Los retiros son idempotentes, sobreviven a una caída del legacy (se encolan y se aplican una sola vez),
el cambio de esquema del DBA no los afecta y existe un rollback inmediato por dominio. Educación sigue leyendo la base sin cambios.

## Integrantes

- <Nombre completo del integrante 1>
- <Nombre completo del integrante 2>

## Requisitos

Docker Engine con el plugin Docker Compose v2 (probado con Docker 29 y Compose 5), Linux, macOS o Windows con WSL2. Para los scripts de apoyo
se usan `bash`, `curl` y `jq`. No hace falta instalar Python ni PostgreSQL en la máquina: todo corre en contenedores.

## Instalación y ejecución

```bash
cp .env.example .env            # y cambien los tres tokens y la clave de la base por valores propios
mkdir -p logs state test-results
docker compose up -d --build    # levanta legacy-db, educacion-app, gateway, portal-client y subsidios-app
docker compose ps               # todos deben estar "running"; gateway y legacy-db "healthy"
./validator check               # pruebas públicas del contrato (gateway en http://localhost:8082)
./rollback.sh affiliations      # devuelve el dominio Afiliaciones a LEGACY (menos de 1 segundo)
./reset.sh                      # vuelve todo al estado inicial (borra volúmenes y la cola)
```

Recorrido completo de los tres eventos del reto (falla del legacy, cambio de esquema, app móvil) y del rollback, con 29 verificaciones
automáticas: `./scripts/scenarios.sh` (úsenlo en un entorno recién levantado y terminen con `./reset.sh`).

## Configuración

Todo se lee de `.env` (se crea desde `.env.example`; `.env` nunca se versiona). Variables:

| Variable | Para qué sirve | Ejemplo |
|---|---|---|
| `POSTGRES_DB` | Nombre de la base legacy | `legacy` |
| `POSTGRES_USER` | Usuario de la base legacy | `legacy` |
| `POSTGRES_PASSWORD` | Clave de la base legacy (cámbiela) | `cambiar-esta-clave` |
| `LEGACY_DB_HOST` | Host de la base; entre contenedores es el nombre del servicio, no `localhost` | `legacy-db` |
| `LEGACY_DB_PORT` | Puerto de la base legacy | `5432` |
| `GATEWAY_URL` | URL del gateway que usan el portal y Subsidios | `http://gateway:8082` |
| `GATEWAY_PORT` | Puerto publicado en el host para el contrato | `8082` |
| `GATEWAY_WRITE_CONSUMERS` | Consumidores con permiso de escritura (retiros); `mobile` nunca puede | `subsidios,portal` |
| `LEGACY_CONNECT_TIMEOUT` | Segundos máximos para conectar con el legacy | `1` |
| `LEGACY_DEADLINE_SECONDS` | Plazo total por llamada al legacy; vencido responde 503 `LEGACY_UNAVAILABLE` | `2.5` |
| `OUTBOX_INTERVAL_SECONDS` | Cada cuánto se reintentan los retiros en cola | `2` |
| `AFFILIATIONS_DEFAULT_MODE` | Estado inicial de Afiliaciones si no existe `state/affiliations.mode` | `DUAL` |
| `PORTAL_TOKEN` | Token Bearer del portal de servicios (lectura y escritura permitida por `GATEWAY_WRITE_CONSUMERS`) | `cambiar-portal` |
| `SUBSIDIOS_TOKEN` | Token Bearer de Subsidios (registra retiros) | `cambiar-subsidios` |
| `MOBILE_TOKEN` | Token Bearer de la app móvil (solo lectura; escribir da 403) | `cambiar-mobile` |

## Arquitectura

```text
Portal / Subsidios / Móvil ──Bearer──▶ gateway ──▶ modelo canónico ──▶ adapter ──▶ legacy-db ◀── educacion-app (sin cambios)
```

- `legacy-db`: PostgreSQL con las tablas heredadas; nadie nuevo se conecta directo a él.
- `gateway`: API en el puerto 8082 con autenticación por token, auditoría, errores uniformes, circuito con plazo máximo y cola de retiros
  (SQLite en el volumen `gateway-data`). El código vive en `src/gateway`; el **adapter** en `src/adapter/legacy_repository.py` es el único
  que conoce tablas, columnas y el procedimiento legacy, y detecta solo si el esquema es el original o el renombrado.
- `educacion-app`: lee la base directamente (no se modifica).
- `portal-client`: solo habla HTTP con `GATEWAY_URL` (no se modifica).
- `subsidios-app`: registra retiros por el gateway (modos DUAL/MODERN) o por el procedimiento legacy (modo LEGACY, el rollback). El modo
  se lee de `state/affiliations.mode`, por eso el rollback no depende de que el gateway esté vivo.
- `tests`: servicio con perfil `test` que ejecuta pytest contra la API en funcionamiento y deja el reporte JUnit en `test-results/`.

Detalle y alternativas descartadas en `docs/architecture.md`.

## Uso

Autenticación: `Authorization: Bearer <token>` (portal, subsidios o mobile). Ejemplos (con `TOKEN=<su PORTAL_TOKEN>`):

`GET /health` — público; `{"status":"UP","legacy":"UP"}`:

```bash
curl http://localhost:8082/health
```

`GET /api/v1/members/{document}` — afiliado en modelo canónico; 404 si no existe:

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8082/api/v1/members/1019886173
=> {"document":"1019886173","fullName":"MONICA PABON MENDOZA","status":"ACTIVE","company":{"id":"2015","name":"LOGISTICA LA PLAYA SAS"}}
```

`GET /api/v1/members/{document}/beneficiaries` — lista de `{document, fullName, relationship}` (`SPOUSE`, `CHILD`, `FATHER`, `MOTHER`):

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8082/api/v1/members/1019886173/beneficiaries
```

`GET /api/v1/companies/{id}` — empresa con `activeMembers`:

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8082/api/v1/companies/2001
=> {"id":"2001","name":"INVERSIONES SAN LUIS S EN C","activeMembers":21}
```

`POST /api/v1/members/{document}/retirements` — retiro idempotente: 201 al aplicarse, 200 si el `requestId` ya estaba aplicado, 202 si el
legacy está caído (queda en cola y se aplica una sola vez), 403 para la app móvil, 409 si el `requestId` se reutilizó con otros datos:

```bash
curl -X POST -H "Authorization: Bearer $SUBSIDIOS_TOKEN" -H "Content-Type: application/json" \
  -d '{"requestId":"ret-0001","date":"2026-10-05","reason":"Retiro voluntario"}' \
  http://localhost:8082/api/v1/members/1019886173/retirements
```

`GET /api/v1/migration/status` — `{"domains":{"affiliations":"DUAL", ...}}`:

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8082/api/v1/migration/status
```

Extras operativos (documentados en `openapi.yaml`): `GET /api/v1/retirements/{requestId}` (estado PENDING/APPLIED/FAILED de un retiro) y
`GET /api/v1/ops/stats` (circuito y cola). Otras puertas: interfaz visual del portal `http://localhost:8093`, Educación
`http://localhost:8090/afiliados/{documento}`, portal API `http://localhost:8092/portal/afiliados/{documento}` y Subsidios
`POST http://localhost:8091/retiros` (pasa por el gateway y queda en
`logs/audit.log` con `consumer` = `subsidios`). Cambiar el estado de un dominio: `scripts/set-mode.sh <dominio> <LEGACY|DUAL|MODERN>`.

## Pruebas

Las pruebas automatizadas (44 con pytest) verifican contra la API en marcha el contrato de cada ruta, el portal visual y sus consultas, el formato de errores sin trazas ni SQL,
los permisos por token, la idempotencia de retiros, el efecto visible en la base legacy y en Educación, el paso de Subsidios por el gateway y la
auditoría con documentos enmascarados; restauran los datos que tocan. Se ejecutan con
`docker compose --profile test run --rm tests` y dejan el reporte JUnit en `test-results/junit.xml`. Los eventos destructivos (caída de la base,
cambio de esquema, rollback) los cubre `./scripts/scenarios.sh`; el validador del kit se corre con `./validator check` y `./validator entregables`.

## Documentación

- [Arquitectura](docs/architecture.md): contexto, componentes, modelo canónico, cambio de esquema y alternativas descartadas.
- [Mapa de dependencias](docs/dependency-map.md): quién lee y quién escribe cada tabla legacy.
- [Plan de migración](docs/migration-plan.md): estados LEGACY → DUAL → MODERN por dominio, criterios y rollback.
- [Interfaz visual](docs/portal-ui.md): componentes, flujo de consulta, privacidad y pruebas del portal FESC Orbit.
- [Contrato OpenAPI](openapi.yaml): las rutas del gateway con esquemas y ejemplos.
- [Uso de IA](AI_USAGE.md): cómo se usó la inteligencia artificial y qué se corrigió.

## Qué resolvimos

Construimos el gateway con modelo canónico y adapter, y migramos el dominio Afiliaciones sin tocar Educación. Las consultas ya no dependen del
esquema: el renombre `AFI_MAE → PERSON_MASTER` no cambia ninguna respuesta. Los retiros son idempotentes con la clave guardada en la misma
transacción del legacy, por lo que ni los reintentos ni los cortes duplican movimientos (incidente de 2021). Si el legacy cae, las consultas
responden 503 en milisegundos y los retiros se encolan y se aplican una sola vez al volver (incidente de 2023). La auditoría enmascara los
documentos (incidente de 2025) y el rollback devuelve Subsidios al camino legacy sin depender del gateway.

## Limitaciones y pendientes

La app móvil y el portal comparten el mismo formato de API; no hay límite de tasa por consumidor ni rotación automática de tokens. La cola de
retiros usa SQLite en un solo nodo, así que no escala horizontalmente sin cambiar a un broker. El camino LEGACY de Subsidios conserva el defecto
histórico de no ser idempotente. Educación, Reportes y Aportes siguen en LEGACY y son los siguientes dominios del plan de migración.

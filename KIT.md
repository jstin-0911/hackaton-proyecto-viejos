# Legacy Escape — modernizar sin apagar el negocio

Varias aplicaciones usan directamente la base legacy. La política de arquitectura es:

> **Ninguna aplicación nueva puede conectarse directamente a la base legacy.**

Construyan la capa de transición (gateway / API + adapter + modelo canónico) y migren el dominio
**Afiliaciones** sin una migración Big Bang. El detalle del reto y el contrato están en `retos.md`.

> Esta es la guía del kit. La documentación de **su** software va en `README.md`, que trae la plantilla con el formato obligatorio (entregable «README: documentación del software»).

## Inicio

```bash
cp .env.example .env        # cambien los tokens
mkdir -p logs
docker compose up -d --build
docker compose ps
curl http://localhost:8090/afiliados/<documento>   # lo que ve Educación
./validator check
```

## Qué hay en el kit

| Ruta | Contenido |
|---|---|
| `docker-compose.yml` | `legacy-db`, `educacion-app` (:8090), `portal-client` (:8092), `subsidios-app` (:8091). Agreguen su `gateway` (:8082) |
| `db/init/` | Esquema, datos sintéticos y `sp_registrar_retiro` |
| `services/` | Código de las aplicaciones consumidoras (Educación y Portal no se modifican) |
| `docs/` | Modelo legacy parcial, procesos e incidentes históricos |
| `scripts/schema-change.sh` | Evento 1: aplica el cambio de esquema del DBA |
| `validator` | Validador del equipo (`./validator check` y `./validator entregables`) |
| `reset.sh` | Vuelve la base y los contenedores al estado inicial |
| `AI_USAGE.md`, `docs/dependency-map.md`, `docs/migration-plan.md`, `docs/architecture.md` | Plantillas de los entregables con el formato obligatorio (vacías no suman) |

## Reglas del contrato que conviene recordar

- Gateway en `http://localhost:8082`, tokens `PORTAL_TOKEN`, `SUBSIDIOS_TOKEN`, `MOBILE_TOKEN` en `.env`.
- Auditoría en `logs/audit.log` del repositorio (monten la carpeta `./logs` en su contenedor), con
  `consumer` ∈ `portal`, `subsidios`, `mobile`.
- Subsidios (`services/subsidios`) sí se modifica: `POST :8091/retiros` debe registrar el retiro por el
  gateway con `SUBSIDIOS_TOKEN`. Conserven el camino legacy para el rollback.
- El servicio de la base debe seguir llamándose `legacy-db`; el validador usa `docker compose stop legacy-db`.
  Los servicios nuevos que hablan con la base se llaman `gateway…` o `adapter…`; ningún otro servicio
  nuevo puede conectarse a `legacy-db` (penalización automática).
- Los nombres legacy (`AFI_MAE`, `NRO_DOC`, `sp_registrar_retiro`…) solo pueden aparecer en `src/` dentro
  de una carpeta o archivo cuyo nombre contenga `adapter`.
- `./rollback.sh affiliations` (ejecutable, en la raíz) devuelve Afiliaciones a `LEGACY` en menos de 3 minutos.
- Servicio `tests` en `docker-compose.yml` con `profiles: ["test"]`: prueba la API en funcionamiento y deja
  un reporte JUnit XML en `./test-results/`.
- Eventos 2 y 3: `docker compose stop legacy-db` / app móvil con `MOBILE_TOKEN` (solo lectura).

## Validador

`./validator check` ejecuta las pruebas no destructivas (salud, consultas, autenticación, errores,
auditoría, estado de migración). Las pruebas que modifican datos, detienen la base o aplican el
cambio de esquema (G07–G11 y G15) solo las ejecuta el validador oficial; pruébenlas ustedes con
`./reset.sh` a mano. Requiere Python 3.8+ y Docker.

`./validator entregables` revisa el adapter, los documentos, OpenAPI, el último reporte de
`test-results/`, el historial Git, `AI_USAGE.md` y `README.md` con las mismas reglas y puntos del calificador oficial.
El rollback (GE04) solo lo ejecuta el validador oficial. Generen el reporte de pruebas con
`docker compose --profile test run --rm tests`.

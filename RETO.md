# FESC Legacy Challenge 2026

Hackathon del programa de Ingeniería de Software · Técnico · Tecnólogo · Profesional

---

## 1. Información general

| | |
|---|---|
| Duración | La anuncian los organizadores. La **hora límite** se publica en la plataforma del evento |
| Equipos | Parejas (2 estudiantes del mismo nivel) |
| Organización del tiempo | Libre. No hay hitos ni orden obligatorio. Todo el material está disponible desde el inicio |
| Inteligencia artificial | Permitida durante todo el reto (ver sección 3) |
| Entorno | Cada nivel descarga su propio kit (ZIP) desde la plataforma del evento. Ningún nivel depende del trabajo de otro |
| Calificación | Validador automático + entregables verificados por el sistema (ver `rubrica.md`). La única excepción es la mitad del pitch: el comité revisa el contenido del video |

### El escenario común

Una Caja de Compensación Familiar lleva años operando sobre un sistema legacy (IBM Informix / Genero) cuya base de datos se convirtió en el punto de integración de todo: afiliaciones, subsidios, educación, reportes. Cambiar una columna rompe varias aplicaciones, y validar afiliaciones con otras cajas sigue siendo manual.

Cada nivel resuelve una parte distinta del problema:

| Nivel | Reto | Pregunta |
|---|---|---|
| Técnico | **Terminal Rescue** | ¿Puedes diagnosticar y reparar un proceso crítico averiado desde la terminal? |
| Tecnólogo | **Legacy Escape** | ¿Puedes modernizar el sistema sin apagarlo ni romper las aplicaciones que dependen de él? |
| Profesional | **Caja Link** | ¿Puedes integrar varias cajas entre sí con seguridad, privacidad y tolerancia a fallas? |

---

## 2. Reglas comunes

1. **Entrega:** cada pareja descarga el kit de su nivel, lo sube a **su propio repositorio Git público** (GitHub, GitLab o Bitbucket) y registra el enlace en la plataforma del evento (**Mi equipo**) (cada integrante entra con su correo; la primera contraseña es su número de documento y la plataforma obliga a cambiarla). El enlace se puede cambiar hasta la fecha de cierre.
2. **Repositorio público:** la plataforma comprueba al registrar que el repositorio se pueda descargar sin usuario ni contraseña. Si al llegar la hora límite el repositorio no está registrado o no es público, el equipo **no se califica**.
3. **Hora límite:** se califica automáticamente el **último commit con fecha anterior a la hora límite**. Lo que se suba después se ignora. Si no hay ningún commit antes de la hora límite, el equipo no se califica.
4. **Commits:** los dos integrantes hacen commits con su propio nombre y correo. El sistema revisa que haya al menos 10 commits durante el evento, al menos 3 de cada integrante y mensajes que describan el cambio ("corrige host de la base en cierre-api", no "update").
5. El entorno debe quedar **levantable desde cero** con `docker compose up -d --build` (o con el `run.sh` que indique cada reto). La calificación es automática y corre en un servidor Linux: los scripts del equipo (`run.sh`, `reset.sh`, `rollback.sh`) se ejecutan con `bash` y solo pueden contar con `docker` / `docker compose`, `git`, `python3`, `curl`, `jq`, `psql` y las utilidades estándar (`grep`, `awk`, `sed`, `sort`…). Cualquier otra herramienta debe correr dentro de un contenedor (`docker compose exec` o `docker compose run`). Por seguridad del servidor, `docker-compose.yml` no puede usar `privileged`, `cap_add`, `devices`, `network_mode: host`, `pid: host` ni montar carpetas fuera del repositorio (por ejemplo, `/var/run/docker.sock`): si lo hace, el entorno no se levanta y las pruebas valen 0.
6. Los secretos van en `.env` (no se versiona). Se entrega `.env.example`. Ningún archivo del repositorio puede tener escrito el valor de un token, clave o contraseña: el código los lee de variables de entorno.
7. Se permite cualquier lenguaje y framework, salvo que el reto indique lo contrario. Los nombres de endpoints, archivos, carpetas, servicios y puertos de este documento son **obligatorios**: el sistema de calificación los usa.
8. Cada kit incluye:
   - `./validator check`: ejecuta las pruebas públicas del contrato. El validador oficial ejecuta además casos ocultos.
   - `./validator entregables`: revisa los documentos y el repositorio con **las mismas reglas y puntos** del calificador oficial.
   - `./reset.sh`: devuelve el kit al estado inicial si el equipo rompe el entorno.
9. Los documentos entregables tienen un **formato obligatorio** (títulos, campos y tablas) indicado en cada reto. El sistema los revisa de forma automática: si el formato no se respeta, el entregable no suma. Cada kit trae estos archivos como **plantillas** con los títulos, campos y tablas listos para llenar; una plantilla sin llenar no suma puntos.
10. **Formato de los documentos:** todos los documentos que se califican van en **Markdown (`.md`)** con el nombre y la ruta exactos que pide el reto (`openapi.yaml` y `config/cajas.yaml` van en YAML). No se aceptan Word (`.docx`), PDF ni otros formatos en su lugar: si el sistema encuentra, por ejemplo, `AI_USAGE.docx` en vez de `AI_USAGE.md`, el entregable vale 0 y el reporte lo indica. La única excepción es la carpeta `evidence/` del nivel Técnico, que acepta `.txt`, `.log`, `.md`, `.csv`, `.json`, `.pdf`, `.png`, `.jpg` y `.jpeg`. Ningún archivo de texto puede pesar más de 1 MB: los que lo superen no se revisan.

11. **Pitch de 1 minuto:** cada pareja graba un video de **60 segundos o menos** que presente su solución (el problema, qué construyeron y qué resultado lograron), lo sube a **Google Drive**, lo comparte como «Cualquier persona con el enlace» y registra ese enlace en **Mi equipo** antes de la hora límite. Vale 5 puntos de los entregables: la mitad la da el sistema si Drive confirma que es un video público de 60 segundos o menos, y la otra mitad el comité si el contenido es válido. Si el comité lo marca como **no válido**, el pitch vale 0. No modifiquen el archivo después de la hora límite: el sistema lo detecta y pierde la mitad automática.

12. **README: documentación del software (2 puntos):** el `README.md` del repositorio es la documentación del software de la pareja (la guía de los organizadores viene aparte, en `KIT.md`). Cada kit lo trae como plantilla con once secciones obligatorias: `## Descripción`, `## Integrantes`, `## Requisitos`, `## Instalación y ejecución`, `## Configuración`, `## Arquitectura`, `## Uso`, `## Pruebas`, `## Documentación`, `## Qué resolvimos` y `## Limitaciones y pendientes`. El sistema no solo revisa que estén llenas: las contrasta con el repositorio. Configuración debe explicar **cada variable de `.env.example`**; Arquitectura, nombrar **cada servicio de `docker-compose.yml`**; Uso, incluir las rutas del contrato (en el Técnico, la API y los archivos de `output/`); Documentación, enlazar los demás entregables del nivel; e Instalación y ejecución, los comandos para levantarlo. El detalle está en la rúbrica (TE08 / GE11 / PE11).

---

## 3. Uso de inteligencia artificial

Se permite usar cualquier herramienta durante el reto (ChatGPT, Claude, Gemini, Copilot, Cursor, agentes, modelos locales).

> Puedes usar IA para construir cualquier parte de la solución, pero ambos integrantes deben poder entender, ejecutar, depurar y modificar todo lo entregado. Documentar con honestidad cómo usaron la IA y qué corrigieron también suma puntos (`AI_USAGE.md`).

Cada equipo entrega `AI_USAGE.md` en la raíz con **al menos 3 usos relevantes**, cada uno con este formato exacto:

```markdown
## Uso 1
- Herramienta: ChatGPT
- Para qué se usó: diagnosticar el error de conexión de la API
- Prompt principal (resumido): "connection refused contra cierre-db en docker compose"
- Qué produjo: sugirió cambiar el host a localhost
- Qué modificó o corrigió el equipo: localhost no sirve entre contenedores; usamos el nombre del servicio cierre-db
```

Los cinco campos deben estar llenos y "Qué modificó o corrigió el equipo" debe explicar la corrección en **8 palabras o más**. Si `AI_USAGE.md` no existe o no tiene ningún uso completo, se aplica la penalización de −5 puntos.

---

## 5. Nivel Tecnólogo — Legacy Escape: modernizar sin apagar el negocio

### Contexto

Varias aplicaciones usan directamente la base legacy. La dirección quiere modernizar, pero no acepta una migración Big Bang. La política de arquitectura es:

> **Ninguna aplicación nueva puede conectarse directamente a la base legacy.**

El sistema debe seguir operando mientras se migra **dominio por dominio**.

### Kit entregado

```text
tecnologo/
├── docker-compose.yml
│   ├── legacy-db          PostgreSQL con tablas heredadas (AFI_MAE, AFI_BEN, EMPRESA, APORTES, LOGMOV)
│   ├── educacion-app      lee la base directamente — NO se puede modificar
│   ├── portal-client      portal nuevo: solo habla HTTP con GATEWAY_URL
│   └── subsidios-app      registra retiros con el procedimiento legacy sp_registrar_retiro
├── docs/                  documentación parcial, procesos, incidentes históricos
├── scripts/schema-change.sh   aplica el cambio de esquema (ver evento 1)
├── validator
└── reset.sh
```

### Consumidores

| Aplicación | Qué hace | ¿Se puede modificar? |
|---|---|---|
| Educación | Lee afiliados directo de la base | No |
| Portal de servicios | Consulta afiliados, beneficiarios y empresas | No: solo se configura `GATEWAY_URL` |
| Subsidios | Registra retiros de afiliados | Sí: debe pasar a registrar los retiros por el gateway con `SUBSIDIOS_TOKEN` |
| App móvil (nueva) | Consulta afiliados y beneficiarios | Se construye durante el reto |

### Misión

Construir la capa de transición (gateway / API + adapter + modelo canónico) y migrar el dominio **Afiliaciones**:

```text
Portal / Subsidios / Móvil → Gateway API → Modelo canónico → Adapter → Legacy DB ← Educación (sin cambios)
```

1. **Discovery:** mapa de quién lee, quién escribe y qué tablas toca cada aplicación.
2. **Consultas por API:** el portal funciona sin conocer tablas, columnas ni códigos.
3. **Escritura migrada:** el retiro se registra por el servicio nuevo (también el que hace Subsidios) y queda en la base legacy, de modo que Educación y los reportes viejos lo ven.
4. **Reversibilidad:** si el servicio nuevo se desactiva, el camino legacy (`sp_registrar_retiro`) sigue funcionando, y `./rollback.sh affiliations` devuelve el dominio a LEGACY.
5. **Plan de migración** por dominio con estados `LEGACY → DUAL → MODERN`, criterios para avanzar y mecanismo de rollback.

### Eventos (disponibles desde el inicio)

1. **Cambio de esquema:** `scripts/schema-change.sh` renombra `AFI_MAE → PERSON_MASTER`, `NRO_DOC → DOCUMENT_NUMBER`, `EST_AFI → STATUS_CODE`. El portal y los contratos no cambian.
2. **Falla del legacy:** la base se detiene unos minutos (`docker compose stop legacy-db`). Las consultas deben fallar de forma controlada y los retiros no pueden perderse ni duplicarse.
3. **Nuevo consumidor:** la app móvil consulta afiliados y beneficiarios usando la API existente, sin acceso a la base y sin permisos de escritura.

### Contrato obligatorio (lo que revisa el validador)

Gateway en `http://localhost:8082`. Autenticación `Authorization: Bearer <token>`, con un token por consumidor definido en `.env`: `PORTAL_TOKEN`, `SUBSIDIOS_TOKEN`, `MOBILE_TOKEN`.

| Método y ruta | Respuesta esperada |
|---|---|
| `GET /health` | `200` · `{ "status": "UP", "legacy": "UP" \| "DOWN" }` |
| `GET /api/v1/members/{document}` | `200` · `{ "document", "fullName", "status", "company": { "id", "name" } }` · `status` ∈ `ACTIVE`, `RETIRED`, `SUSPENDED` |
| `GET /api/v1/members/{document}/beneficiaries` | `200` · lista de `{ "document", "fullName", "relationship" }` |
| `GET /api/v1/companies/{id}` | `200` · `{ "id", "name", "activeMembers" }` |
| `POST /api/v1/members/{document}/retirements` | Cuerpo `{ "requestId", "date", "reason" }` → `201`. Repetir el mismo `requestId` → `200` sin duplicar |
| `GET /api/v1/migration/status` | `{ "domains": { "affiliations": "LEGACY\|DUAL\|MODERN", ... } }` |

Reglas:

- Sin token → `401`. `MOBILE_TOKEN` en un `POST` → `403`.
- Documento inexistente → `404`. Errores con formato `{ "message", "error_id" }`, sin trazas ni SQL.
- Legacy caído: respuesta en menos de 3 segundos con `503` y `{ "code": "LEGACY_UNAVAILABLE" }`.
- Un retiro aceptado durante la caída (`202`) debe aplicarse al recuperarse, una sola vez.
- Auditoría en `logs/audit.log`, una línea JSON por petición: `timestamp`, `consumer` (`portal`, `subsidios` o `mobile`), `endpoint`, `status`, `latency_ms`. El documento va enmascarado (máximo 4 dígitos visibles).
- `sp_registrar_retiro` debe seguir funcionando.
- `POST http://localhost:8091/retiros` (Subsidios) sigue respondiendo como hoy, pero el retiro pasa por el gateway: aparece en `logs/audit.log` con `consumer` = `subsidios`.
- El servicio de la base se sigue llamando `legacy-db`. Los servicios nuevos que hablan con la base se llaman `gateway…` o `adapter…`; ningún otro servicio nuevo puede conectarse a `legacy-db`.

**`./rollback.sh affiliations`** (raíz del repositorio, ejecutable): devuelve el dominio Afiliaciones a `LEGACY` en menos de 3 minutos y termina con código 0. Después, `GET /api/v1/migration/status` muestra `affiliations: LEGACY` y un retiro hecho desde Subsidios sigue quedando en la base legacy.

**Pruebas del equipo:** un servicio `tests` en `docker-compose.yml` con `profiles: ["test"]`. El sistema ejecuta `docker compose --profile test run --rm tests` con el entorno recién levantado. El servicio prueba la API en funcionamiento, termina con código distinto de 0 si alguna prueba falla y deja un reporte JUnit XML en `./test-results/` (por ejemplo `pytest --junitxml`, `jest-junit` o los reportes de Maven Surefire).

### Entregables

```text
src/                   el adapter vive en una carpeta o archivo cuyo nombre contiene "adapter"
tests/
docker-compose.yml     levanta legacy + gateway + consumidores; incluye el servicio tests
rollback.sh
openapi.yaml           contrato v1 (OpenAPI 3) con las 6 rutas
README.md              documentación del software (regla 12)
AI_USAGE.md
docs/
├── dependency-map.md
├── architecture.md
└── migration-plan.md
```

**Adapter:** los nombres de tablas, columnas y procedimientos legacy (`AFI_MAE`, `NRO_DOC`, `EST_AFI`, `LOGMOV`, `sp_registrar_retiro`…) solo pueden aparecer en archivos de `src/` dentro de una carpeta o archivo cuyo nombre contenga `adapter` (por ejemplo `src/adapter/legacy_repository.py`). El resto del código usa el modelo canónico.

**Formato obligatorio de `docs/dependency-map.md`:** una tabla con una fila por aplicación y tabla.

```markdown
| Aplicación | Tabla | Operación | Criticidad |
|---|---|---|---|
| Educación | AFI_MAE | Lectura | Alta |
```

`Operación` ∈ `Lectura`, `Escritura`. `Criticidad` ∈ `Alta`, `Media`, `Baja`. El sistema compara las filas con las dependencias reales del legacy (`docs/procesos.md` del kit da las pistas); las filas incorrectas restan.

**Formato obligatorio de `docs/migration-plan.md`:**

```markdown
| Dominio | Estado | Criterio para avanzar | Rollback |
|---|---|---|---|
| Afiliaciones | DUAL | 7 días sin diferencias entre gateway y legacy | ./rollback.sh affiliations |
| Retiros | LEGACY | 0 retiros perdidos en 2 semanas de DUAL | volver Subsidios a sp_registrar_retiro |
| Empresas | LEGACY | ... | ... |

Siguiente dominio: Retiros
```

Al menos 3 dominios (uno es Afiliaciones), estado `LEGACY`, `DUAL` o `MODERN`, criterios con un número medible y rollback descrito en cada fila.

**Formato obligatorio de `docs/architecture.md`:** secciones `## Contexto`, `## Componentes`, `## Modelo canónico`, `## Cambio de esquema` y `## Alternativas descartadas` (esta última con al menos 2 alternativas en lista). Cada sección cuenta solo si tiene al menos 20 palabras.

---

## 7. Premios

| Premio | Para |
|---|---|
| Technical Builder | Mayor nota final del nivel Técnico |
| Product Builder | Mayor nota final del nivel Tecnólogo |
| Engineering Award | Mayor nota final del nivel Profesional |
| AI Engineering Award | Entre los equipos calificados sin penalizaciones, el mejor `AI_USAGE.md` según el sistema |
| FESC Productization | Entre los tres primeros de cada nivel, la mayor nota de los que están listos para producción: sin penalizaciones, validador ≥ 80 % y entregables ≥ 80 % |

La calificación detallada está en `rubrica.md`.

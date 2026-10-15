# Uso de inteligencia artificial

Herramienta principal: Claude (Claude Code). Todo lo generado se ejecutó y se verificó contra una base PostgreSQL real con los
scripts de `db/init`, con `./validator check`, `./validator entregables`, las pruebas de `tests/` y `scripts/scenarios.sh`.

## Uso 1
- Herramienta: Claude (Claude Code)
- Para qué se usó: diseñar y generar el gateway, el modelo canónico y el adapter que aísla el esquema legacy
- Prompt principal (resumido): "construir la capa de transición del reto Legacy Escape (gateway, adapter, modelo canónico) y migrar el dominio Afiliaciones sin tocar Educación"
- Qué produjo: el servicio `src/gateway` con autenticación por token, auditoría con documentos enmascarados y errores uniformes, y `src/adapter/legacy_repository.py` que detecta el esquema original o renombrado en cada consulta
- Qué modificó o corrigió el equipo: se revisó que ningún nombre legacy apareciera fuera del adapter con `./validator entregables`, se verificó que las respuestas fueran idénticas antes y después de `scripts/schema-change.sh`, y se decidió degradar un código de estado desconocido a SUSPENDED en vez de ACTIVE

## Uso 2
- Herramienta: Claude (Claude Code)
- Para qué se usó: diseñar la escritura de retiros idempotente y la tolerancia a la caída del legacy
- Prompt principal (resumido): "retiros que no se pierdan ni se dupliquen si la base se detiene, con respuesta 503 en menos de 3 segundos"
- Qué produjo: una cola SQLite con patrón outbox, una tabla de idempotencia escrita en la misma transacción del procedimiento legacy y un interruptor de circuito
- Qué modificó o corrigió el equipo: la primera versión solo usaba el timeout de conexión del driver, que no cubre la resolución DNS de un contenedor detenido; se agregó un plazo máximo por llamada en un hilo aparte y un circuito que deja pasar una sola llamada de prueba

## Uso 3
- Herramienta: Claude (Claude Code)
- Para qué se usó: escribir las pruebas automatizadas y el script de recorrido de los tres eventos del reto
- Prompt principal (resumido): "pruebas pytest del contrato con limpieza de datos y un script que pruebe caída, cambio de esquema, app móvil y rollback"
- Qué produjo: 38 pruebas en `tests/`, el servicio `tests` del compose y `scripts/scenarios.sh` con 29 verificaciones
- Qué modificó o corrigió el equipo: una prueba de Subsidios con un motivo con tilde devolvió 502 y reveló que el gateway fallaba con texto no ASCII; se forzó la codificación UTF-8 en la conexión y se agregó protección para que un retiro defectuoso no bloquee la cola

## Uso 4
- Herramienta: Claude (Claude Code)
- Para qué se usó: redactar la documentación obligatoria y revisarla con el validador de entregables
- Prompt principal (resumido): "llenar README, OpenAPI, mapa de dependencias, plan de migración y arquitectura con el formato exigido"
- Qué produjo: `README.md`, `openapi.yaml` y los tres documentos de `docs/` con las tablas y secciones del reto
- Qué modificó o corrigió el equipo: el validador reportó rutas faltantes en el README porque líneas que empezaban con # dentro de un bloque de código cortaban la sección Uso; se reemplazaron esas líneas y se corrigió un error de sintaxis YAML en `openapi.yaml`

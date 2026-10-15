# Arquitectura

## Contexto

La Caja de Compensación opera sobre una base legacy (réplica de Informix/Genero en PostgreSQL) que se volvió el punto de
integración de todo: Educación la lee directo, Subsidios escribe retiros con un procedimiento no idempotente y los
reportes nocturnos la consultan. Cambiar una columna rompe varias aplicaciones (incidente de 2019), un reintento duplicó
un retiro (2021), una caída de 40 minutos perdió retiros (2023) y un informe expuso documentos completos (2025). La política
nueva es que **ninguna aplicación nueva se conecta directo a la base**: se moderniza dominio por dominio, sin Big Bang.

## Componentes

```text
Portal / Subsidios / Móvil ──HTTP+Bearer──▶ gateway ──▶ modelo canónico ──▶ adapter ──▶ legacy-db ◀── Educación (sin cambios)
                                              │  └─ cola de retiros (SQLite, volumen gateway-data)
                                              └──── logs/audit.log (una línea JSON por petición)
```

- **gateway** (`src/gateway`): API REST en el puerto 8082. Autentica por token (un consumidor por token), aplica
  permisos (la app móvil es de solo lectura), audita cada petición con el documento enmascarado y responde errores
  uniformes `{message, error_id}` sin trazas ni SQL.
- **adapter** (`src/adapter/legacy_repository.py`): el único código que conoce tablas, columnas, códigos y el
  procedimiento `sp_registrar_retiro`. Detecta en cada consulta si el esquema es el original o el renombrado.
- **Circuito y plazo** (`resilience.py`): ninguna llamada al legacy espera más de 2,5 s; si falla, se responde 503
  `LEGACY_UNAVAILABLE` de inmediato durante 1 s y se deja pasar una sola llamada de prueba.
- **Cola de retiros** (`outbox.py`): bitácora write-ahead en SQLite sobre un volumen. Si el legacy está caído el retiro se acepta (202),
  y un hilo lo aplica cuando la base vuelve. La idempotencia vive en el legacy (tabla `gw_retiro_request`, misma transacción que el
  procedimiento), así que "una sola vez" sobrevive a reinicios del gateway.
- **subsidios-app**: registra por el gateway en DUAL/MODERN y por `sp_registrar_retiro` en LEGACY (rollback). **educacion-app**
  no se modifica. **portal-client** solo conoce `GATEWAY_URL`. **tests** corre pytest contra la API en marcha.

## Modelo canónico

El resto del sistema habla un vocabulario propio, independiente del legacy: `Member { document, fullName, status, company }`,
`Beneficiary { document, fullName, relationship }`, `Company { id, name, activeMembers }` y `RetirementOutcome`. El adapter traduce
`A/R/S` a `ACTIVE/RETIRED/SUSPENDED`, `C/H/P/M` a `SPOUSE/CHILD/FATHER/MOTHER` y concatena los cuatro campos de nombre en `fullName`.
Un código desconocido nunca se presenta como `ACTIVE`: se degrada a `SUSPENDED` (no apto) para fallar del lado seguro.
El contrato HTTP (`openapi.yaml`) se define sobre este modelo, no sobre las tablas.

## Cambio de esquema

`scripts/schema-change.sh` renombra `AFI_MAE → PERSON_MASTER`, `NRO_DOC → DOCUMENT_NUMBER` y `EST_AFI → STATUS_CODE`. El adapter
consulta `to_regclass('person_master')` al inicio de cada operación y elige el juego de nombres correspondiente, de modo que
no hace falta reiniciar ni desplegar nada: las respuestas de `members`, `beneficiaries` y `companies` son idénticas antes y después.
Esto está verificado por `scripts/scenarios.sh` (compara byte a byte las respuestas) y las pruebas pasan con ambos esquemas.
Solo el adapter cambió su comportamiento; el portal, Subsidios y la app móvil no se enteran.

## Alternativas descartadas

- **Migración Big Bang** (reescribir todo y apagar el legacy): descartada porque obliga a una ventana de parada, no tiene
  rollback creíble y la dirección pidió explícitamente no apagar el negocio.
- **Que cada aplicación nueva lea la base con vistas de compatibilidad**: descartada porque deja a todas acopladas al esquema
  y viola la política de no conexión directa; el próximo renombre volvería a romper a varias a la vez.
- **Caché con datos viejos cuando el legacy cae**: descartada porque el reto exige 503 explícito y porque servir un estado
  de afiliación desactualizado (por ejemplo un afiliado ya retirado) causa errores de negocio peores que un reintento.
- **Idempotencia solo en el gateway (SQLite)**: descartada porque un corte entre el commit del legacy y la anotación local
  duplicaría el retiro; con la clave en la misma transacción del legacy no existe esa ventana.
- **Un broker de mensajes (Kafka/RabbitMQ) para la cola**: descartado por ahora; añade un componente operativo para un volumen
  bajo, y el patrón outbox sobre SQLite cubre el requisito. Se reevalúa al pasar a MODERN.

# Mapa de dependencias del legacy

Quién lee y quién escribe cada tabla de la base legacy **hoy** (antes de que el gateway sea el único
camino de las aplicaciones nuevas). Fuente: `docs/procesos.md`, el código de `services/` y el esquema de `db/init/`.

| Aplicación | Tabla | Operación | Criticidad |
|---|---|---|---|
| Educación | AFI_MAE | Lectura | Alta |
| Educación | EMPRESA | Lectura | Media |
| Subsidios | AFI_MAE | Escritura | Alta |
| Subsidios | LOGMOV | Escritura | Alta |
| Reportes nocturnos | AFI_MAE | Lectura | Media |
| Reportes nocturnos | LOGMOV | Lectura | Media |
| Gateway (adapter) | AFI_MAE | Lectura | Alta |
| Gateway (adapter) | AFI_BEN | Lectura | Media |
| Gateway (adapter) | EMPRESA | Lectura | Media |
| Gateway (adapter) | LOGMOV | Escritura | Alta |

## Criterios de la tabla

- **Criticidad Alta:** si falla, se pierde información de negocio o se bloquea una operación del día
  (matrículas subsidiadas de Educación, registro de retiros de Subsidios).
- **Criticidad Media:** consultas y reportes que pueden esperar horas sin daño económico.
- Las filas del gateway describen la **única** dependencia nueva y están acotadas al adapter
  (`src/adapter/legacy_repository.py`). El gateway escribe `LOGMOV` y `AFI_MAE` solo a través del
  procedimiento `sp_registrar_retiro`; además guarda su control de idempotencia en la tabla propia `gw_retiro_request`.

## Aplicaciones sin acceso directo

El **Portal de servicios** y la **app móvil** no tocan ninguna tabla: hablan HTTP con el gateway
(`PORTAL_TOKEN` y `MOBILE_TOKEN`). La app móvil además es de solo lectura (403 en cualquier escritura).

## Qué cambia con la migración

| Tabla | Hoy | Meta (MODERN) |
|---|---|---|
| AFI_MAE | Educación, Reportes y Subsidios (vía procedimiento) | Solo el adapter; Educación consume `GET /api/v1/members/{document}` |
| LOGMOV | Subsidios (vía procedimiento) y Reportes | Solo el adapter; Reportes consume una API de movimientos |
| EMPRESA | Educación | Solo el adapter |
| AFI_BEN | (nadie directo; solo el portal antiguo) | Solo el adapter |

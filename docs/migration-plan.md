# Plan de migración por dominio

Estrategia **strangler**: el gateway se pone delante del legacy y cada dominio avanza
`LEGACY → DUAL → MODERN` por separado, sin apagar nada y sin migración Big Bang.

- **LEGACY:** las aplicaciones usan el camino original. El gateway no participa en las escrituras.
- **DUAL:** el gateway es el camino de las aplicaciones nuevas y de las escrituras de Subsidios, pero la
  base legacy sigue siendo la fuente de verdad y el camino viejo sigue vivo para volver atrás.
- **MODERN:** el gateway es el único camino y el legacy queda solo como almacenamiento detrás del adapter.

El estado real de cada dominio lo publica `GET /api/v1/migration/status` y se guarda en `state/<dominio>.mode`.

| Dominio | Estado | Criterio para avanzar | Rollback |
|---|---|---|---|
| Afiliaciones | DUAL | 7 días sin diferencias entre gateway y legacy, 0 retiros perdidos o duplicados y p95 de consulta menor a 300 ms | ./rollback.sh affiliations |
| Empresas | LEGACY | Educación consume GET /api/v1/companies/{id} durante 5 días hábiles con 0 errores 5xx | scripts/set-mode.sh companies LEGACY y Educación vuelve a leer EMPRESA |
| Aportes | LEGACY | API de aportes publicada y conciliada con APORTES en 3 cierres mensuales consecutivos | scripts/set-mode.sh contributions LEGACY y los reportes leen APORTES directo |
| Reportes | LEGACY | 100% de los reportes nocturnos leen por API durante 14 noches sin diferencias de conteo | scripts/set-mode.sh reports LEGACY y se reactiva la lectura directa |

Siguiente dominio: Empresas

## Cómo se avanza y cómo se vuelve

1. **Avanzar:** `scripts/set-mode.sh <dominio> DUAL` (o `MODERN`). Es un archivo de estado: aplica en menos de un segundo, sin reiniciar.
2. **Evidencia:** `logs/audit.log` (una línea JSON por petición) y `GET /api/v1/ops/stats` (cola, circuito, conteos).
3. **Volver atrás:** `./rollback.sh affiliations` deja el dominio en LEGACY en menos de 1 segundo (la meta del reto es menos de 3 minutos).
   Subsidios vuelve a `sp_registrar_retiro`; no depende de que el gateway esté vivo. Los retiros que el gateway ya aceptó (202)
   siguen en su cola y se aplican una sola vez cuando el legacy responde.
4. **Dato al volver:** como el legacy fue siempre la fuente de verdad en DUAL, no hay datos que reconciliar al hacer rollback.

## Riesgos conocidos

- El camino LEGACY de Subsidios conserva el defecto histórico de `sp_registrar_retiro` (no es idempotente): un reintento
  manual en modo LEGACY puede duplicar el movimiento. Por eso el modo normal es DUAL.
- Pasar a MODERN exige decidir qué sistema es la fuente de verdad; hasta entonces no se avanza ese estado.

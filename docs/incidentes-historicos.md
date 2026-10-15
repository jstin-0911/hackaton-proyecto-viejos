# Incidentes históricos

- **2019-03:** se renombró `NOM_AFI` a `NOM1`/`NOM2` y tres aplicaciones dejaron de funcionar una semana.
- **2021-07:** un reintento automático de Subsidios registró dos veces el mismo retiro (dos filas `RET` en `LOGMOV`);
  Auditoría tuvo que corregirlo a mano.
- **2023-11:** la base estuvo detenida 40 minutos por mantenimiento; los retiros de esa franja se perdieron porque
  Subsidios no reintentó.
- **2025-02:** un informe expuso documentos completos en logs de acceso. Desde entonces los documentos se registran
  enmascarados (máximo 4 dígitos visibles).

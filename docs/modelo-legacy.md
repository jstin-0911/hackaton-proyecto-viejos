# Modelo de datos legacy (documentación parcial)

> Recuperado de la documentación de 2014. Puede estar incompleto.

| Tabla | Propósito | Columnas principales |
|---|---|---|
| `AFI_MAE` | Maestro de afiliados | `NRO_DOC`, `TIP_DOC`, `NOM1`, `NOM2`, `APE1`, `APE2`, `EST_AFI`, `COD_EMP`, `FEC_AFI`, `FEC_RET` |
| `AFI_BEN` | Beneficiarios | `NRO_DOC_BEN`, `NRO_DOC` (afiliado), `NOM1`, `NOM2`, `APE1`, `APE2`, `COD_PAR` |
| `EMPRESA` | Empresas aportantes | `COD_EMP`, `NOM_EMP`, `NIT`, `EST_EMP` |
| `APORTES` | Aportes mensuales | `NRO_DOC`, `PER_APO` (`YYYYMM`), `VLR_APO` |
| `LOGMOV` | Bitácora de movimientos | `ID_MOV`, `NRO_DOC`, `TIP_MOV` (`AFI`, `RET`), `FEC_MOV`, `USR_MOV`, `OBS_MOV` |

## Códigos

- `EST_AFI`: `A` activo · `R` retirado · `S` suspendido.
- `COD_PAR`: `C` cónyuge · `H` hijo(a) · `P` padre · `M` madre.

## Procedimientos

- `sp_registrar_retiro(p_nro_doc, p_fecha, p_motivo, p_usuario DEFAULT 'SUBSIDIOS')`: marca `EST_AFI = 'R'`,
  guarda `FEC_RET` e inserta un movimiento `RET` en `LOGMOV`. **No es idempotente.**

Ejemplo: `SELECT sp_registrar_retiro('1012345678', DATE '2026-10-05', 'Retiro voluntario');`

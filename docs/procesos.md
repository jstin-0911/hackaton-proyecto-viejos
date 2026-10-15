# Procesos y aplicaciones

| Aplicación | Proceso | Acceso a la base hoy |
|---|---|---|
| Educación (`educacion-app`, :8090) | Verifica afiliación antes de matricular en cursos subsidiados | Lee `AFI_MAE` y `EMPRESA` |
| Portal de servicios (`portal-client`, :8092) | Ficha del afiliado: datos, beneficiarios, empresa | Solo HTTP a `GATEWAY_URL` |
| Subsidios (`subsidios-app`, :8091) | Registra retiros | `sp_registrar_retiro` (escribe `AFI_MAE` y `LOGMOV`) |
| Reportes nocturnos | Conteos por empresa y estado | Lee `AFI_MAE`, `LOGMOV` |

## Cómo verificar lo que ve Educación

```bash
curl http://localhost:8090/afiliados/<documento>
```

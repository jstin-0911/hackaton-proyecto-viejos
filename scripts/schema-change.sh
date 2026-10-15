#!/usr/bin/env bash
# Evento 1 — Cambio de esquema aprobado por el DBA.
#   AFI_MAE -> PERSON_MASTER, NRO_DOC -> DOCUMENT_NUMBER, EST_AFI -> STATUS_CODE
# El DBA también actualiza sp_registrar_retiro. El portal y los contratos NO cambian.
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose exec -T legacy-db sh -c 'psql -v ON_ERROR_STOP=1 -q -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
DO $$
BEGIN
    IF to_regclass('public.afi_mae') IS NULL THEN
        RAISE NOTICE 'El cambio de esquema ya estaba aplicado';
        RETURN;
    END IF;
    ALTER TABLE afi_mae RENAME TO person_master;
    ALTER TABLE person_master RENAME COLUMN nro_doc TO document_number;
    ALTER TABLE person_master RENAME COLUMN est_afi TO status_code;
END
$$;

CREATE OR REPLACE FUNCTION sp_registrar_retiro(
    p_nro_doc VARCHAR,
    p_fecha   DATE,
    p_motivo  VARCHAR,
    p_usuario VARCHAR DEFAULT 'SUBSIDIOS'
) RETURNS INTEGER AS $$
DECLARE
    v_rows INTEGER;
    v_id   INTEGER;
BEGIN
    UPDATE person_master
       SET status_code = 'R',
           fec_ret = p_fecha
     WHERE document_number = p_nro_doc;
    GET DIAGNOSTICS v_rows = ROW_COUNT;
    IF v_rows = 0 THEN
        RAISE EXCEPTION 'AFI-404 afiliado % no existe', p_nro_doc;
    END IF;
    INSERT INTO logmov (nro_doc, tip_mov, fec_mov, usr_mov, obs_mov)
    VALUES (p_nro_doc, 'RET', now(), p_usuario, p_motivo)
    RETURNING id_mov INTO v_id;
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;
SQL

echo "Cambio de esquema aplicado: PERSON_MASTER(DOCUMENT_NUMBER, STATUS_CODE)"

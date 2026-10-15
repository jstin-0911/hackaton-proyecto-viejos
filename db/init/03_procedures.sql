-- Procedimiento legacy usado por Subsidios para registrar retiros.
-- Escribe en AFI_MAE (estado y fecha de retiro) y deja el movimiento en LOGMOV.
-- No es idempotente: cada llamada inserta un movimiento.

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
    UPDATE afi_mae
       SET est_afi = 'R',
           fec_ret = p_fecha
     WHERE nro_doc = p_nro_doc;
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

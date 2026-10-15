-- Esquema heredado (réplica del modelo Informix/Genero). Nombres y códigos legacy.
--   AFI_MAE.EST_AFI : A = activo, R = retirado, S = suspendido
--   AFI_BEN.COD_PAR : C = cónyuge, H = hijo(a), P = padre, M = madre

CREATE TABLE empresa (
    cod_emp  VARCHAR(10) PRIMARY KEY,
    nom_emp  VARCHAR(120) NOT NULL,
    nit      VARCHAR(20),
    est_emp  CHAR(1) DEFAULT 'A'
);

CREATE TABLE afi_mae (
    nro_doc  VARCHAR(15) PRIMARY KEY,
    tip_doc  CHAR(2) NOT NULL DEFAULT 'CC',
    nom1     VARCHAR(40) NOT NULL,
    nom2     VARCHAR(40),
    ape1     VARCHAR(40) NOT NULL,
    ape2     VARCHAR(40),
    est_afi  CHAR(1) NOT NULL,
    cod_emp  VARCHAR(10) REFERENCES empresa (cod_emp),
    fec_afi  DATE,
    fec_ret  DATE
);

CREATE TABLE afi_ben (
    nro_doc_ben VARCHAR(15) PRIMARY KEY,
    nro_doc     VARCHAR(15) NOT NULL,
    nom1        VARCHAR(40) NOT NULL,
    nom2        VARCHAR(40),
    ape1        VARCHAR(40) NOT NULL,
    ape2        VARCHAR(40),
    cod_par     CHAR(1) NOT NULL
);

CREATE TABLE aportes (
    nro_doc  VARCHAR(15) NOT NULL,
    per_apo  CHAR(6) NOT NULL,
    vlr_apo  NUMERIC(12, 0) NOT NULL
);

CREATE TABLE logmov (
    id_mov   SERIAL PRIMARY KEY,
    nro_doc  VARCHAR(15) NOT NULL,
    tip_mov  CHAR(3) NOT NULL,
    fec_mov  TIMESTAMP NOT NULL DEFAULT now(),
    usr_mov  VARCHAR(20) NOT NULL,
    obs_mov  VARCHAR(200)
);

CREATE INDEX idx_afi_ben_doc ON afi_ben (nro_doc);
CREATE INDEX idx_logmov_doc ON logmov (nro_doc);

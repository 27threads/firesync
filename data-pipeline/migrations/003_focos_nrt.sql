-- Migration 003: índice só dos focos NRT (poucos, os mais recentes).
-- O importador apaga o NRT que o SP substituiu depois de cada arquivo; sem este índice cada DELETE
-- percorreria todos os focos do satélite. Idempotente.
CREATE INDEX IF NOT EXISTS focos_nrt ON focos (satelite, datahora_utc) WHERE qualidade = 'NRT';

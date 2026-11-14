-- Migration 003: índice só dos focos NRT (poucos, os mais recentes), ordenado pelo tempo.
-- Atende duas consultas sem percorrer os ~46 milhões de focos:
--   1. o importador apaga o NRT que o SP substituiu (depois de cada arquivo);
--   2. a camada de focos recentes da API (últimas N horas): os últimos dias são sempre NRT (issue #5).
-- Idempotente.
CREATE INDEX IF NOT EXISTS focos_nrt ON focos (datahora_utc) WHERE qualidade = 'NRT';

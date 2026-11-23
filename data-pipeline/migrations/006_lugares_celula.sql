-- Migration 006: nome do lugar de cada célula H3 de resolução 4 (a unidade do risco e do alerta).
-- O job `lugares.py` cruza a célula com os municípios do IBGE, as unidades de conservação do MMA (CNUC) e as terras
-- indígenas da Funai, e grava aqui; a API só lê, para a lista "onde olhar primeiro" dizer de quem é a área.
-- Idempotente.
CREATE TABLE IF NOT EXISTS lugares_celula (
    h3                   BIGINT      PRIMARY KEY CHECK (((h3 >> 52) & 15) = 4),
    municipio            TEXT,
    uf                   TEXT,
    unidades_conservacao TEXT[]      NOT NULL DEFAULT '{}',
    terras_indigenas     TEXT[]      NOT NULL DEFAULT '{}',
    calculado_em         TIMESTAMPTZ NOT NULL
);

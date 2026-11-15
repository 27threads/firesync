-- Migration 005: risco por célula (RFC 0003, decisão de 15/11/2026).
-- O modelo treinado calcula, para cada célula H3 de resolução 4, a chance de ter fogo relevante (10 ou mais detecções)
-- nos 14 dias seguintes. O job `risco_celulas.py` pontua fora da API e grava aqui; a API só lê.
-- Idempotente.
CREATE TABLE IF NOT EXISTS risco_celulas (
    h3            BIGINT      NOT NULL CHECK (((h3 >> 52) & 15) = 4),
    data_ref      DATE        NOT NULL,
    prob          REAL        NOT NULL CHECK (prob >= 0 AND prob <= 1),
    faixa         TEXT        NOT NULL CHECK (faixa IN ('very_high', 'high', 'medium', 'lower')),
    modelo_versao TEXT        NOT NULL,
    calculado_em  TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (h3, data_ref)
);
CREATE INDEX IF NOT EXISTS risco_celulas_data_ref ON risco_celulas (data_ref);

-- Migration 002: revisão do PR #2 (docs/banco.md).
-- Idempotente: pode rodar de novo, e roda tanto num banco novo quanto num que já tem a 001.

-- 1. Células de cada região numa tabela, não numa lista dentro de `regioes` (escala para o mundo).
CREATE TABLE IF NOT EXISTS celula_regiao (
    h3        BIGINT  NOT NULL CHECK (((h3 >> 52) & 15) = 6),
    regiao_id INTEGER NOT NULL REFERENCES regioes (id) ON DELETE CASCADE,
    PRIMARY KEY (h3, regiao_id)
);
CREATE INDEX IF NOT EXISTS celula_regiao_regiao ON celula_regiao (regiao_id);
ALTER TABLE regioes DROP COLUMN IF EXISTS celulas_h3;

-- 2. Dias sem dado de satélite (FIRMS missing_data). Vale para o mundo todo, não por célula.
--    A API conta quantos dias sem dado cada mês teve; o front marca o mês a partir de 3 dias.
CREATE TABLE IF NOT EXISTS dias_sem_dados (
    data     DATE NOT NULL,
    satelite TEXT NOT NULL CHECK (satelite IN ('Terra', 'Aqua', 'SNPP', 'N20', 'N21')),
    PRIMARY KEY (data, satelite)
);
ALTER TABLE agregados DROP COLUMN IF EXISTS sem_dados;

-- 3. Pedido do PR #3: quanto sustenta cada fator e qual condição vizinha foi usada.
ALTER TABLE fatores_harmonizacao ADD COLUMN IF NOT EXISTS n_focos_origem INTEGER;  -- focos do Aqua usados no fator
ALTER TABLE fatores_harmonizacao ADD COLUMN IF NOT EXISTS fusao_com TEXT;          -- condição vizinha quando o mínimo de focos não é atingido

-- Schema do banco firesync (PostgreSQL 16 + PostGIS).
-- Nomes de tabelas e colunas: docs/importacao-regioes.md. Decisões: docs/banco.md.
-- Idempotente: pode rodar de novo sem apagar dados.
-- H3 é calculado no Python (lib `h3`) e guardado como BIGINT: não depende da extensão h3-pg.

CREATE EXTENSION IF NOT EXISTS postgis;

-- Fonte única de configuração. O pipeline e a API leem daqui, sem número fixo no código.
CREATE TABLE IF NOT EXISTS config (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
INSERT INTO config (chave, valor) VALUES
    ('h3_resolucao', '6'),        -- mudar exige migration nova: refazer agregados e celula_regiao
    ('cobertura_pais', 'Brazil')  -- unidade de download do FIRMS (arquivo anual por país)
ON CONFLICT (chave) DO NOTHING;

-- Um foco detectado. Tudo o que foi baixado (cobertura), sem recorte por região.
-- Terra fica guardado, mas fora do cálculo.
CREATE TABLE IF NOT EXISTS focos (
    id             BIGSERIAL PRIMARY KEY,
    sensor         TEXT        NOT NULL CHECK (sensor IN ('MODIS', 'VIIRS')),
    satelite       TEXT        NOT NULL CHECK (satelite IN ('Terra', 'Aqua', 'SNPP', 'N20', 'N21')),
    lat            DOUBLE PRECISION NOT NULL,
    lon            DOUBLE PRECISION NOT NULL,
    datahora_utc   TIMESTAMPTZ NOT NULL,
    confianca      TEXT        NOT NULL CHECK (confianca IN ('baixa', 'nominal', 'alta')),
    frp            REAL,
    periodo        CHAR(1)     NOT NULL CHECK (periodo IN ('D', 'N')),
    tipo           SMALLINT,                       -- vazio no NRT (a coluna type não existe lá)
    qualidade      TEXT        NOT NULL CHECK (qualidade IN ('SP', 'NRT')),
    scan           REAL,                           -- tamanho do pixel; o time de dados usa no modelo
    track          REAL,
    arquivo_origem TEXT        NOT NULL,
    -- a resolução fica nos bits 52-55 do ID: carga na resolução errada falha aqui
    h3             BIGINT      NOT NULL CHECK (((h3 >> 52) & 15) = 6),
    UNIQUE (satelite, lat, lon, datahora_utc)      -- chave única do upsert
);
CREATE INDEX IF NOT EXISTS focos_h3_data ON focos (h3, datahora_utc);
CREATE INDEX IF NOT EXISTS focos_sat_data ON focos (satelite, datahora_utc);

-- Regiões de calibração (hoje: os 6 biomas do IBGE). Fonte de verdade para API, calibração e agregação.
-- Preenchida pelo comando `python pipeline.py cadastrar` a partir de regioes.json.
CREATE TABLE IF NOT EXISTS regioes (
    id             SERIAL PRIMARY KEY,
    nome           TEXT   NOT NULL UNIQUE,
    geom           geometry(MultiPolygon, 4326) NOT NULL,
    fonte_poligono TEXT   NOT NULL
);
CREATE INDEX IF NOT EXISTS regioes_geom ON regioes USING GIST (geom);

-- Quais células H3 pertencem a cada região (calculado no cadastro). Tabela, não lista: escala para o mundo.
CREATE TABLE IF NOT EXISTS celula_regiao (
    h3        BIGINT  NOT NULL CHECK (((h3 >> 52) & 15) = 6),
    regiao_id INTEGER NOT NULL REFERENCES regioes (id) ON DELETE CASCADE,
    PRIMARY KEY (h3, regiao_id)
);
CREATE INDEX IF NOT EXISTS celula_regiao_regiao ON celula_regiao (regiao_id);

-- Período em que cada satélite tem dado em cada região. A API responde "sem dados" fora daqui.
CREATE TABLE IF NOT EXISTS cobertura (
    regiao_id     INTEGER     NOT NULL REFERENCES regioes (id) ON DELETE CASCADE,
    satelite      TEXT        NOT NULL,
    data_inicio   DATE        NOT NULL,
    data_fim      DATE        NOT NULL,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (regiao_id, satelite)
);

-- Um fator por região × par de satélites × mês × dia/noite × ano de calibração.
-- Cada ano é um cenário: a mediana é o fator central e o P10-P90 é a faixa (calculados na API).
CREATE TABLE IF NOT EXISTS fatores_harmonizacao (
    regiao_id        INTEGER  NOT NULL REFERENCES regioes (id) ON DELETE CASCADE,
    satelite_origem  TEXT     NOT NULL,
    satelite_destino TEXT     NOT NULL,
    mes              SMALLINT NOT NULL CHECK (mes BETWEEN 1 AND 12),
    periodo          CHAR(1)  NOT NULL CHECK (periodo IN ('D', 'N')),
    ano_calibracao   SMALLINT NOT NULL,
    fator            REAL     NOT NULL,
    PRIMARY KEY (regiao_id, satelite_origem, satelite_destino, mes, periodo, ano_calibracao)
);

-- Contrato 1 (T01): o que a API lê. Contagem BRUTA por célula × mês × satélite × dia/noite;
-- a API soma a área e só depois aplica os fatores. Mês sem focos não tem linha (a API preenche zero).
CREATE TABLE IF NOT EXISTS agregados (
    h3           BIGINT   NOT NULL CHECK (((h3 >> 52) & 15) = 6),
    ano          SMALLINT NOT NULL,
    mes          SMALLINT NOT NULL CHECK (mes BETWEEN 1 AND 12),
    regiao_id    INTEGER  NOT NULL REFERENCES regioes (id) ON DELETE CASCADE,
    satelite     TEXT     NOT NULL,
    periodo      CHAR(1)  NOT NULL CHECK (periodo IN ('D', 'N')),
    focos_brutos INTEGER  NOT NULL,
    frp_soma     REAL     NOT NULL,
    PRIMARY KEY (h3, ano, mes, satelite, periodo)   -- também é o índice da consulta da API
);

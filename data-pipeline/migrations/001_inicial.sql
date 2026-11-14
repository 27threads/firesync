-- Schema do banco firesync (PostgreSQL 16 + PostGIS).
-- Nomes de tabelas e colunas: docs/importacao-regioes.md. Decisões: docs/banco.md.
-- Idempotente: pode rodar de novo sem apagar dados.
-- H3 é calculado no Python (lib `h3`) e guardado como BIGINT: não depende da extensão h3-pg.

CREATE EXTENSION IF NOT EXISTS postgis;

-- Um foco detectado. Brasil inteiro, todos os satélites (Terra fica guardado, mas fora do cálculo).
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
    h3             BIGINT      NOT NULL,           -- resolução definida em docs/banco.md
    UNIQUE (satelite, lat, lon, datahora_utc)      -- chave única do upsert
);
CREATE INDEX IF NOT EXISTS focos_h3_data ON focos (h3, datahora_utc);
CREATE INDEX IF NOT EXISTS focos_sat_data ON focos (satelite, datahora_utc);

-- Regiões são dado, não código.
CREATE TABLE IF NOT EXISTS regioes (
    id             SERIAL PRIMARY KEY,
    nome           TEXT   NOT NULL UNIQUE,
    geom           geometry(MultiPolygon, 4326) NOT NULL,
    celulas_h3     BIGINT[] NOT NULL DEFAULT '{}',
    fonte_poligono TEXT   NOT NULL
);
CREATE INDEX IF NOT EXISTS regioes_geom ON regioes USING GIST (geom);

-- Período em que cada satélite tem dado em cada região. A API responde "sem dados" fora daqui.
CREATE TABLE IF NOT EXISTS cobertura (
    regiao_id     INTEGER     NOT NULL REFERENCES regioes (id) ON DELETE CASCADE,
    satelite      TEXT        NOT NULL,
    data_inicio   DATE        NOT NULL,
    data_fim      DATE        NOT NULL,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (regiao_id, satelite)
);

-- Fatores de harmonização por região (frente B). Colunas conforme importacao-regioes.md;
-- podem mudar quando o método de harmonização for decidido.
CREATE TABLE IF NOT EXISTS fatores_harmonizacao (
    regiao_id          INTEGER   NOT NULL REFERENCES regioes (id) ON DELETE CASCADE,
    satelite_origem    TEXT      NOT NULL,
    satelite_destino   TEXT      NOT NULL,
    fator              REAL      NOT NULL,
    periodo_calibracao DATERANGE NOT NULL,
    n_meses            INTEGER   NOT NULL,
    PRIMARY KEY (regiao_id, satelite_origem, satelite_destino)
);

-- Contrato 1 (T01): o que a API lê. Uma linha por célula H3 × ano × mês, só células com dado.
CREATE TABLE IF NOT EXISTS agregados (
    h3                 BIGINT   NOT NULL,
    ano                SMALLINT NOT NULL,
    mes                SMALLINT NOT NULL CHECK (mes BETWEEN 1 AND 12),
    focos_harmonizados REAL     NOT NULL,
    focos_brutos       INTEGER  NOT NULL,
    frp_soma           REAL     NOT NULL,
    sem_dados          BOOLEAN  NOT NULL DEFAULT false,
    PRIMARY KEY (h3, ano, mes)   -- também é o índice da consulta da API
);

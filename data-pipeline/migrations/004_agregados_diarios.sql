-- Migration 004: contagens diárias (issue #8), para o "normal da época" de ±15 dias e o alerta.
-- Mesmo padrão de `agregados`, por dia em vez de mês. Só VIIRS (fev/2012 em diante), só dias com foco.
-- Idempotente.
CREATE TABLE IF NOT EXISTS agregados_diarios (
    h3           BIGINT   NOT NULL CHECK (((h3 >> 52) & 15) = 6),
    data         DATE     NOT NULL,
    regiao_id    INTEGER  NOT NULL REFERENCES regioes (id) ON DELETE CASCADE,
    satelite     TEXT     NOT NULL,
    periodo      CHAR(1)  NOT NULL CHECK (periodo IN ('D', 'N')),
    focos_brutos INTEGER  NOT NULL,
    PRIMARY KEY (h3, data, satelite, periodo)   -- atende a soma das células da área nas janelas de datas
);

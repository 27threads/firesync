"""Agregação: `focos` -> `agregados` (contagem bruta, sem harmonizar). Regras em docs/importacao-regioes.md.

Uso:
    python agregar.py                    # refaz a tabela inteira
    python agregar.py 2026-10 2026-11    # refaz só esses meses (job de atualização)

Cada execução é uma transação: apaga os meses do intervalo e grava de novo, então rodar duas vezes dá o mesmo resultado.
Na mesma transação refaz `agregados_diarios` (só VIIRS) e grava a versão em `config` (issue #15): quem lê vê
os dados e a versão novos juntos, ou os antigos juntos, nunca metade.
Datas em UTC: a conexão de pipeline.db() fixa o fuso.
"""
import sys
import time
from datetime import date, datetime, timezone

import logs
from pipeline import db, ms_desde

log = logs.logger("agregar")

# Satélite que vale em cada mês (tabela de importacao-regioes.md). Um satélite por mês, nunca a soma.
# Jan/2012 fica com o Aqua porque o S-NPP só começa em 20/01/2012; nov/2026 já é NOAA-20 (S-NPP parou em 02/11).
SATELITE_DO_MES = [
    (date(2003, 1, 1), date(2012, 2, 1), "Aqua"),
    (date(2012, 2, 1), date(2026, 11, 1), "SNPP"),
    (date(2026, 11, 1), date(9999, 1, 1), "N20"),
]

# As mesmas regras de limpeza estão em pandas em pipeline.py (clean). Mudou uma, mude a outra.
SQL = """
INSERT INTO agregados (h3, ano, mes, regiao_id, satelite, periodo, focos_brutos, frp_soma)
SELECT f.h3,
       extract(year FROM f.datahora_utc)::smallint,
       extract(month FROM f.datahora_utc)::smallint,
       cr.regiao_id, f.satelite, f.periodo, count(*), sum(f.frp)
FROM focos f
JOIN celula_regiao cr ON cr.h3 = f.h3
WHERE f.satelite = %(sat)s
  AND f.datahora_utc >= %(ini)s AND f.datahora_utc < %(fim)s
  AND f.confianca IN ('nominal', 'alta')                      -- baixa confiança fica fora do fator e do calendário
  AND (f.tipo = 0 OR (f.tipo IS NULL AND f.qualidade = 'NRT'))  -- type != 0 sai; NRT não tem type e fica
  AND f.frp > 0                                               -- FRP vazio, zero ou negativo sai
GROUP BY 1, 2, 3, 4, 5, 6
"""

# Contagem diária (issue #8): mesmos filtros, por dia. Só VIIRS: o Aqua não entra no normal da janela recente.
SQL_DIA = """
INSERT INTO agregados_diarios (h3, data, regiao_id, satelite, periodo, focos_brutos)
SELECT f.h3, f.datahora_utc::date, cr.regiao_id, f.satelite, f.periodo, count(*)
FROM focos f
JOIN celula_regiao cr ON cr.h3 = f.h3
WHERE f.satelite = %(sat)s
  AND f.datahora_utc >= %(ini)s AND f.datahora_utc < %(fim)s
  AND f.confianca IN ('nominal', 'alta')
  AND (f.tipo = 0 OR (f.tipo IS NULL AND f.qualidade = 'NRT'))
  AND f.frp > 0
GROUP BY 1, 2, 3, 4, 5
"""
# Para o log: quantos focos entraram no calendário (as linhas são células × mês, não focos).
FOCOS_DA_JANELA = """SELECT coalesce(sum(focos_brutos), 0) FROM agregados
                     WHERE satelite = %(sat)s AND make_date(ano, mes, 1) >= %(ini)s AND make_date(ano, mes, 1) < %(fim)s"""
VERSAO = """INSERT INTO config (chave, valor) VALUES (%s, %s)
            ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor"""


def janelas(de, ate):
    """Corta [de, ate) nos períodos de SATELITE_DO_MES -> [(satélite, início, fim)]."""
    out = []
    for ini, fim, sat in SATELITE_DO_MES:
        a, b = max(ini, de), min(fim, ate)
        if a < b:
            out.append((sat, a, b))
    return out


def mes(s):
    y, m = map(int, s.split("-"))
    return date(y, m, 1)


def proximo_mes(d):
    return date(d.year + d.month // 12, d.month % 12 + 1, 1)


INICIO, FIM = date(2003, 1, 1), date(9999, 1, 1)


def agregar(de=INICIO, ate=FIM):
    """Refaz `agregados` e `agregados_diarios` do intervalo e grava a versão, tudo num commit. Devolve a versão."""
    conn = db()
    inicio = time.monotonic()
    versao = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    completa = (de, ate) == (INICIO, FIM)
    log.info("aggregate_started", start=de, end=ate, scope="full" if completa else "partial")
    with conn.transaction():
        apagadas = conn.execute(
            "DELETE FROM agregados WHERE make_date(ano, mes, 1) >= %s AND make_date(ano, mes, 1) < %s",
            (de, ate)).rowcount
        apagadas_dia = conn.execute("DELETE FROM agregados_diarios WHERE data >= %s AND data < %s",
                                    (de, ate)).rowcount
        for sat, ini, fim in janelas(de, ate):
            n = conn.execute(SQL, {"sat": sat, "ini": ini, "fim": fim}).rowcount
            d = 0 if sat == "Aqua" else conn.execute(SQL_DIA, {"sat": sat, "ini": ini, "fim": fim}).rowcount
            focos = conn.execute(FOCOS_DA_JANELA, {"sat": sat, "ini": ini, "fim": fim}).fetchone()[0]
            log.info("aggregate_window_done", satellite=sat, start=ini, end=fim, monthly_rows=n, daily_rows=d,
                     detections=focos, daily_skipped=sat == "Aqua")
        # `atualizado_em` muda a cada escrita (é a chave do cache da API); `data_version` só na carga completa
        # (a API recarrega os fatores). Data e hora: duas cargas no mesmo dia dão versões diferentes.
        conn.execute(VERSAO, ("atualizado_em", versao))
        if completa:
            conn.execute(VERSAO, ("data_version", versao))
    log.info("aggregate_finished", scope="full" if completa else "partial", updated_at=versao,
             data_version_changed=completa, monthly_rows_deleted=apagadas, daily_rows_deleted=apagadas_dia,
             duration_ms=ms_desde(inicio))
    return versao


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        agregar()
    else:
        agregar(mes(args[0]), proximo_mes(mes(args[-1])))

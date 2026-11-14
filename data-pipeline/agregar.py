"""Agregação: `focos` -> `agregados` (contagem bruta, sem harmonizar). Regras em docs/importacao-regioes.md.

Uso:
    python agregar.py                    # refaz a tabela inteira
    python agregar.py 2026-10 2026-11    # refaz só esses meses (job de atualização)

Cada execução é uma transação: apaga os meses do intervalo e grava de novo, então rodar duas vezes dá o mesmo resultado.
Datas em UTC: a conexão de pipeline.db() fixa o fuso.
"""
import sys
from datetime import date

from pipeline import db

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
    conn = db()
    with conn.transaction():
        conn.execute("DELETE FROM agregados WHERE make_date(ano, mes, 1) >= %s AND make_date(ano, mes, 1) < %s",
                     (de, ate))
        for sat, ini, fim in janelas(de, ate):
            n = conn.execute(SQL, {"sat": sat, "ini": ini, "fim": fim}).rowcount
            print(f"agregar: {sat} {ini} a {fim}: {n:,} linhas", flush=True)
        if (de, ate) == (INICIO, FIM):
            # tabela inteira refeita: é o `data_version` da API (quando os dados foram carregados)
            conn.execute("""INSERT INTO config (chave, valor) VALUES ('data_version', CURRENT_DATE::text)
                            ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor""")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        agregar()
    else:
        agregar(mes(args[0]), proximo_mes(mes(args[-1])))

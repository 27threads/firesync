"""B3. Calibração Aqua -> S-NPP (escala VIIRS): fatores por bioma x mês x dia/noite, um cenário por ano.

Regras: docs/decisoes-harmonizacao.md (seção 4) e docs/importacao-regioes.md ("Fórmula do calendário").

O que faz:
  1. Conta focos por bioma, dia, período e satélite (Aqua e S-NPP), de fev/2012 a dez/2024, só SP,
     confiança nominal e alta, tipo = 0, FRP > 0. Tira os dias em que o Aqua OU o S-NPP aparecem em
     `dias_sem_dados`, e janeiro de 2012 (S-NPP incompleto).
  2. Para cada ano k (cenário): F_k = soma do S-NPP / soma do Aqua, por bioma x mês x período (razão das somas).
     Se o Aqua tem menos que o mínimo de focos, aplica a fusão na ordem de ORDEM_FUSAO (meses vizinhos no mesmo
     período, depois o ano inteiro no mesmo período, depois o ano inteiro com dia e noite) e registra em `fusao_com`.
  3. Validação deixando um ano de fora: para cada ano y, os fatores dos outros anos estimam y a partir do Aqua de y.
     Estimado = mediana entre cenários de E_k = soma(Aqua_y x F_k) (a mesma conta da API). Faixa = P5 e P95 de E_k (FAIXA),
     interpolação linear. Compara com o S-NPP real de y.
  4. Critério fixado antes de rodar: se o erro médio de 2022-2024 passar de 1,5x o de 2012-2021 (Amazônia),
     ficam só 2012-2021; senão, 2012-2024.
  5. Grava os fatores dos anos escolhidos em `fatores_harmonizacao` (com --gravar), numa transação.

Uso (dentro de data-pipeline/, com DATABASE_URL configurado como no pipeline.py):
    python harmonizacao/calibrar.py --saida relatorios/calibracao                  # só calcula e salva os CSVs
    python harmonizacao/calibrar.py --saida relatorios/calibracao --gravar         # também grava no banco
    python harmonizacao/calibrar.py --csv contagens.csv --saida pasta              # sem banco (testes)

Opções:
    --minimo N            mínimo de focos do Aqua para ter fator próprio (padrão 30; ESCOLHA DA EQUIPE, ainda em aberto)
    --erro simples|ponderado
                          medida de erro do ano que decide o critério. Padrão "ponderado" (soma|e-o| / soma o),
                          aprovado no PR #4. "simples" (média de |e-o|/o nos meses) era o critério original do PR #3.
                          O relatório mostra as duas de qualquer forma.

Saídas na pasta --saida:
    fatores_todos_os_anos.csv   um fator por bioma x mês x período x ano (2012-2024), com n_focos_origem e fusao_com
    validacao_anos.csv          erro de cada ano (as duas medidas) e cobertura da faixa, por bioma
    validacao_meses.csv         estimado, faixa (P5 e P95) e observado de cada bioma x ano x mês
    relatorio.txt               resumo e a decisão dos anos
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ANOS_BASE = list(range(2012, 2025))
ANOS_ANTES_DERIVA = list(range(2012, 2022))
ANOS_DEPOIS_DERIVA = [2022, 2023, 2024]
LIMITE_CRITERIO = 1.5           # ESCOLHA DA EQUIPE (PR #3)
REGIAO_DA_DECISAO = "Amazônia"  # a decisão dos anos usa a Amazônia, que tem mais focos
# Percentis da faixa, os mesmos da API (interpolação linear). Com poucos cenários, a faixa entre percentis cobre
# menos do que o nome sugere: para um ano novo, a chance esperada de cair dentro é cerca de
#   P10-P90: ~68% com 12 cenários (validação) e ~69% com 13 (série)
#   P5-P95:  ~78% com 12 cenários (validação) e ~79% com 13 (série)
# (simulação com anos intercambiáveis, 200 mil sorteios)
# A primeira rodada com P10-P90 mediu 0,58 a 0,69. Troca para P5-P95 decidida pelo Weberson em 14/11/2026.
FAIXA = (5, 95)

# Ordem da fusão quando o Aqua não atinge o mínimo (docs/decisoes-harmonizacao.md):
#   "vizinhos": meses m-1 e m+1 no mesmo período e mesmo ano (dezembro e janeiro são vizinhos)
#   "ano_periodo": o ano inteiro do bioma, só no mesmo período (noite com noite)
#   "ano": o ano inteiro do bioma, dia e noite juntos (último recurso)
# Dia e noite só se juntam no fim porque o fator noturno é ~5x o diurno (B1, 2024): juntar antes
# puxaria o fator da noite para o do dia (ex.: Caatinga, março, noite: 25,4 próprio -> 9,4 com dia e noite).
ORDEM_FUSAO = ["vizinhos", "ano_periodo", "ano"]

SQL_CONTAGENS = """
SELECT r.nome AS regiao, (f.datahora_utc)::date AS data, f.periodo, f.satelite, count(*) AS focos
FROM focos f
JOIN celula_regiao cr ON cr.h3 = f.h3
JOIN regioes r ON r.id = cr.regiao_id
WHERE f.satelite IN ('Aqua', 'SNPP')
  AND f.datahora_utc >= '2012-02-01' AND f.datahora_utc < '2025-01-01'   -- janeiro de 2012 fora
  AND f.qualidade = 'SP'
  AND f.confianca IN ('nominal', 'alta')
  AND f.tipo = 0
  AND f.frp > 0
  AND NOT EXISTS (                                  -- dia sem dado de qualquer um dos dois satélites sai
      SELECT 1 FROM dias_sem_dados d
      WHERE d.data = (f.datahora_utc)::date AND d.satelite IN ('Aqua', 'SNPP'))
GROUP BY 1, 2, 3, 4
"""


# ---------------------------------------------------------------- entrada

def contagens_do_banco():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from pipeline import db  # mesma conexão do pipeline (UTC)
    conn = db()
    return pd.DataFrame(conn.execute(SQL_CONTAGENS).fetchall(),
                        columns=["regiao", "data", "periodo", "satelite", "focos"])


def contagens_do_csv(caminho):
    """CSV com as colunas regiao, data, periodo, satelite, focos (uma linha por dia). Para testes sem banco."""
    return pd.read_csv(caminho)


def mensal(diario):
    d = diario.copy()
    d["data"] = pd.to_datetime(d["data"])
    d = d[d["data"] >= "2012-02-01"]
    d["ano"] = d["data"].dt.year
    d["mes"] = d["data"].dt.month
    t = d.pivot_table(index=["regiao", "ano", "mes", "periodo"], columns="satelite", values="focos",
                      aggfunc="sum", fill_value=0)
    t = t.reindex(columns=["Aqua", "SNPP"], fill_value=0).rename(columns={"Aqua": "A", "SNPP": "S"})
    return t.reset_index()


# ---------------------------------------------------------------- fatores

def fatores_por_ano(m, minimo):
    """Um fator por regiao x ano x mes x periodo, com a fusão quando o Aqua não atinge o mínimo."""
    linhas = []
    for (regiao, ano), g in m.groupby(["regiao", "ano"]):
        g = g.set_index(["mes", "periodo"])[["A", "S"]]
        meses = sorted(set(g.index.get_level_values(0)))
        for mes in meses:
            for periodo in ("D", "N"):
                a, s = (g.loc[(mes, periodo)] if (mes, periodo) in g.index else (0, 0))
                fator, fusao, n = (s / a if a > 0 else np.nan), None, a
                if a < minimo:
                    for nivel in ORDEM_FUSAO:
                        if nivel == "vizinhos":
                            viz = [(mes - 2) % 12 + 1, mes, mes % 12 + 1]
                            sel = [(x, periodo) for x in viz if (x, periodo) in g.index]
                            rotulo = f"meses {viz[0]}, {mes} e {viz[2]} ({periodo})"
                        elif nivel == "ano_periodo":
                            sel = [x for x in g.index if x[1] == periodo]
                            rotulo = f"ano inteiro ({periodo})"
                        else:
                            sel = list(g.index)
                            rotulo = "ano inteiro, dia e noite"
                        sa, ss = g.loc[sel, "A"].sum(), g.loc[sel, "S"].sum()
                        if sa >= minimo:
                            fator, fusao, n = ss / sa, rotulo, sa
                            break
                    else:
                        # nem o ano inteiro atinge o mínimo: usa o que houver, se houver Aqua
                        sa, ss = g["A"].sum(), g["S"].sum()
                        fator, fusao, n = ((ss / sa) if sa > 0 else np.nan), "ano inteiro (abaixo do mínimo)", sa
                linhas.append({"regiao": regiao, "ano": ano, "mes": mes, "periodo": periodo,
                               "fator": fator, "n_focos_origem": int(n), "fusao_com": fusao})
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------- validação

def estimar(aqua_mes, fatores, anos_cenario):
    """aqua_mes: A de um bioma x ano x mês por período. Devolve (mediana, faixa_baixa, faixa_alta, n_cenarios) de E_k."""
    e = []
    for k in anos_cenario:
        f = fatores.get(k)
        if f is None:
            continue
        valores = [aqua_mes.get(p, 0) * f[p] for p in ("D", "N") if p in f and not np.isnan(f[p])]
        faltando = [p for p in ("D", "N") if aqua_mes.get(p, 0) > 0 and (p not in f or np.isnan(f[p]))]
        if faltando:
            continue  # cenário sem fator para um período com Aqua: não entra
        e.append(sum(valores))
    if not e:
        return np.nan, np.nan, np.nan, 0
    e = np.array(e)
    return float(np.median(e)), float(np.percentile(e, FAIXA[0])), float(np.percentile(e, FAIXA[1])), len(e)


def validar(m, fat):
    """Deixa um ano de fora por vez. Devolve uma linha por regiao x ano x mes."""
    f_idx = {}
    for r in fat.itertuples():
        f_idx.setdefault((r.regiao, r.mes), {}).setdefault(r.ano, {})[r.periodo] = r.fator
    linhas = []
    for (regiao, ano, mes), g in m.groupby(["regiao", "ano", "mes"]):
        aqua = dict(zip(g["periodo"], g["A"]))
        obs = int(g["S"].sum())
        outros = [k for k in ANOS_BASE if k != ano]
        est, baixa, alta, n = estimar(aqua, f_idx.get((regiao, mes), {}), outros)
        linhas.append({"regiao": regiao, "ano": ano, "mes": mes, "aqua": int(g["A"].sum()), "observado": obs,
                       "estimado": est, "faixa_baixa": baixa, "faixa_alta": alta, "n_cenarios": n})
    return pd.DataFrame(linhas)


def erros_por_ano(v):
    v = v.dropna(subset=["estimado"]).copy()
    v["erro_abs"] = (v["estimado"] - v["observado"]).abs()
    v["dentro"] = (v["observado"] >= v["faixa_baixa"]) & (v["observado"] <= v["faixa_alta"])
    linhas = []
    for (regiao, ano), g in v.groupby(["regiao", "ano"]):
        com_obs = g[g["observado"] > 0]
        linhas.append({
            "regiao": regiao, "ano": ano, "meses": len(g),
            "erro_simples": float((com_obs["erro_abs"] / com_obs["observado"]).mean()) if len(com_obs) else np.nan,
            "erro_ponderado": float(g["erro_abs"].sum() / g["observado"].sum()) if g["observado"].sum() else np.nan,
            "cobertura_faixa": float(g["dentro"].mean()),
        })
    return pd.DataFrame(linhas)


def decidir(erros, medida):
    e = erros[erros["regiao"] == REGIAO_DA_DECISAO].set_index("ano")[medida]
    antes = e.reindex(ANOS_ANTES_DERIVA).mean()
    depois = e.reindex(ANOS_DEPOIS_DERIVA).mean()
    razao = depois / antes if antes else np.nan
    anos = ANOS_ANTES_DERIVA if razao > LIMITE_CRITERIO else ANOS_BASE
    return anos, antes, depois, razao


# ---------------------------------------------------------------- saída

def gravar(fatores, anos):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from pipeline import db
    conn = db()
    ids = dict(conn.execute("SELECT nome, id FROM regioes").fetchall())
    f = fatores[fatores["ano"].isin(anos) & fatores["fator"].notna()]
    with conn.transaction():
        conn.execute("DELETE FROM fatores_harmonizacao WHERE satelite_origem = 'Aqua' AND satelite_destino = 'SNPP'")
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO fatores_harmonizacao (regiao_id, satelite_origem, satelite_destino, mes, periodo, "
                "ano_calibracao, fator, n_focos_origem, fusao_com) VALUES (%s, 'Aqua', 'SNPP', %s, %s, %s, %s, %s, %s)",
                [(ids[r.regiao], int(r.mes), r.periodo, int(r.ano), float(r.fator), int(r.n_focos_origem), r.fusao_com)
                 for r in f.itertuples()])
    return len(f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--minimo", type=int, default=30)
    ap.add_argument("--erro", choices=["simples", "ponderado"], default="ponderado")
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()

    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    diario = contagens_do_csv(a.csv) if a.csv else contagens_do_banco()
    m = mensal(diario)
    fat = fatores_por_ano(m, a.minimo)
    fat.to_csv(saida / "fatores_todos_os_anos.csv", index=False)

    rel = [f"Calibração Aqua -> S-NPP | mínimo de focos = {a.minimo} | medida de erro da decisão = {a.erro}",
           f"Condições com fator: {fat['fator'].notna().sum()} de {len(fat)} | com fusão: {fat['fusao_com'].notna().sum()}"]
    rel += [f"  fusão '{k}': {v}" for k, v in fat["fusao_com"].value_counts().items()]

    anos_presentes = sorted(m["ano"].unique())
    if len(anos_presentes) < 2:
        rel.append(f"Só há o ano {anos_presentes}: sem validação nem decisão dos anos (precisa de 2012 a 2024).")
        anos = anos_presentes
    else:
        v = validar(m, fat)
        v.to_csv(saida / "validacao_meses.csv", index=False)
        erros = erros_por_ano(v)
        erros.to_csv(saida / "validacao_anos.csv", index=False)
        anos, antes, depois, razao = decidir(erros, f"erro_{a.erro}")
        rel.append(f"\nErro por ano ({REGIAO_DA_DECISAO}):")
        rel.append(erros[erros["regiao"] == REGIAO_DA_DECISAO].round(3).to_string(index=False))
        for medida in ("simples", "ponderado"):
            _, b, d, r = decidir(erros, f"erro_{medida}")
            rel.append(f"  {medida}: 2012-2021 = {b:.3f} | 2022-2024 = {d:.3f} | razão = {r:.2f}")
        rel.append(f"\nDecisão ({a.erro}, limite {LIMITE_CRITERIO}x): razão {razao:.2f} -> anos {anos[0]} a {anos[-1]} "
                   f"({len(anos)} cenários)")
        cob = erros.groupby("regiao")["cobertura_faixa"].mean().round(2)
        rel.append(f"Cobertura da faixa P{FAIXA[0]} a P{FAIXA[1]} (média dos anos; esperado ~0,78 com os 12 cenários "
                   f"da validação e ~0,79 com os 13 da série):\n" + cob.to_string())

    if a.gravar:
        if a.csv:
            sys.exit("--gravar só funciona lendo do banco")
        n = gravar(fat, anos)
        rel.append(f"\nGravados {n} fatores em fatores_harmonizacao (Aqua -> SNPP), anos {anos[0]} a {anos[-1]}.")

    texto = "\n".join(rel)
    (saida / "relatorio.txt").write_text(texto, encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()

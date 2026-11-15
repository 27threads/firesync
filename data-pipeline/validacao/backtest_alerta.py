"""Backtest do nível de alerta (solução A + B do docs/validacao-alerta.md, RFC 0001). Só LÊ o banco.

Para cada domingo t de 2013 a 2024, em cada unidade (célula H3 res 4 e bioma inteiro):
  - nível (0 Normal, 1 Atenção, 2 Crítico) pela regra do config/alert_rules.json: os 7 dias t-6..t contra o
    normal de ±15 dias da mesma data nos OUTROS anos (deixa o próprio ano de fora, como a API);
  - gabarito "muito fogo": os 14 dias t+1..t+14 acima do P90 do normal de 14 dias e com pelo menos 10 detecções.
    O gabarito começa no dia seguinte ao último dia que o nível usa: nenhum dia entra nas duas janelas.
Mede cada regra de uma grade e compara com a regra ingênua (persistência) na MESMA frequência de alerta.

Uso (dentro de data-pipeline/, com DATABASE_URL):
    python validacao/backtest_alerta.py --saida relatorios/alerta

Saídas na pasta --saida:
    backtest.csv    uma linha por regra (unidades res 4), mais a sensibilidade do gabarito na regra atual
    por_bioma.csv   uma linha por regra e bioma
    eventos.csv     nível semana a semana em cada evento conhecido e a antecedência (solução B)
    relatorio.txt   resumo e regras que passam na regra de decisão
"""
import argparse
from calendar import monthrange
import io
import itertools
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

PASTA = Path(__file__).resolve().parent.parent  # data-pipeline/
INICIO, FIM = date(2012, 2, 1), date(2024, 12, 31)  # S-NPP no agregados_diarios; 2025 fica fora (deriva do Aqua)
PRIMEIRO_DOMINGO, ULTIMO_DOMINGO = date(2013, 1, 6), date(2024, 12, 15)  # gabarito do último vai até 2024-12-29
JANELA_GABARITO = 14

# grade para a frente B escolher a v1 (docs/validacao-alerta.md)
RAZOES = (1.5, 2.0, 2.5, 3.0)
TENDENCIAS = (True, False)
ATENCOES = (75, 90)
PISOS_CONTINUOS = (False, True)  # piso só na mediana zero ou contínuo (issue #59)
GABARITO = (90, 10)  # percentil do normal de 14 dias e mínimo de detecções
SENSIBILIDADE = ((80, 10), (95, 10), (90, 5), (90, 20))
ANOS_COM_GANHO_MIN = 7  # regra de decisão: ganho positivo no total e em pelo menos 7 dos 12 anos
SORTEIOS, SEMENTE = 2000, 2026  # bootstrap por blocos de ano (intervalo de 95% do ganho)
SEMANAS_ANTES_DO_EVENTO = 8

# célula-mãe res 4 de uma res 6: resolução (bits 52-55) = 4 e dígitos 5 e 6 (bits 27-32) = 7 (sem célula)
MASCARA_RES, RES4, DIGITOS_5_6 = 15 << 52, 4 << 52, 63 << 27

PERIODO = f"data BETWEEN '{INICIO}' AND '{FIM}'"
SQL_RES4 = f"""COPY (
SELECT ((h3 & ~{MASCARA_RES}::bigint) | {RES4 | DIGITOS_5_6}::bigint) AS unidade, data, sum(focos_brutos) AS n
FROM agregados_diarios WHERE {PERIODO} GROUP BY 1, 2) TO STDOUT WITH CSV HEADER"""
SQL_BIOMAS = f"""COPY (
SELECT r.nome AS unidade, a.data, sum(a.focos_brutos) AS n
FROM agregados_diarios a JOIN regioes r ON r.id = a.regiao_id WHERE a.{PERIODO} GROUP BY 1, 2) TO STDOUT WITH CSV HEADER"""


def matriz(df):
    """(unidade, data, n) -> (unidades, matriz unidade x dia de INICIO a FIM). Dia sem linha = 0 detecções."""
    unidades, u = np.unique(df["unidade"].to_numpy(), return_inverse=True)
    d = (pd.to_datetime(df["data"]) - pd.Timestamp(INICIO)).dt.days.to_numpy()
    m = np.zeros((len(unidades), (FIM - INICIO).days + 1), np.float32)
    np.add.at(m, (u, d), df["n"].to_numpy(np.float32))
    return unidades, m


def somas_moveis(m, k):
    """Soma dos k dias que terminam em cada dia. NaN onde a janela sai do começo da série."""
    c = np.cumsum(m, axis=1, dtype=np.float64)
    s = np.full(m.shape, np.nan, np.float32)
    s[:, k - 1:] = c[:, k - 1:] - np.concatenate([np.zeros((m.shape[0], 1)), c[:, :-k]], axis=1)
    return s


def indices_normal(t, raio, anos, ano_excluido):
    """Dias (índices) do normal de t: a mesma data deslocada de -raio a +raio em cada ano, menos o excluído."""
    ultimo = (FIM - INICIO).days
    idx = []
    for ano in anos:
        if ano == ano_excluido:
            continue
        centro = t.replace(year=ano, day=min(t.day, monthrange(ano, t.month)[1]))
        idx += [i for i in range((centro - INICIO).days - raio, (centro - INICIO).days + raio + 1) if 0 <= i <= ultimo]
    return np.array(idx)


def indices_gabarito(t, raio, anos):
    """Normal do gabarito (14 dias até t+14). Exclui o ano de t+14: no fim de dezembro ele é o ano seguinte."""
    fim = t + timedelta(JANELA_GABARITO)
    return indices_normal(fim, raio, anos, fim.year)


def avaliar(m, regra):
    """Somas e normal de cada domingo e unidade -> (semanas, dict de arrays semana x unidade)."""
    base, crit = regra["baseline"], regra["levels"]["critical"]
    raio, kt = base["neighbor_days"], crit["trend_days"]
    anos = range(base["reference_years_from"], FIM.year + 1)
    s7, s3, s14 = (somas_moveis(m, k) for k in (base["window_days"], kt, JANELA_GABARITO))
    semanas = [PRIMEIRO_DOMINGO + timedelta(weeks=w) for w in range((ULTIMO_DOMINGO - PRIMEIRO_DOMINGO).days // 7 + 1)]
    a = {c: np.empty((len(semanas), m.shape[0]), np.float32)
         for c in ("s7", "med7", "p75", "p90", "sobe", "score", "s14", "g80", "g90", "g95")}
    for w, t in enumerate(semanas):
        i, j = (t - INICIO).days, (t - INICIO).days + JANELA_GABARITO
        ref7 = s7[:, [k for k in indices_normal(t, raio, anos, t.year) if not np.isnan(s7[0, k])]]
        ref14 = s14[:, [k for k in indices_gabarito(t, raio, anos) if not np.isnan(s14[0, k])]]
        a["s7"][w] = s7[:, i]
        a["med7"][w], a["p75"][w], a["p90"][w] = np.percentile(ref7, [50, 75, 90], axis=1)
        a["sobe"][w] = s3[:, i] > s3[:, i - kt]
        a["score"][w] = (s7[:, i] + 1) / (a["p90"][w] + 1)  # ingênua: quanto a semana passa do P90
        a["s14"][w] = s14[:, j]
        a["g80"][w], a["g90"][w], a["g95"][w] = np.percentile(ref14, [80, 90, 95], axis=1)
    a["sobe"] = a["sobe"].astype(bool)
    return semanas, a


def nivel(a, razao, tendencia, atencao, piso, piso_continuo=False):
    """0 Normal, 1 Atenção, 2 Crítico (regra do alert_rules.json com os parâmetros da grade).

    Piso só na mediana zero: Crítico com s7 >= piso onde o normal é zero e s7 >= razao x mediana no resto.
    Piso contínuo (issue #59): s7 >= max(razao x mediana, piso) sempre, sem o degrau da mediana baixa.
    """
    if piso_continuo:
        critico = a["s7"] >= np.maximum(razao * a["med7"], piso)
    else:
        critico = np.where(a["med7"] > 0, a["s7"] >= razao * a["med7"], a["s7"] >= piso)
    if tendencia:
        critico &= a["sobe"]
    return np.where(critico, 2, np.where(a["s7"] > a[f"p{atencao}"], 1, 0))


def nivel_da_regra(a, regra):
    """Nível pela regra do alert_rules.json, com o piso contínuo de min_detections: a mesma regra de nível do
    `recent` da API. O normal difere: aqui usa os outros anos, inclusive os posteriores (limite declarado)."""
    crit = regra["levels"]["critical"]
    return nivel(a, crit["min_ratio_to_median"], crit["requires_rising_trend"],
                 regra["levels"]["attention"]["above_percentile"], crit["min_detections"], piso_continuo=True)


def gabarito(a, pct, minimo):
    return (a["s14"] > a[f"g{pct}"]) & (a["s14"] >= minimo)


def taxa(x, cond):
    return float(x[cond].mean()) if cond.any() else np.nan


def alerta_mesma_frequencia(score, f):
    """A ingênua com o mesmo número de alertas: as k semanas de maior score."""
    k = round(f * score.size)
    alerta = np.zeros(score.size, bool)
    if k:
        alerta[np.argpartition(-score.ravel(), k - 1)[:k]] = True
    return alerta.reshape(score.shape)


def ganho_bootstrap(crit, ingenua, gab, anos, sorteios=SORTEIOS, semente=SEMENTE):
    """Intervalo de 95% do ganho sorteando ANOS inteiros com reposição (bootstrap por blocos de ano).

    Semanas seguidas têm gabaritos que se sobrepõem, então a semana não é independente; o ano é. Os alertas da
    ingênua ficam os da amostra completa (não são recalculados a cada sorteio).
    """
    ys = np.unique(anos)
    por_ano = np.array([[(crit & gab)[anos == y].sum(), crit[anos == y].sum(),
                         (ingenua & gab)[anos == y].sum(), ingenua[anos == y].sum()] for y in ys], float)
    soma = por_ano[np.random.default_rng(semente).integers(0, len(ys), (sorteios, len(ys)))].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        ganhos = soma[:, 0] / soma[:, 1] - soma[:, 2] / soma[:, 3]
    baixo, alto = np.nanpercentile(ganhos, [2.5, 97.5]) if np.isfinite(ganhos).any() else (np.nan, np.nan)
    return float(baixo), float(alto)


def medidas(niv, gab, score, anos):
    """Medidas de uma regra (arrays semana x unidade). O ganho é sobre a ingênua na mesma frequência."""
    crit = niv == 2
    ingenua = alerta_mesma_frequencia(score, crit.mean())
    acerto, acerto_ing = taxa(gab, crit), taxa(gab, ingenua)
    ganho_ano = [taxa(gab[anos == y], crit[anos == y]) - taxa(gab[anos == y], ingenua[anos == y])
                 for y in np.unique(anos)]
    meses = niv.shape[0] * 7 / 30.4375
    ic_baixo, ic_alto = ganho_bootstrap(crit, ingenua, gab, anos)
    return {"freq_normal": float((niv == 0).mean()), "freq_atencao": float((niv == 1).mean()),
            "freq_critico": float(crit.mean()), "prevalencia_gabarito": float(gab.mean()), "acerto": acerto, "cobertura": taxa(niv >= 1, gab),
            "cobertura_critico": taxa(crit, gab), "alarme_falso": 1 - acerto,
            "trocas_mes": float((niv[1:] != niv[:-1]).sum() / (niv.shape[1] * meses)),
            "acerto_ingenua": acerto_ing, "ganho": acerto - acerto_ing,
            "anos_com_ganho_positivo": int(np.sum(np.array(ganho_ano) > 0)),
            "ganho_ic95_baixo": ic_baixo, "ganho_ic95_alto": ic_alto}


def regras(regra):
    """A grade, com a regra atual do alert_rules.json marcada."""
    crit = regra["levels"]["critical"]
    atual = (crit["min_ratio_to_median"], crit["requires_rising_trend"], regra["levels"]["attention"]["above_percentile"])
    for r, t, at, pc in itertools.product(RAZOES, TENDENCIAS, ATENCOES, PISOS_CONTINUOS):
        yield {"regra": f"razao{r}_tend{int(t)}_atencao_p{at}" + ("_piso_continuo" if pc else ""), "razao": r,
               "tendencia": t, "atencao": at, "piso_continuo": pc, "regra_atual": (r, t, at, pc) == (*atual, True),
               "variante_da_atual": (r, t, at) == atual}


def tabela(semanas, a, regra, colunas=None):
    """Uma linha por regra (e por coluna/unidade, se `colunas` vier), mais a ingênua no P90 como regra."""
    anos = np.array([t.year for t in semanas])[:, None] * np.ones((1, a["s7"].shape[1]), int)
    grupos = {"todas": slice(None)} if colunas is None else {c: [j] for j, c in enumerate(colunas)}
    piso = regra["levels"]["critical"]["min_detections"]  # o mesmo piso da API e do eventos.csv
    linhas = []
    for nome, sel in grupos.items():
        sub = {k: v[:, sel] for k, v in a.items()}
        gab = gabarito(sub, *GABARITO)
        for r in regras(regra):
            niv = nivel(sub, r["razao"], r["tendencia"], r["atencao"], piso, r["piso_continuo"])
            linhas.append({"unidade": nome, **r, "p_gabarito": GABARITO[0], "minimo": GABARITO[1],
                           **medidas(niv, gab, sub["score"], anos[:, sel])})
            if r["variante_da_atual"] and colunas is None:  # sensibilidade nas duas versões do piso
                for p, mn in SENSIBILIDADE:
                    linhas.append({"unidade": nome, **r, "p_gabarito": p, "minimo": mn,
                                   **medidas(niv, gabarito(sub, p, mn), sub["score"], anos[:, sel])})
        ing = np.where(sub["s7"] > sub["p90"], 2, 0)
        linhas.append({"unidade": nome, "regra": "ingenua_p90", "regra_atual": False, "p_gabarito": GABARITO[0],
                       "minimo": GABARITO[1], **medidas(ing, gab, sub["score"], anos[:, sel])})
    return pd.DataFrame(linhas)


def ler_eventos(caminho):
    """Eventos conhecidos (solução B). Nenhuma linha entra sem fonte oficial."""
    ev = pd.read_csv(caminho, parse_dates=["inicio", "fim"])
    sem = ev[ev["fonte_url"].fillna("").str.strip() == ""]
    if len(sem):
        raise ValueError(f"evento sem fonte oficial: {', '.join(sem['nome'])}")
    return ev


def eventos(ev, unidades, semanas, a, niv):
    """Nível semana a semana em cada evento (bioma inteiro) e a antecedência do primeiro alerta antes do início.

    antecedencia_no_limite: o alerta já estava ligado na 1ª semana da janela; a antecedência real pode ser maior.
    alerta_continuo: o nível ficou em Atenção ou Crítico de o primeiro alerta até o último domingo antes do início.
    antecedencia_continua_dias: dias desde o começo do trecho sem volta a Normal que chega ao último domingo antes do
    início (vazio se esse domingo foi Normal); antecedencia_critico_continuo_dias: o primeiro Crítico desse trecho.
    Frase da tela: "virou Crítico X dias antes e ficou em Atenção ou Crítico até o início".
    continua_no_limite: o trecho começa na 1ª semana da janela; a antecedência real pode ser maior.
    """
    linhas = []
    for e in ev.itertuples():
        if e.regiao not in list(unidades):
            raise ValueError(f"evento {e.nome}: região {e.regiao!r} não está em `regioes`")
        j = list(unidades).index(e.regiao)
        ini, fim = e.inicio.date(), e.fim.date()
        sel = [(w, t) for w, t in enumerate(semanas) if ini - timedelta(weeks=SEMANAS_ANTES_DO_EVENTO) <= t <= fim]
        antes = [(t, niv[w, j] >= 1) for w, t in sel if t < ini]
        alertas = [t for t, ligado in antes if ligado]
        dias = (ini - min(alertas)).days if alertas else None  # vazio = nenhum alerta nas semanas antes
        no_limite = bool(antes) and antes[0][1]
        continuo = bool(alertas) and all(ligado for t, ligado in antes if t >= min(alertas))
        trecho = []  # domingos seguidos em Atenção ou Crítico até o último antes do início
        for w, t in sel:
            if t < ini:
                trecho = trecho + [(w, t)] if niv[w, j] >= 1 else []
        criticos = [t for w, t in trecho if niv[w, j] == 2]
        linhas += [{"evento": e.nome, "regiao": e.regiao, "semana": t, "nivel": int(niv[w, j]),
                    "detections": float(a["s7"][w, j]), "typical_median": float(a["med7"][w, j]),
                    "antecedencia_dias": dias, "antecedencia_semanas": None if dias is None else dias // 7,
                    "antecedencia_no_limite": no_limite, "alerta_continuo": continuo,
                    "antecedencia_continua_dias": (ini - trecho[0][1]).days if trecho else None,
                    "antecedencia_critico_continuo_dias": (ini - criticos[0]).days if criticos else None,
                    "continua_no_limite": bool(trecho) and trecho[0][1] == antes[0][0]}
                   for w, t in sel]
    return pd.DataFrame(linhas)


def situacao(bt):
    """Linhas do gabarito principal (sem a ingênua) com a coluna `situacao` no critério completo da regra de decisão:
    ganho > 0 no total e em >= 7 dos 12 anos no gabarito principal e ganho > 0 em cada variação de SENSIBILIDADE.
    Regra que passa no principal mas não tem as quatro variações calculadas fica como "sensibilidade não avaliada"."""
    principal = (bt["p_gabarito"] == GABARITO[0]) & (bt["minimo"] == GABARITO[1])
    linhas = bt[principal & (bt["regra"] != "ingenua_p90")].copy()
    variacoes = bt[~principal].set_index(["regra", "p_gabarito", "minimo"])["ganho"]

    def uma(r):
        if not (r["ganho"] > 0 and r["anos_com_ganho_positivo"] >= ANOS_COM_GANHO_MIN):
            return "reprovada"
        ganhos = [variacoes.get((r["regra"], p, mn)) for p, mn in SENSIBILIDADE]
        if any(g is not None and not g > 0 for g in ganhos):
            return "reprovada"
        return "sensibilidade não avaliada" if None in ganhos else "aprovada"

    linhas["situacao"] = linhas.apply(uma, axis=1)
    return linhas


def relatorio(bt):
    sit = situacao(bt)
    atual = sit[sit["regra_atual"]]
    aprovadas = sit[sit["situacao"] == "aprovada"].sort_values("ganho", ascending=False)
    sem_sens = sit[sit["situacao"] == "sensibilidade não avaliada"].sort_values("ganho", ascending=False)
    cols = ["regra", "freq_critico", "acerto", "acerto_ingenua", "ganho", "ganho_ic95_baixo", "ganho_ic95_alto",
            "anos_com_ganho_positivo", "cobertura_critico"]
    variacoes = ", ".join(f"P{p} e mínimo {mn}" for p, mn in SENSIBILIDADE)
    return "\n".join([
        f"Backtest do alerta, {PRIMEIRO_DOMINGO} a {ULTIMO_DOMINGO} (domingos), unidades H3 res 4.",
        f"Gabarito: {JANELA_GABARITO} dias seguintes acima do P{GABARITO[0]} do normal e >= {GABARITO[1]} detecções.",
        "Ganho = acerto do Crítico - acerto da ingênua (persistência) com a MESMA frequência de alerta.",
        f"Intervalo de 95% do ganho: bootstrap sorteando anos inteiros ({SORTEIOS} sorteios, semente {SEMENTE}).",
        "", "Regra atual do alert_rules.json:", atual[cols + ["situacao"]].to_string(index=False), "",
        f"Regras aprovadas: ganho > 0 no total e em >= {ANOS_COM_GANHO_MIN} dos 12 anos e ganho > 0 no total de cada "
        f"variação do gabarito ({variacoes}):",
        aprovadas[cols].to_string(index=False) if len(aprovadas)
        else "NENHUMA. A tela não mostra acerto (docs/validacao-alerta.md, \"Regra de decisão\").",
        "", "Passam no gabarito principal, mas a sensibilidade não foi calculada (NÃO aprovadas):",
        sem_sens[cols].to_string(index=False) if len(sem_sens) else "nenhuma"])


def ler(conn, sql):
    with conn.cursor().copy(sql) as cp:
        return pd.read_csv(io.BytesIO(b"".join(bytes(b) for b in cp)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saida", type=Path, default=PASTA / "relatorios" / "alerta")
    ap.add_argument("--regras", type=Path, default=PASTA.parent / "config" / "alert_rules.json")
    ap.add_argument("--eventos", type=Path, default=PASTA / "referencia" / "eventos_conhecidos.csv")
    args = ap.parse_args()
    regra = json.loads(args.regras.read_text(encoding="utf-8"))
    sys.path.insert(0, str(PASTA))
    from pipeline import db
    conn = db()
    args.saida.mkdir(parents=True, exist_ok=True)

    _, m = matriz(ler(conn, SQL_RES4))
    semanas, a = avaliar(m, regra)
    bt = tabela(semanas, a, regra)
    bt.to_csv(args.saida / "backtest.csv", index=False)

    biomas, mb = matriz(ler(conn, SQL_BIOMAS))
    semanas, ab = avaliar(mb, regra)
    tabela(semanas, ab, regra, colunas=biomas).to_csv(args.saida / "por_bioma.csv", index=False)
    if args.eventos.exists():
        eventos(ler_eventos(args.eventos), biomas, semanas, ab, nivel_da_regra(ab, regra)).to_csv(args.saida / "eventos.csv", index=False)

    texto = relatorio(bt)
    (args.saida / "relatorio.txt").write_text(texto + "\n", encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()

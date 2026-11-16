"""Exploratório: melhorar o acerto do modelo 'onde vai ter fogo' (>= 10 detecções na célula res 4 nos 14 dias seguintes).

PROTOCOLO FIXADO ANTES DE RODAR (15/11/2026):
  - Comparação: modelo BASE (12 variáveis, o do primeiro teste) contra o modelo MELHORADO (as mesmas + 10 novas).
  - Métrica: acerto (precisão) das 10% de células mais arriscadas de cada semana, na avaliação SEM o Pantanal.
  - As variáveis novas ficam se: em 2017-2020 (desenvolvimento) melhoram em >= 3 de 4 anos e em média >= 0,5 ponto;
    e em 2021-2024 (confirmação, não usada na escolha) melhoram em >= 3 de 4 anos e em média >= 0,5 ponto.
  - Treino sempre só com semanas cujo gabarito termina antes do ano de teste (validação em avanço).
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import h3
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, r"C:\Users\user\AppData\Local\Temp\firesync_clone\data-pipeline")
from validacao import backtest_alerta as bt, modelo_risco as mr

base = Path(r"C:\Users\user\AppData\Local\Temp\claude\735018456ef07932\19212868-59be-4d83-8e39-80c0980fbc11\scratchpad")
saida = base / "risco" / "onde4"
saida.mkdir(parents=True, exist_ok=True)
MINIMO, ANOS, DEV, HOLD = 10, list(range(2017, 2025)), [2017, 2018, 2019, 2020], [2021, 2022, 2023, 2024]
LINHAS_TREINO = 1_200_000
PANTANAL = 6

regra = json.loads(Path(r"C:\Users\user\AppData\Local\Temp\firesync_clone\config\alert_rules.json").read_text(encoding="utf-8"))
unidades, m_n, m_frp = mr.matrizes(pd.read_parquet(base / "risco" / "serie.parquet"))
semanas, a = bt.avaliar(m_n, regra)
alvo = a["s14"] >= MINIMO
W, U = alvo.shape
dias = np.array([(t - bt.INICIO).days for t in semanas])
viz1 = mr.vizinhos(unidades)
fogo = mr.pistas_fogo(m_n, m_frp, semanas, viz1)          # s7 s14 s30 tendencia frp7 viz7 ano_anterior normal_passado
del a


def anel(k):
    pos = {int(u): j for j, u in enumerate(unidades)}
    L, C = [], []
    for u, j in pos.items():
        for v in h3.grid_ring(h3.int_to_str(u), k):
            c = pos.get(h3.str_to_int(v))
            if c is not None:
                L.append(j)
                C.append(c)
    return np.array(L, int), np.array(C, int)


def soma_viz(pares, s_dias):                               # s_dias: unidades x semanas -> semanas x unidades
    out = np.zeros_like(s_dias)
    np.add.at(out, pares[0], s_dias[pares[1]])
    return out.T


s30d = bt.somas_moveis(m_n, 30)[:, dias]
s14d = bt.somas_moveis(m_n, 14)
ultimo = np.maximum.accumulate(np.where(m_n > 0, np.arange(m_n.shape[1], dtype=np.int32)[None, :], -1).astype(np.int32), axis=1)
novas = {
    "s90": bt.somas_moveis(m_n, 90)[:, dias].T,
    "dias_fogo30": bt.somas_moveis((m_n > 0).astype(np.float32), 30)[:, dias].T,
    "desde_ultimo": np.where(ultimo[:, dias] >= 0, dias[None, :] - ultimo[:, dias], 400).T.astype(np.float32),
    "frp30": bt.somas_moveis(m_frp, 30)[:, dias].T,
    "viz30": soma_viz(viz1, np.nan_to_num(s30d)),
    "viz2_30": soma_viz(anel(2), np.nan_to_num(s30d)),
}
freq = np.full((W, U), np.nan, np.float32)
mx = np.full((W, U), np.nan, np.float32)
a2 = np.full((W, U), np.nan, np.float32)
for w, i in enumerate(dias):
    js = [j for j in (i + 14 - int(round(365.25 * k)) for k in range(1, 14)) if j >= 13]
    if js:
        v = s14d[:, js]
        freq[w], mx[w] = (v >= MINIMO).mean(axis=1), v.max(axis=1)
        if len(js) >= 2:
            a2[w] = v[:, 1]
novas.update(freq_passada=freq, max_passada=mx, ano_anterior_2=a2,
             razao_7_30=(fogo["s7"] / (fogo["s30"] * 7 / 30 + 1)).astype(np.float32))
del m_n, m_frp, s14d, ultimo, s30d

lat, lon = mr.posicao_das_unidades(unidades)
bioma = mr.bioma_das_unidades(unidades, gpd.read_file(base / "ibge" / "Biomas_250mil.zip"))
vetores = {"semana": np.repeat(np.array([t.isocalendar()[1] for t in semanas], np.float32)[:, None], U, 1),
           "lat": np.tile(lat, (W, 1)), "lon": np.tile(lon, (W, 1)), "bioma": np.tile(bioma, (W, 1))}
chaves_base = ["s7", "s14", "s30", "tendencia", "frp7", "viz7", "ano_anterior", "normal_passado"]
pistas = {**{k: fogo[k] for k in chaves_base}, **vetores}                    # 12 variáveis do modelo base
n_base = len(pistas)
pistas.update(novas)                                                          # + 10 novas
X = mr.empilhar(pistas, (W, U))
cat = [list(pistas).index("bioma")]
print(f"variáveis: base {n_base}, melhorado {X.shape[2]} | semanas {W} | células {U}", flush=True)

ok = np.nan_to_num(bioma, nan=0) != PANTANAL                                  # avaliação sem o Pantanal
bioma_ok = np.nan_to_num(bioma[ok], nan=0)
pico = np.array([8 <= t.month <= 10 for t in semanas])
rng = np.random.default_rng(mr.SEMENTE)


def topo(score, fracao):
    k = max(1, int(round(fracao * score.shape[1])))
    t = np.zeros(score.shape, bool)
    np.put_along_axis(t, np.argpartition(-score, k - 1, axis=1)[:, :k], True, axis=1)
    return t


def medir(score, y, pk, ano, metodo):
    linha = {"ano": ano, "metodo": metodo, "base": float(y.mean()), "auc": float(roc_auc_score(y.ravel(), score.ravel()))}
    for f in (0.05, 0.10, 0.20):
        t = topo(score, f)
        linha[f"acerto_top{int(f * 100)}"] = float(y[t].mean())
        linha[f"cobre_top{int(f * 100)}"] = float((y & t).sum() / y.sum())
    t = topo(score, 0.10)
    linha["top10_pico"] = float(y[pk][t[pk]].mean()) if pk.any() else np.nan
    linha["top10_fora_pico"] = float(y[~pk][t[~pk]].mean()) if (~pk).any() else np.nan
    return linha


def prever(modelo, Xte, cols):
    out = np.empty(Xte.shape[0], np.float32)
    for ini in range(0, Xte.shape[0], 400_000):
        out[ini:ini + 400_000] = modelo.predict_proba(Xte[ini:ini + 400_000][:, cols])[:, 1]
    return out


linhas, linhas_bioma, calib = [], [], []
for ano in ANOS:
    treino, teste = mr.cortes(semanas, ano)
    ws = np.flatnonzero(treino)[rng.integers(0, treino.sum(), LINHAS_TREINO)]
    us = rng.integers(0, U, LINHAS_TREINO)
    Xtr, ytr = X[ws, us], alvo[ws, us]
    y = alvo[teste][:, ok]
    pk = pico[teste]
    Xte = X[teste][:, ok]
    forma = y.shape
    Xte = Xte.reshape(-1, X.shape[2])
    scores = {}
    fora = {list(pistas).index("frp7"), list(pistas).index("bioma")}
    for nome, cols in (("base12", list(range(n_base))), ("final10", [i for i in range(n_base) if i not in fora])):
        categ = [cols.index(cat[0])] if cat[0] in cols else []
        modelo = mr.ajustar(Xtr[:, cols], ytr, categ, mr.SEMENTE)
        scores[nome] = prever(modelo, Xte, cols).reshape(forma)
        del modelo
    f30 = pd.DataFrame(fogo["s30"][teste][:, ok]).rank(axis=1).to_numpy()
    scores["regua_30d_mais_epoca"] = f30 + pd.DataFrame(np.nan_to_num(fogo["normal_passado"][teste][:, ok])).rank(axis=1).to_numpy()
    scores["regua_freq_passada"] = f30 + pd.DataFrame(np.nan_to_num(freq[teste][:, ok])).rank(axis=1).to_numpy()
    for nome, s in scores.items():
        linhas.append(medir(s, y, pk, ano, nome))
        for b in (1, 2, 3, 4, 5):
            c = bioma_ok == b
            if c.sum() >= 20:
                t = topo(s[:, c], 0.10)
                linhas_bioma.append({"ano": ano, "metodo": nome, "bioma": b, "acerto_top10": float(y[:, c][t].mean())})
    if ano in HOLD:
        for s_nome in ("final10",):
            calib.append(pd.DataFrame({"p": scores[s_nome].ravel(), "y": y.ravel(),
                                       "pico": np.repeat(pk, forma[1])}))
    print(f"{ano}: pronto", flush=True)
    pd.DataFrame(linhas).to_csv(saida / "medidas.csv", index=False)
    pd.DataFrame(linhas_bioma).to_csv(saida / "por_bioma.csv", index=False)

m = pd.DataFrame(linhas)
print("\nMEDIA 2017-2024 (sem Pantanal)")
print((m.groupby("metodo")[["auc", "acerto_top5", "cobre_top5", "acerto_top10", "cobre_top10", "acerto_top20", "top10_pico", "top10_fora_pico"]].mean() * 100).round(1).to_string())
p = m.pivot(index="ano", columns="metodo", values="acerto_top10") * 100
print("\nacerto no top 10%, por ano:\n", p.round(1).to_string())
for nome, anos in (("DESENVOLVIMENTO 2017-2020", DEV), ("CONFIRMACAO 2021-2024", HOLD)):
    d = (p["final10"] - p["base12"]).loc[anos]
    print(f"{nome}: melhorado - base: melhor em {int((d > 0).sum())}/4 anos, media {d.mean():+.2f} pt")
d = (p["final10"] - p["regua_30d_mais_epoca"])
print(f"melhorado - regua simples (8 anos): melhor em {int((d > 0).sum())}/8, media {d.mean():+.2f} pt")
if calib:
    c = pd.concat(calib)
    c["faixa"] = pd.cut(c["p"], [0, .05, .1, .2, .3, .4, .5, .6, .7, .8, 1.0], include_lowest=True)
    tab = c.groupby(["pico", "faixa"], observed=True).agg(prevista=("p", "mean"), observada=("y", "mean"), n=("y", "size")).round(3)
    tab.to_csv(saida / "calibracao_2021_2024.csv")
    print("\nCALIBRACAO 2021-2024 (pico = ago-out):\n", tab.to_string())
print("\nPOR BIOMA (acerto top 10% dentro do bioma, media dos anos):")
print((pd.DataFrame(linhas_bioma).groupby(["bioma", "metodo"])["acerto_top10"].mean().unstack() * 100).round(1).to_string())

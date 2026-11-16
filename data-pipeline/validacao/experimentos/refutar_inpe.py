"""Tentativa de REFUTAR 'o nosso modelo ordena melhor que o INPE'. Cada bloco testa uma hipótese de viés.

H1 (agregação): o INPE perde por termos usado a MÉDIA do índice sobre a célula; com o máximo ou o P90 ele ganharia?
H2 (persistência): o INPE ganha onde o fogo NÃO é persistente (células quietas nos últimos 30 dias, ou seja, início de fogo)?
H3 (bioma): o INPE ganha em algum bioma?
H4 (horizonte): o INPE ganha em horizontes curtos (3 e 7 dias), para os quais o índice foi pensado?
Nada é gravado fora da pasta de saída.
"""
import glob
import sys
from datetime import date, timedelta
from pathlib import Path

import geopandas as gpd
import h3
import h5py
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, r"C:\Users\user\AppData\Local\Temp\firesync_clone\data-pipeline")
import risco_celulas as rc  # noqa: E402
from validacao import backtest_alerta as bt, modelo_risco as mr  # noqa: E402

base = Path(r"C:\Users\user\AppData\Local\Temp\claude\735018456ef07932\19212868-59be-4d83-8e39-80c0980fbc11\scratchpad")
df = pd.read_parquet(base / "risco" / "serie.parquet")
domingos = [date(2024, 1, 7) + timedelta(weeks=k) for k in range(50)]
serie = rc.preparar_serie(df, date(2024, 12, 31))
unidades, m = serie["unidades"], serie["matriz"]
idx = np.array([(t - bt.INICIO).days for t in domingos])
alvo = {k: (bt.somas_moveis(m, k)[:, idx + k].T) for k in (3, 7, 14)}           # soma dos k dias seguintes (semana x célula)
modelo = rc.treinar(df, date(2023, 12, 31))
pist = rc.montar_pistas(serie, domingos)
X = mr.empilhar(pist, alvo[14].shape)
nosso = modelo["modelo"].predict_proba(X.reshape(-1, X.shape[2]))[:, 1].reshape(alvo[14].shape)
s30 = pist["s30"]

filhos = [h3.cell_to_children(h3.int_to_str(int(u)), 6) for u in unidades]
pts = np.array([h3.cell_to_latlng(f) for fs in filhos for f in fs])
n_filhos = len(filhos[0])
assert all(len(f) == n_filhos for f in filhos)
agreg = {k: np.full(alvo[14].shape, np.nan, np.float32) for k in ("media", "max", "p90")}
arquivos = {date(int(f[-11:-7]), int(f[-7:-5]), int(f[-5:-3])): f for f in glob.glob(str(base / "inpe_risco_2024" / "*.nc"))}
for w, t in enumerate(domingos):
    with h5py.File(arquivos[t], "r") as h:
        lat, lon = h["lat"][:], h["lon"][:]
        i = np.clip(np.rint((pts[:, 0] - lat[0]) / (lat[1] - lat[0])).astype(int), 0, len(lat) - 1)
        k = np.clip(np.rint((pts[:, 1] - lon[0]) / (lon[1] - lon[0])).astype(int), 0, len(lon) - 1)
        grade = h["rf"][0]
        v = grade[i, k].astype(np.float32)
        del grade
    v[v < 0] = np.nan
    v = v.reshape(len(unidades), n_filhos)
    with np.errstate(all="ignore"):
        agreg["media"][w], agreg["max"][w], agreg["p90"][w] = np.nanmean(v, axis=1), np.nanmax(v, axis=1), np.nanpercentile(v, 90, axis=1)
np.savez_compressed(base / "inpe_comparacao" / "arrays_2024.npz", nosso=nosso, media=agreg["media"], max=agreg["max"], p90=agreg["p90"],
                    s30=s30, a3=alvo[3], a7=alvo[7], a14=alvo[14])

bioma = np.nan_to_num(mr.bioma_das_unidades(unidades, gpd.read_file(base / "ibge" / "Biomas_250mil.zip")), nan=0)
ok = (bioma != 6)[None, :] & np.isfinite(agreg["media"])


def topo(score, valido, fracao):
    t = np.zeros(score.shape, bool)
    for w in range(score.shape[0]):
        ix = np.flatnonzero(valido[w])
        if len(ix):
            t[w, ix[np.argsort(-score[w, ix])[: max(1, int(round(fracao * len(ix))))]]] = True
    return t


def medir(score, y, valido):
    if y[valido].all() or not y[valido].any():
        return np.nan, np.nan, int(valido.sum())
    s = np.where(valido, score, -np.inf)
    return roc_auc_score(y[valido], s[valido]), y[topo(s, valido, 0.10)].mean(), int(valido.sum())


y14 = alvo[14] >= 10
print("== H1: o INPE melhora com outra agregação da célula? (alvo: 10+ detecções em 14 dias; AUC | acerto no top 10%)")
a, p, n = medir(nosso, y14, ok)
print(f"  nosso modelo      AUC {a:.3f} | {p:.1%}")
for nome in ("media", "max", "p90"):
    a, p, n = medir(agreg[nome], y14, ok)
    print(f"  INPE ({nome:5s})     AUC {a:.3f} | {p:.1%}")

print("\n== H2: o INPE ganha onde o fogo não é persistente? (células pela contagem dos 30 dias anteriores)")
for rotulo, sel in (("quietas: 0 detecções em 30 dias", s30 == 0), ("poucas: 1 a 9", (s30 >= 1) & (s30 < 10)),
                    ("médias: 10 a 99", (s30 >= 10) & (s30 < 100)), ("fortes: 100 ou mais", s30 >= 100)):
    v = ok & sel
    an, pn, nn = medir(nosso, y14, v)
    ai, pi, _ = medir(agreg["media"], y14, v)
    print(f"  {rotulo:34s} n={nn:7d} fogo={y14[v].mean():5.1%} | nosso AUC {an:.3f} acerto {pn:.1%} | INPE AUC {ai:.3f} acerto {pi:.1%}")

print("\n== H3: o INPE ganha em algum bioma? (sem o Pantanal; ranking dentro do bioma)")
nomes = {1: "Amazônia", 2: "Caatinga", 3: "Cerrado", 4: "Mata Atlântica", 5: "Pampa"}
for b, nome in nomes.items():
    v = ok & (bioma == b)[None, :]
    an, pn, nn = medir(nosso, y14, v)
    ai, pi, _ = medir(agreg["media"], y14, v)
    print(f"  {nome:15s} n={nn:7d} fogo={y14[v].mean():5.1%} | nosso AUC {an:.3f} acerto {pn:.1%} | INPE AUC {ai:.3f} acerto {pi:.1%}")

print("\n== H4: o INPE ganha em horizontes curtos? (a mesma nota de cada um, alvos mais curtos)")
for rotulo, y in (("5+ detecções em 3 dias", alvo[3] >= 5), ("10+ detecções em 7 dias", alvo[7] >= 10), ("10+ detecções em 14 dias", y14)):
    an, pn, nn = medir(nosso, y, ok)
    ai, pi, _ = medir(agreg["media"], y, ok)
    print(f"  {rotulo:26s} fogo={y[ok].mean():5.1%} | nosso AUC {an:.3f} acerto {pn:.1%} | INPE AUC {ai:.3f} acerto {pi:.1%}")

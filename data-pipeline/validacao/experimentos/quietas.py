"""De onde vem o '69'? Contagens das celulas quietas na Amazonia (2021-2024), domingos, aviso = nota >= 50%.
Quieta = zero deteccoes nos 30 dias ate o domingo. Relevante = 10 ou mais deteccoes VIIRS nos 14 dias seguintes."""
import sys
from datetime import date, timedelta
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\user\AppData\Local\Temp\firesync_risco\data-pipeline")
import risco_celulas as rc  # noqa: E402
from validacao import backtest_alerta as bt, modelo_risco as mr  # noqa: E402

velha = Path(r"C:\Users\user\AppData\Local\Temp\claude\735018456ef07932\19212868-59be-4d83-8e39-80c0980fbc11\scratchpad")
novo = Path(r"C:\Users\user\AppData\Local\Temp\claude\7e0d63c41983d7ba\19212868-59be-4d83-8e39-80c0980fbc11\scratchpad")
d = pd.read_parquet(novo / "amazonia" / "amazonia_notas.parquet")
serie = rc.preparar_serie(pd.read_parquet(velha / "risco" / "serie.parquet"), bt.FIM)
unidades, m = serie["unidades"], serie["matriz"]
bioma = np.nan_to_num(mr.bioma_das_unidades(unidades, gpd.read_file(velha / "ibge" / "Biomas_250mil.zip")), nan=0)
cel = np.flatnonzero(bioma == 1)
datas = []
for ano in (2021, 2022, 2023, 2024):
    t = date(ano, 1, 1)
    while t.weekday() != 6:
        t += timedelta(days=1)
    while t.year == ano and t <= bt.ULTIMO_DOMINGO:
        datas.append(t)
        t += timedelta(weeks=1)
P = d["prob"].to_numpy().reshape(len(datas), len(cel))
Y = d["fogo"].to_numpy().astype(bool).reshape(len(datas), len(cel))
Q = np.zeros_like(Y)
for w, t in enumerate(datas):
    i = (t - bt.INICIO).days
    Q[w] = m[cel, i - 29: i + 1].sum(axis=1) == 0
av = P >= 0.5
tot = Y.size
print(f"celulas-semana na Amazonia (2021-2024): {tot:,}")
print(f"  QUIETAS (zero deteccoes em 30 dias): {Q.sum():,} ({Q.mean() * 100:.1f}% do total)")
print(f"  das quietas, tiveram fogo relevante nos 14 dias seguintes: {(Q & Y).sum():,} ({(Q & Y).sum() / Q.sum() * 100:.2f}% das quietas)")
print(f"  das quietas, o modelo avisou (nota >= 50%): {(Q & av).sum():,}")
print(f"  das quietas, avisadas E com fogo relevante (os '69'): {(Q & av & Y).sum():,}")
print(f"  -> cobertura nas quietas: {(Q & av & Y).sum() / (Q & Y).sum() * 100:.1f}% dos inicios de fogo relevante foram avisados")
print(f"  -> precisao nas quietas: {(Q & av & Y).sum() / max(1, (Q & av).sum()) * 100:.1f}% dos avisos em celulas quietas se confirmaram")
print(f"  celulas-semana NAO quietas (ja havia fogo): {(~Q).sum():,}; avisadas e relevantes: {(~Q & av & Y).sum():,}")

print("\nNAS CELULAS QUIETAS: se a brigada olhar so para as X% de maior nota entre as quietas de cada semana")
tot_on = (Q & Y).sum()
for frac in (0.01, 0.02, 0.05, 0.10):
    cap = marc = 0
    for w in range(P.shape[0]):
        idx = np.flatnonzero(Q[w])
        k = max(1, int(round(frac * len(idx))))
        top = idx[np.argsort(-P[w, idx])[:k]]
        cap += Y[w, top].sum(); marc += k
    print(f"  top {int(frac * 100):2d}% das quietas ({marc // P.shape[0]:3d} celulas/semana): captura {cap / tot_on * 100:4.1f}% dos inicios de fogo relevante | precisao {cap / marc * 100:4.1f}% (sorteio: {tot_on / Q.sum() * 100:.2f}%)")
for corte in (0.2, 0.3, 0.4):
    a = Q & (P >= corte)
    print(f"  nota >= {int(corte * 100)}%: avisa {a.sum():,} | captura {(a & Y).sum() / tot_on * 100:4.1f}% | precisao {(a & Y).sum() / max(1, a.sum()) * 100:4.1f}%")

"""Precisao, cobertura e AUC por bioma e no Brasil . Modelo padrao treinado ate 2020, domingos de 2021-2024, aviso = nota >= 50%.
Mesmo modelo e mesmas datas para todos, para a comparacao ser justa."""
import sys
from datetime import date, timedelta
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, r"C:\Users\user\AppData\Local\Temp\firesync_risco\data-pipeline")
import risco_celulas as rc  # noqa: E402
from validacao import backtest_alerta as bt, modelo_risco as mr  # noqa: E402

velha = Path(r"C:\Users\user\AppData\Local\Temp\claude\735018456ef07932\19212868-59be-4d83-8e39-80c0980fbc11\scratchpad")
df = pd.read_parquet(velha / "risco" / "serie.parquet")
serie = rc.preparar_serie(df, bt.FIM)
unidades = serie["unidades"]
fogo14 = bt.somas_moveis(serie["matriz"], 14)
bioma = np.nan_to_num(mr.bioma_das_unidades(unidades, gpd.read_file(velha / "ibge" / "Biomas_250mil.zip")), nan=0)
modelo = rc.treinar(df, date(2020, 12, 31))["modelo"]
datas, d = [], date(2021, 1, 3)
while d <= bt.ULTIMO_DOMINGO:
    datas.append(d)
    d += timedelta(weeks=1)
idx = np.array([(t - bt.INICIO).days for t in datas])
y = fogo14[:, idx + 14].T >= 10
x = mr.empilhar(rc.montar_pistas(serie, datas), y.shape)
p = modelo.predict_proba(x.reshape(-1, x.shape[2]))[:, 1].reshape(y.shape)
pico = np.array([8 <= t.month <= 10 for t in datas])


def linha(cols, mask_t=None):
    pp, yy = p[:, cols], y[:, cols]
    if mask_t is not None:
        pp, yy = pp[mask_t], yy[mask_t]
    av = pp >= 0.5
    tp = (av & yy).sum()
    return {"celulas": int(cols.sum()), "fogo_%": yy.mean() * 100, "precisao_%": tp / max(1, av.sum()) * 100,
            "cobertura_%": tp / max(1, yy.sum()) * 100, "acerto_geral_%": (av == yy).mean() * 100,
            "auc": roc_auc_score(yy.ravel(), pp.ravel()) if 0 < yy.sum() < yy.size else np.nan}


NOMES = {1: "Amazonia", 2: "Caatinga", 3: "Cerrado", 4: "Mata Atlantica", 5: "Pampa", 6: "Pantanal"}
tab = {n: linha(bioma == c) for c, n in NOMES.items()}
tab["BRASIL (com Pantanal)"] = linha(bioma >= 0)
print("POR BIOMA, corte 50%, domingos de 2021-2024 (modelo treinado ate 2020)")
print(pd.DataFrame(tab).T.round(3).to_string())
print("\nTEMPORADA (ago-out) E FORA: precisao | cobertura")
for nome, cols in (("Amazonia", bioma == 1), ("BRASIL", bioma >= 0)):
    a, b = linha(cols, pico), linha(cols, ~pico)
    print(f"  {nome:9s} temporada: {a['precisao_%']:.1f}% | {a['cobertura_%']:.1f}%   fora: {b['precisao_%']:.1f}% | {b['cobertura_%']:.1f}%")

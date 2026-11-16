"""Antecedencia do aviso na Amazonia (2021-2024, treino so com anos anteriores), aviso = nota >= 50% no domingo t.
Para cada celula avisada que depois teve fogo relevante (10+ deteccoes em t+1..t+14): em quantos dias, contados a partir do domingo,
(a) apareceu a PRIMEIRA deteccao e (b) a celula chegou a 10 deteccoes acumuladas. 'Quieta' = zero deteccoes nos 30 dias ate t (nada observado antes).
Limite: o aviso e de domingo (um por semana); com notas diarias a antecedencia pode ser maior."""
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
assert len(datas) == 207 and len(cel) == 2129

primeiro, dez, q_primeiro, q_dez = [], [], [], []
for w, t in enumerate(datas):
    i = (t - bt.INICIO).days
    janela = m[cel, i + 1: i + 15]
    acum = np.cumsum(janela, axis=1)
    relevante = acum[:, -1] >= 10
    quieta = m[cel, i - 29: i + 1].sum(axis=1) == 0
    ok = (P[w] >= 0.5) & relevante
    pri = np.argmax(janela > 0, axis=1) + 1
    d10 = np.argmax(acum >= 10, axis=1) + 1
    primeiro += list(pri[ok]); dez += list(d10[ok])
    q = ok & quieta
    q_primeiro += list(pri[q]); q_dez += list(d10[q])


def resumo(nome, v):
    v = np.array(v)
    print(f"  {nome:42s} n={len(v):6d} | mediana {np.median(v):4.1f} d | media {v.mean():4.1f} d | >=3 dias: {np.mean(v >= 3) * 100:4.1f}% | >=7 dias: {np.mean(v >= 7) * 100:4.1f}%")


print("ANTECEDENCIA, em dias a partir do domingo do aviso (celulas avisadas que tiveram fogo relevante)")
resumo("ate a 1a deteccao (todas)", primeiro)
resumo("ate chegar a 10 deteccoes (todas)", dez)
print("Celulas QUIETAS (zero deteccoes nos 30 dias antes do aviso):")
resumo("ate a 1a deteccao (quietas)", q_primeiro)
resumo("ate chegar a 10 deteccoes (quietas)", q_dez)

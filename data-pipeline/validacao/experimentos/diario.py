"""Antecedencia do aviso com notas DIARIAS na Amazonia (2021-2024), treino so com anos anteriores a cada ano.
Evento = INICIO de fogo relevante numa celula: o dia D em que as deteccoes dos ultimos 14 dias (D-13..D) chegam a 10 ou mais, depois de 14 dias sem estar nesse estado.
Aviso = nota >= 50% em algum dia de D-14 a D-1 (a nota do dia D-14 e exatamente a previsao desse evento). Antecedencia = dias entre o PRIMEIRO dia avisado e D.
Quieta = zero deteccoes nos 30 dias ate D-14 (nada observado antes do primeiro aviso possivel).
CRITERIO fixado antes: reportar, para todos os inicios e para os de celulas quietas: % avisados, mediana da antecedencia, % com 3 dias ou mais e % com 7 dias ou mais (sobre TODOS os inicios)."""
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
df = pd.read_parquet(velha / "risco" / "serie.parquet")
serie = rc.preparar_serie(df, bt.FIM)
unidades, m = serie["unidades"], serie["matriz"]
bioma = np.nan_to_num(mr.bioma_das_unidades(unidades, gpd.read_file(velha / "ibge" / "Biomas_250mil.zip")), nan=0)
cel = np.flatnonzero(bioma == 1)
INI, FIM = date(2021, 1, 1), date(2024, 12, 17)
partes = []
for ano in (2021, 2022, 2023, 2024):
    print(f"== {ano}: treinando ate {ano - 1}-12-31", flush=True)
    modelo = rc.treinar(df, date(ano - 1, 12, 31))["modelo"]
    a, b = max(INI, date(ano, 1, 1)), min(FIM, date(ano, 12, 31))
    dias = [a + timedelta(days=k) for k in range((b - a).days + 1)]
    for c0 in range(0, len(dias), 46):
        lote = dias[c0:c0 + 46]
        x = mr.empilhar(rc.montar_pistas(serie, lote), (len(lote), len(unidades)))[:, cel, :]
        partes.append(modelo.predict_proba(x.reshape(-1, x.shape[2]))[:, 1].reshape(len(lote), len(cel)).astype(np.float32))
    print(f"   pontuado {ano}: {len(dias)} dias", flush=True)
flag = (np.concatenate(partes) >= 0.5).T            # celulas x dias, dia 0 = INI
n_dias = flag.shape[1]
i0 = (INI - bt.INICIO).days
cont = m[cel, i0 - 60: i0 + n_dias + 1].astype(np.float32)        # contagens com 60 dias antes; indice j = dia (j - 60)
C = np.cumsum(cont, axis=1)
T14 = np.full_like(C, np.nan)
T14[:, 14:] = C[:, 14:] - C[:, :-14]                  # deteccoes nos 14 dias terminando em cada dia
rel = T14 >= 10
res = {"todos": [], "quietas": []}
for D in range(60 + 14, 60 + n_dias):                 # dia D: indices de flag = D - 60
    novo_evento = rel[:, D] & ~rel[:, D - 14: D].any(axis=1)
    if not novo_evento.any():
        continue
    cs = np.flatnonzero(novo_evento)
    lead = np.zeros(len(cs), int)
    for k in range(1, 15):
        j = D - 60 - k
        if j >= 0:
            lead = np.where(flag[cs, j], k, lead)
    quieta = cont[cs, D - 14 - 30 + 1: D - 14 + 1].sum(axis=1) == 0
    res["todos"] += list(lead)
    res["quietas"] += list(lead[quieta])
print("\nANTECEDENCIA COM NOTAS DIARIAS, Amazonia 2021-2024 (corte de aviso 50%)")
for nome, v in res.items():
    v = np.array(v)
    av = v > 0
    print(f"  {nome:8s}: {len(v):6d} inicios de fogo relevante | avisados {av.mean() * 100:5.1f}% | mediana (dos avisados) {np.median(v[av]) if av.any() else 0:4.1f} d | "
          f">=3 dias: {np.mean(v >= 3) * 100:5.1f}% | >=7 dias: {np.mean(v >= 7) * 100:5.1f}% | 14 dias: {np.mean(v == 14) * 100:5.1f}%")

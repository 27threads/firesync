"""O modelo, treinado so em domingos, funciona igual nos outros dias da semana?

CRITERIO FIXADO ANTES DE RODAR (15/11/2026): modelo padrao treinado ate 2020 (so domingos), aplicado a cada dia da semana de
2021-2024, de 3 em 3 semanas, com as MESMAS semanas para os 7 dias (domingo, segunda, ..., sabado de cada semana escolhida).
"O dia da semana nao importa" se mantem se nenhum dia ficar mais de 0,005 de AUC abaixo, nem mais de 2% de Brier acima, do domingo.
Brasil sem Pantanal. Tambem mostro a precisao e a cobertura na Amazonia no corte de 50%.
"""
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
ok, amaz = bioma != 6, bioma == 1

print("treinando com dados ate 2020-12-31 (so domingos)", flush=True)
modelo = rc.treinar(df, date(2020, 12, 31))["modelo"]

domingos, d = [], date(2021, 1, 3)
while d <= date(2024, 12, 1):
    domingos.append(d)
    d += timedelta(weeks=3)
NOMES = ["domingo", "segunda", "terca", "quarta", "quinta", "sexta", "sabado"]
linhas = []
for k, nome in enumerate(NOMES):
    datas = [t + timedelta(days=k) for t in domingos]
    idx = np.array([(t - bt.INICIO).days for t in datas])
    y = (fogo14[:, idx + 14].T >= 10)
    x = mr.empilhar(rc.montar_pistas(serie, datas), y.shape)
    p = modelo.predict_proba(x.reshape(-1, x.shape[2]))[:, 1].reshape(y.shape)
    pa, ya = p[:, amaz], y[:, amaz]
    av = pa >= 0.5
    linhas.append({"dia": nome, "datas": len(datas), "auc": roc_auc_score(y[:, ok].ravel(), p[:, ok].ravel()),
                   "brier": np.mean((p[:, ok] - y[:, ok]) ** 2), "amaz_precisao_%": (av & ya).sum() / max(1, av.sum()) * 100,
                   "amaz_cobertura_%": (av & ya).sum() / max(1, ya.sum()) * 100})
    print(f"  {nome}: pronto", flush=True)
t = pd.DataFrame(linhas).set_index("dia")
print("\nPOR DIA DA SEMANA (modelo treinado so em domingos; teste 2021-2024, Brasil sem Pantanal)")
print(t.round(4).to_string())
dom = t.loc["domingo"]
pior_auc = (dom["auc"] - t["auc"]).max()
pior_brier = (t["brier"] / dom["brier"] - 1).max()
print(f"\nPior queda de AUC contra o domingo: {pior_auc:+.4f} (limite 0,005) | pior alta de Brier: {pior_brier:+.1%} (limite 2%)")
print("CONCLUSAO:", "MANTIDO: o dia da semana nao importa" if (pior_auc <= 0.005 and pior_brier <= 0.02) else "REFUTADO: algum dia e pior que o domingo")

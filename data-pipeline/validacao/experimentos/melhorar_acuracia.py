"""O que melhoraria a acuracia do modelo? Duas ideias do Eduardo, testadas.

A) MAIS HISTORICO (o que um MODIS harmonizado de 2002-2011 acrescentaria): curva de aprendizado. Mesmo modelo, treinado ate 2015,
   2017, 2019 e 2020 (3, 5, 7 e 8 anos de treino), testado nos mesmos domingos de 2021-2024. Se a curva ja esta achatada com 7-8 anos,
   dobrar o historico nao deve ajudar muito.
B) AJUSTE DOS PARAMETROS (o modelo usa max_iter=200, taxa 0,1, folhas 31, sem ajuste nenhum). Escolho a melhor configuracao
   NUM PERIODO DE VALIDACAO (treino ate 2018, validacao 2019-2020) e so depois testo em 2021-2024 (treino ate 2020), contra o padrao.
   Assim nao ajusto o modelo olhando para o gabarito do teste.
CRITERIO FIXADO ANTES DE RODAR (15/11/2026): uma mudanca so conta como melhora se, no teste 2021-2024 (Brasil sem Pantanal),
   o AUC sobe >= 0,005 OU o Brier cai >= 2%, e isso vale em pelo menos 3 dos 4 anos. Fora disso, "sem ganho relevante".
Metricas: AUC (ordena bem?), Brier (probabilidade honesta e bem separada: menor e melhor), e na Amazonia precisao e cobertura no corte 50%.
RL ("volta no tempo e ajusta ate acertar") nao e testado: o gabarito ja e conhecido, entao o problema e de aprendizado supervisionado
(o gradient boosting ja ajusta o modelo contra o gabarito, rodada a rodada) e nao ha decisoes que mudem o ambiente.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

sys.path.insert(0, r"C:\Users\user\AppData\Local\Temp\firesync_risco\data-pipeline")
import risco_celulas as rc  # noqa: E402
from validacao import backtest_alerta as bt, modelo_risco as mr  # noqa: E402

velha = Path(r"C:\Users\user\AppData\Local\Temp\claude\735018456ef07932\19212868-59be-4d83-8e39-80c0980fbc11\scratchpad")
saida = Path(r"C:\Users\user\AppData\Local\Temp\claude\7e0d63c41983d7ba\19212868-59be-4d83-8e39-80c0980fbc11\scratchpad\acuracia")
saida.mkdir(parents=True, exist_ok=True)
df = pd.read_parquet(velha / "risco" / "serie.parquet")
serie = rc.preparar_serie(df, bt.FIM)
unidades, m = serie["unidades"], serie["matriz"]
fogo14 = bt.somas_moveis(m, 14)
bioma = np.nan_to_num(mr.bioma_das_unidades(unidades, gpd.read_file(velha / "ibge" / "Biomas_250mil.zip")), nan=0)
ok, amaz = bioma != 6, bioma == 1


def domingos(ini, fim):
    d = ini
    while d.weekday() != 6:
        d += timedelta(days=1)
    saida_ = []
    while d <= fim and d <= bt.ULTIMO_DOMINGO:
        saida_.append(d)
        d += timedelta(weeks=1)
    return saida_


def montar(datas):
    pist = rc.montar_pistas(serie, datas)
    x = mr.empilhar(pist, (len(datas), len(unidades)))
    idx = np.array([(t - bt.INICIO).days for t in datas])
    return x, (fogo14[:, idx + 14].T >= 10)


TESTE = domingos(date(2021, 1, 1), date(2024, 12, 31))
VALID = domingos(date(2019, 1, 1), date(2020, 12, 31))
X_TESTE, Y_TESTE = montar(TESTE)
X_VALID, Y_VALID = montar(VALID)
ANO_T = np.array([t.year for t in TESTE])
print(f"domingos de teste {len(TESTE)}, de validacao {len(VALID)}", flush=True)


def treinar(fim, **params):
    s = rc.preparar_serie(df, fim)
    datas = rc.domingos_de_treino(s)
    dias = np.array([(t - bt.INICIO).days for t in datas])
    alvo = bt.somas_moveis(s["matriz"], 14)[:, dias + 14].T >= 10
    x = mr.empilhar(rc.montar_pistas(s, datas), alvo.shape)
    linhas, y = x.reshape(-1, x.shape[2]), alvo.ravel()
    if len(y) > rc.LINHAS_TREINO:
        e = np.random.default_rng(rc.SEMENTE).choice(len(y), rc.LINHAS_TREINO, replace=False)
        linhas, y = linhas[e], y[e]
    base = dict(max_iter=200, learning_rate=0.1, random_state=rc.SEMENTE)
    base.update(params)
    return HistGradientBoostingClassifier(**base).fit(linhas, y)


def prever(modelo, x):
    return modelo.predict_proba(x.reshape(-1, x.shape[2]))[:, 1].reshape(x.shape[:2])


def medir(p, y, mask_cols, anos=None):
    pp, yy = p[:, mask_cols], y[:, mask_cols]
    r = {"auc": roc_auc_score(yy.ravel(), pp.ravel()), "brier": np.mean((pp - yy) ** 2)}
    av = pp >= 0.5
    r["precisao_%"] = (av & yy).sum() / max(1, av.sum()) * 100
    r["cobertura_%"] = (av & yy).sum() / max(1, yy.sum()) * 100
    return r


print("\nA) CURVA DE APRENDIZADO (modelo padrao; teste 2021-2024, Brasil sem Pantanal)", flush=True)
linhas, por_ano = [], {}
for fim, anos_treino in ((date(2015, 12, 31), 3), (date(2017, 12, 31), 5), (date(2019, 12, 31), 7), (date(2020, 12, 31), 8)):
    p = prever(treinar(fim), X_TESTE)
    r = medir(p, Y_TESTE, ok)
    ra = medir(p, Y_TESTE, amaz)
    por_ano[anos_treino] = {a: np.mean((p[ANO_T == a][:, ok] - Y_TESTE[ANO_T == a][:, ok]) ** 2) for a in (2021, 2022, 2023, 2024)}
    linhas.append({"anos_de_treino": anos_treino, "auc": r["auc"], "brier": r["brier"], "amaz_precisao_%": ra["precisao_%"], "amaz_cobertura_%": ra["cobertura_%"]})
    print(f"  {anos_treino} anos: AUC {r['auc']:.4f} | Brier {r['brier']:.5f} | Amazonia precisao {ra['precisao_%']:.1f}% cobertura {ra['cobertura_%']:.1f}%", flush=True)
curva = pd.DataFrame(linhas).set_index("anos_de_treino")
curva.to_csv(saida / "curva_aprendizado.csv")

print("\nB) AJUSTE DOS PARAMETROS: escolha na validacao (treino ate 2018, validacao 2019-2020)", flush=True)
CONFIGS = {"padrao (200, 0,1, folhas 31)": {}, "400 iter, taxa 0,05": dict(max_iter=400, learning_rate=0.05),
           "folhas 15": dict(max_leaf_nodes=15), "folhas 63": dict(max_leaf_nodes=63),
           "min 200 por folha": dict(min_samples_leaf=200), "100 iter": dict(max_iter=100)}
val = {}
for nome, params in CONFIGS.items():
    p = prever(treinar(date(2018, 12, 31), **params), X_VALID)
    r = medir(p, Y_VALID, ok)
    val[nome] = (r["brier"], r["auc"])
    print(f"  {nome:30s} validacao: Brier {r['brier']:.5f} | AUC {r['auc']:.4f}", flush=True)
melhor = min(val, key=lambda k: val[k][0])
print(f"  -> melhor na validacao: {melhor}", flush=True)

print("\nTESTE 2021-2024 (treino ate 2020): padrao contra a escolhida", flush=True)
p0 = prever(treinar(date(2020, 12, 31)), X_TESTE)
p1 = prever(treinar(date(2020, 12, 31), **CONFIGS[melhor]), X_TESTE)
for nome, p in (("padrao", p0), (melhor, p1)):
    r, ra = medir(p, Y_TESTE, ok), medir(p, Y_TESTE, amaz)
    print(f"  {nome:30s} Brasil: AUC {r['auc']:.4f} Brier {r['brier']:.5f} | Amazonia: AUC {ra['auc']:.4f} precisao {ra['precisao_%']:.1f}% cobertura {ra['cobertura_%']:.1f}%")
ganho_auc = medir(p1, Y_TESTE, ok)["auc"] - medir(p0, Y_TESTE, ok)["auc"]
ganho_brier = 1 - medir(p1, Y_TESTE, ok)["brier"] / medir(p0, Y_TESTE, ok)["brier"]
anos_ok = 0
for a in (2021, 2022, 2023, 2024):
    k = ANO_T == a
    da = medir(p1[k], Y_TESTE[k], ok)["auc"] - medir(p0[k], Y_TESTE[k], ok)["auc"]
    db = 1 - medir(p1[k], Y_TESTE[k], ok)["brier"] / medir(p0[k], Y_TESTE[k], ok)["brier"]
    anos_ok += int(da >= 0.005 or db >= 0.02)
    print(f"    {a}: AUC {da:+.4f} | Brier {db:+.1%}")
print(f"\nCRITERIO: ganho de AUC {ganho_auc:+.4f} (>=0,005?) | ganho de Brier {ganho_brier:+.1%} (>=2%?) | anos com melhora {anos_ok}/4 (>=3?)")
print("CONCLUSAO B:", "MELHORA RELEVANTE" if ((ganho_auc >= 0.005 or ganho_brier >= 0.02) and anos_ok >= 3) else "SEM GANHO RELEVANTE")
d0, d1 = curva.loc[7], curva.loc[8]
print(f"\nCONCLUSAO A: de 3 para 8 anos de treino o AUC foi de {curva.loc[3, 'auc']:.4f} para {curva.loc[8, 'auc']:.4f}; "
      f"de 7 para 8 anos, {d1['auc'] - d0['auc']:+.4f} no AUC e {1 - d1['brier'] / d0['brier']:+.1%} no Brier.")

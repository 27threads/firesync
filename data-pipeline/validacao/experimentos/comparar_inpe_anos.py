"""Comparação do nosso modelo com o índice de Risco de Fogo do INPE em 4 anos (2021 a 2024), sem o Pantanal.

CRITÉRIO FIXADO ANTES DE RODAR (15/11/2026):
  a conclusão 'o nosso modelo ordena melhor que o INPE' se mantém só se, em CADA um dos 4 anos, o nosso acerto nas 10% mais
  arriscadas for maior que o do INPE; e 'o INPE não acrescenta' se, em cada ano, juntar o INPE (regressão logística com
  validação cruzada por semana) não elevar o acerto nas 10% mais arriscadas em mais de 1 ponto.
Cada ano de teste treina o nosso modelo só com anos anteriores. O alvo: 10 ou mais detecções do VIIRS nos 14 dias seguintes.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import geopandas as gpd
import h3
import h5py
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, r"C:\Users\user\AppData\Local\Temp\firesync_risco\data-pipeline")
import risco_celulas as rc  # noqa: E402
from validacao import backtest_alerta as bt, modelo_risco as mr  # noqa: E402

base = Path(r"C:\Users\user\AppData\Local\Temp\claude\735018456ef07932\19212868-59be-4d83-8e39-80c0980fbc11\scratchpad")
ANOS = [2021, 2022, 2023, 2024]
df = pd.read_parquet(base / "risco" / "serie.parquet")
serie = rc.preparar_serie(df, date(2024, 12, 31))
unidades, m = serie["unidades"], serie["matriz"]
fogo14 = bt.somas_moveis(m, 14)
bioma = np.nan_to_num(mr.bioma_das_unidades(unidades, gpd.read_file(base / "ibge" / "Biomas_250mil.zip")), nan=0)
sem_pantanal = bioma != 6
filhos = [h3.cell_to_children(h3.int_to_str(int(u)), 6) for u in unidades]
pts = np.array([h3.cell_to_latlng(f) for fs in filhos for f in fs])
n_filhos = len(filhos[0])
GRADE = {}


def arquivo_inpe(ano, d):
    if ano == 2024:
        return base / "inpe_risco_2024" / f"INPE_FireRiskModel_2.2_FireRisk_{d:%Y%m%d}.nc"
    return base / f"inpe_risco_{ano}" / f"rf_{d:%Y%m%d}.nc"


def ler_inpe(ano, datas):
    saida = np.full((len(datas), len(unidades)), np.nan, np.float32)
    for w, d in enumerate(datas):
        f = arquivo_inpe(ano, d)
        if not f.exists():
            print(f"  aviso: falta {f.name}")
            continue
        with h5py.File(f, "r") as h:
            lat, lon, forma = h["lat"][:], h["lon"][:], h["rf"].shape
            if not GRADE:
                GRADE.update(forma=forma, lat0=lat[0], dlat=lat[1] - lat[0], lon0=lon[0], dlon=lon[1] - lon[0])
            assert forma == GRADE["forma"] and abs(lat[0] - GRADE["lat0"]) < 1e-6, f"grade diferente em {f.name}"
            i = np.clip(np.rint((pts[:, 0] - lat[0]) / (lat[1] - lat[0])).astype(int), 0, len(lat) - 1)
            k = np.clip(np.rint((pts[:, 1] - lon[0]) / (lon[1] - lon[0])).astype(int), 0, len(lon) - 1)
            grade = h["rf"][0]
            v = grade[i, k].astype(np.float32)
            del grade
        v[v < 0] = np.nan
        with np.errstate(all="ignore"):
            saida[w] = np.nanmean(v.reshape(len(unidades), n_filhos), axis=1)
    return saida


def topo(score, valido, fracao=0.10):
    t = np.zeros(score.shape, bool)
    for w in range(score.shape[0]):
        ix = np.flatnonzero(valido[w])
        if len(ix):
            t[w, ix[np.argsort(-score[w, ix])[: max(1, int(round(fracao * len(ix))))]]] = True
    return t


def metricas(score, y, ok, pico):
    s = np.where(ok, score, -np.inf)
    t = topo(s, ok)
    return {"auc": roc_auc_score(y[ok], s[ok]), "top10": y[t].mean(),
            "top10_pico": y[pico][t[pico]].mean() if pico.any() else np.nan,
            "top10_fora": y[~pico][t[~pico]].mean() if (~pico).any() else np.nan}


linhas = []
for ano in ANOS:
    print(f"== {ano}: treinando com dados até {ano - 1}-12-31", flush=True)
    modelo = rc.treinar(df, date(ano - 1, 12, 31))
    d = date(ano, 1, 1)
    while d.weekday() != 6:
        d += timedelta(days=1)
    datas = []
    while d.year == ano and d <= bt.ULTIMO_DOMINGO:
        datas.append(d)
        d += timedelta(weeks=1)
    idx = np.array([(t - bt.INICIO).days for t in datas])
    y = fogo14[:, idx + 14].T >= 10
    pist = rc.montar_pistas(serie, datas)
    X = mr.empilhar(pist, y.shape)
    nosso = modelo["modelo"].predict_proba(X.reshape(-1, X.shape[2]))[:, 1].reshape(y.shape)
    regua = pd.DataFrame(pist["s30"]).rank(axis=1).to_numpy() + pd.DataFrame(pist["normal_passado"]).rank(axis=1).to_numpy()
    inpe = ler_inpe(ano, datas)
    ok = sem_pantanal[None, :] & np.isfinite(inpe)
    pico = np.array([8 <= t.month <= 10 for t in datas])
    r = {"ano": ano, "semanas": len(datas), "fogo": y[ok].mean()}
    for nome, s in (("nosso", nosso), ("inpe", inpe), ("regua", regua)):
        for k, v in metricas(s, y, ok, pico).items():
            r[f"{nome}_{k}"] = v
    # células quietas (0 detecções em 30 dias): início de fogo
    quietas = ok & (pist["s30"] == 0)
    r["quietas_auc_nosso"], r["quietas_auc_inpe"] = roc_auc_score(y[quietas], nosso[quietas]), roc_auc_score(y[quietas], np.nan_to_num(inpe)[quietas])
    # o INPE acrescenta? regressão logística, validação cruzada por semana
    g = np.repeat(np.arange(len(datas))[:, None], y.shape[1], 1)[ok]
    p = np.clip(nosso[ok], 1e-4, 1 - 1e-4)
    f_nosso = np.log(p / (1 - p))
    pct = pd.DataFrame(np.where(ok, inpe, np.nan)).rank(axis=1, pct=True).to_numpy()[ok]
    F = np.column_stack([f_nosso, inpe[ok], pct])
    oof = {"so_nosso": np.zeros(len(g)), "com_inpe": np.zeros(len(g))}
    for tr, te in GroupKFold(5).split(F, y[ok], g):
        oof["so_nosso"][te] = LogisticRegression(max_iter=500).fit(F[tr][:, :1], y[ok][tr]).predict_proba(F[te][:, :1])[:, 1]
        oof["com_inpe"][te] = LogisticRegression(max_iter=500).fit(F[tr], y[ok][tr]).predict_proba(F[te])[:, 1]
    tmp = np.full(y.shape, -np.inf)
    for nome, v in oof.items():
        tmp[ok] = v
        r[f"lr_{nome}_top10"] = y[topo(tmp, ok)].mean()
    linhas.append(r)
    pd.DataFrame(linhas).to_csv(base / "inpe_comparacao" / "comparacao_anos.csv", index=False)
    print(f"  pronto: nosso top10 {r['nosso_top10']:.1%} | INPE {r['inpe_top10']:.1%}", flush=True)

t = pd.DataFrame(linhas).set_index("ano")
fmt = lambda c: (t[c] * 100).round(1)  # noqa: E731
print("\nACERTO NAS 10% MAIS ARRISCADAS E AUC, POR ANO (sem o Pantanal)")
print(pd.DataFrame({"fogo_%": fmt("fogo"), "nosso_top10": fmt("nosso_top10"), "inpe_top10": fmt("inpe_top10"), "regua_top10": fmt("regua_top10"),
                    "nosso_auc": t["nosso_auc"].round(3), "inpe_auc": t["inpe_auc"].round(3), "regua_auc": t["regua_auc"].round(3)}).to_string())
print("\nTEMPORADA (ago-out) E FORA, top10:")
print(pd.DataFrame({"nosso_pico": fmt("nosso_top10_pico"), "inpe_pico": fmt("inpe_top10_pico"), "nosso_fora": fmt("nosso_top10_fora"), "inpe_fora": fmt("inpe_top10_fora")}).to_string())
print("\nCÉLULAS QUIETAS (início de fogo), AUC:")
print(t[["quietas_auc_nosso", "quietas_auc_inpe"]].round(3).to_string())
print("\nO INPE ACRESCENTA? acerto top10, regressão logística (validação cruzada por semana):")
print((t[["lr_so_nosso_top10", "lr_com_inpe_top10"]] * 100).round(1).to_string())
ganha = (t["nosso_top10"] > t["inpe_top10"]).all()
soma = ((t["lr_com_inpe_top10"] - t["lr_so_nosso_top10"]) * 100).max()
print(f"\nCRITÉRIO 1 (nosso > INPE em todos os anos): {'MANTIDO' if ganha else 'REFUTADO'}")
print(f"CRITÉRIO 2 (INPE acrescenta no máximo 1 ponto em todos os anos): {'MANTIDO' if soma <= 1 else 'REFUTADO'} (maior ganho: {soma:+.2f} pt)")

"""O dia de hoje, ainda incompleto, derruba as notas? E usar o ultimo dia COMPLETO (hoje - 1) resolve?

CRITERIOS FIXADOS ANTES DE RODAR (15/11/2026):
  Variantes, todas contra o MESMO gabarito (>= 10 deteccoes VIIRS nos 14 dias seguintes ao domingo t, sem Pantanal):
    COMPLETO  : dia t inteiro (o que o treino viu; na producao so existe de madrugada, no dia seguinte)
    MANHA     : dia t so com o que chegou ate 12:00 UTC (so a passagem da madrugada do satelite)
    TARDE     : dia t com o que chegou ate 18:00 UTC (passagem da tarde ainda chegando)
    NOITE     : dia t com o que chegou ate 21:00 UTC (quase tudo)
    ONTEM     : a proposta, notas calculadas com o dia t-1 inteiro (nenhum dia parcial)
  C1 (o vies do dia parcial e real): na MANHA, o erro de calibracao (media prevista - taxa observada) piora >= 0,5 ponto
     percentual em valor absoluto contra o COMPLETO, OU o Brier piora >= 2% relativo, OU >= 3% das celulas descem de faixa.
     Se nenhum dos tres: C1 REFUTADO (o efeito e pequeno).
  C2 (a proposta e pelo menos tao boa quanto usar o dia parcial): o Brier do ONTEM <= o da MANHA e o AUC do ONTEM nao fica
     mais de 0,002 abaixo do da MANHA. Se nao, a proposta NAO e melhor.
  C3 (custo de usar dado com 1 dia de atraso): ONTEM contra COMPLETO, so reportado (sem criterio).
Cada ano de teste treina so com anos anteriores. Domingos de 3 em 3 semanas (para caber no tempo).
Limite: o corte por horario simula o que ja chegou; nao simula atrasos e lotes reais do NRT.
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
saida = Path(r"C:\Users\user\AppData\Local\Temp\claude\7e0d63c41983d7ba\19212868-59be-4d83-8e39-80c0980fbc11\scratchpad\dia_parcial")
saida.mkdir(parents=True, exist_ok=True)
ANOS = [2022, 2023, 2024]
CORTES = {"MANHA": "1200", "TARDE": "1800", "NOITE": "2100"}
VARIANTES = ["COMPLETO", "MANHA", "TARDE", "NOITE", "ONTEM"]
regras = rc.carregar_regras()
CORTES_FAIXA = np.array(sorted(t["min_prob"] for t in regras["tiers"]))      # 0.0, 0.2, 0.4, 0.6
NOMES_FAIXA = [t["tier"] for t in sorted(regras["tiers"], key=lambda t: t["min_prob"])]

df = pd.read_parquet(velha / "risco" / "serie.parquet")
serie = rc.preparar_serie(df, bt.FIM)
unidades, m = serie["unidades"], serie["matriz"]
z = np.zeros_like(m)
viz = mr.vizinhos(unidades)
lat, lon = mr.posicao_das_unidades(unidades)
fogo14 = bt.somas_moveis(m, 14)
bioma = np.nan_to_num(mr.bioma_das_unidades(unidades, gpd.read_file(velha / "ibge" / "Biomas_250mil.zip")), nan=0)
sem_pantanal = bioma != 6


def pistas(datas):
    p = mr.pistas_fogo(m, z, datas, viz)
    forma = (len(datas), len(unidades))
    p.update(semana=np.repeat(np.array([d.isocalendar()[1] for d in datas], np.float32)[:, None], forma[1], 1),
             lat=np.tile(lat, (forma[0], 1)), lon=np.tile(lon, (forma[0], 1)))
    return {k: p[k] for k in rc.FEATURES}


def domingos(ano):
    d = date(ano, 1, 1)
    while d.weekday() != 6:
        d += timedelta(days=1)
    saida_ = []
    while d.year == ano and d <= bt.ULTIMO_DOMINGO:
        saida_.append(d)
        d += timedelta(weeks=1)
    return saida_[::3]


def topo(score, valido, fracao=0.10):
    t = np.zeros(score.shape, bool)
    for w in range(score.shape[0]):
        ix = np.flatnonzero(valido[w])
        t[w, ix[np.argsort(-score[w, ix])[: max(1, int(round(fracao * len(ix))))]]] = True
    return t


acum = {v: {"p": [], "y": [], "pico": [], "data": []} for v in VARIANTES}
chegada = {c: [] for c in CORTES}          # (mes, n_parcial, n_total) por corte
for ano in ANOS:
    print(f"== {ano}: treinando com dados ate {ano - 1}-12-31", flush=True)
    modelo = rc.treinar(df, date(ano - 1, 12, 31))["modelo"]
    datas = domingos(ano)
    idx = np.array([(t - bt.INICIO).days for t in datas])
    y = fogo14[:, idx + 14].T >= 10
    ok = np.broadcast_to(sem_pantanal[None, :], y.shape)
    pico = np.array([8 <= t.month <= 10 for t in datas])

    def prever(pist):
        x = mr.empilhar(pist, (len(pist["s7"]), len(unidades)))
        return modelo.predict_proba(x.reshape(-1, x.shape[2]))[:, 1].reshape(len(pist["s7"]), len(unidades))

    prob = {"COMPLETO": prever(pistas(datas)),
            "ONTEM": prever(pistas([t - timedelta(days=1) for t in datas]))}

    # dia parcial: le o ano bruto uma vez e corta por horario de aquisicao
    bruto = pd.read_csv(velha / "firms_brasil" / f"viirs-snpp_{ano}_Brazil.csv", dtype=mr.TIPOS)
    hora = bruto["acq_time"].str.zfill(4)
    for nome, corte in CORTES.items():
        parcial = mr.serie_diaria(bruto[hora < corte])
        completo_ano = df[df["data"].astype(str).str[:4] == str(ano)]
        for mes in range(1, 13):
            pm = parcial[parcial["data"].str[5:7] == f"{mes:02d}"]["n"].sum()
            cm = completo_ano[completo_ano["data"].astype(str).str[5:7] == f"{mes:02d}"]["n"].sum()
            chegada[nome].append((mes, pm, cm))
        por_dia = {k: g for k, g in parcial.groupby("data")}
        linhas = []
        for t in datas:
            i = (t - bt.INICIO).days
            guardado = m[:, i].copy()
            m[:, i] = 0
            g = por_dia.get(t.isoformat())
            if g is not None:
                ix = np.searchsorted(unidades, g["unidade"].to_numpy())
                assert (unidades[ix] == g["unidade"].to_numpy()).all()
                m[ix, i] = g["n"].to_numpy(np.float32)
            linhas.append(prever(pistas([t]))[0])
            m[:, i] = guardado
        prob[nome] = np.array(linhas)
    del bruto, hora
    for v in VARIANTES:
        acum[v]["p"].append(np.where(ok, prob[v], np.nan))
        acum[v]["y"].append(np.where(ok, y, np.nan))
        acum[v]["pico"].append(np.repeat(pico[:, None], len(unidades), 1))
    print(f"   pronto {ano}: {len(datas)} domingos", flush=True)

P = {v: np.concatenate(acum[v]["p"]) for v in VARIANTES}
Y = np.concatenate(acum["COMPLETO"]["y"])
PICO = np.concatenate(acum["COMPLETO"]["pico"])
OK = np.isfinite(Y)


def metricas(p, mascara):
    mk = OK & mascara
    pp, yy = p[mk], Y[mk]
    t = topo(np.where(mk, p, -np.inf), mk)
    return {"media_prev_%": pp.mean() * 100, "taxa_obs_%": yy.mean() * 100, "erro_pp": (pp.mean() - yy.mean()) * 100,
            "brier": np.mean((pp - yy) ** 2), "auc": roc_auc_score(yy, pp), "top10_%": Y[t].mean() * 100}


TUDO = np.ones_like(OK)
tabela = pd.DataFrame({v: metricas(P[v], TUDO) for v in VARIANTES}).T
print("\n1) QUANTO DO DIA CHEGA ATE CADA HORA (parte das deteccoes do dia ja disponivel), media 2022-24")
chg = pd.DataFrame({c: [sum(a for mes, a, b in chegada[c] if mes == k) / max(1, sum(b for mes, a, b in chegada[c] if mes == k)) * 100
                        for k in range(1, 13)] for c in CORTES}, index=range(1, 13))
print(chg.round(0).T.to_string(float_format=lambda v: f"{v:.0f}"))
print("\n2) CALIBRACAO E ORDENACAO, todas as semanas (sem Pantanal); gabarito: >=10 deteccoes nos 14 dias seguintes")
print(tabela.round(4).to_string())
print("\n3) POR FAIXA (limites 0,2 / 0,4 / 0,6): % das celulas em cada faixa | taxa observada na faixa")
for v in VARIANTES:
    fx = np.digitize(P[v][OK], CORTES_FAIXA[1:])
    yy = Y[OK]
    partes = [f"{NOMES_FAIXA[k]} {np.mean(fx == k) * 100:5.1f}% | {yy[fx == k].mean() * 100 if (fx == k).any() else float('nan'):5.1f}%" for k in range(len(NOMES_FAIXA))]
    print(f"  {v:9s} " + "  ".join(partes))
print("\n4) MIGRACAO DE FAIXA CONTRA O COMPLETO (% das celulas)")
base = np.digitize(P["COMPLETO"][OK], CORTES_FAIXA[1:])
for v in VARIANTES[1:]:
    fx = np.digitize(P[v][OK], CORTES_FAIXA[1:])
    print(f"  {v:9s} desce {np.mean(fx < base) * 100:5.2f}% | sobe {np.mean(fx > base) * 100:5.2f}% | igual {np.mean(fx == base) * 100:5.2f}%")
print("\n5) TEMPORADA (ago-out) E FORA: erro de calibracao (pp) e Brier")
for nome, mask in (("pico", PICO), ("fora", ~PICO)):
    t = pd.DataFrame({v: metricas(P[v], mask) for v in VARIANTES}).T[["erro_pp", "brier", "auc", "top10_%"]]
    print(f"  -- {nome}")
    print(t.round(4).to_string())

c, m_ = tabela.loc["COMPLETO"], tabela.loc["MANHA"]
desce = np.mean(np.digitize(P["MANHA"][OK], CORTES_FAIXA[1:]) < base) * 100
c1a, c1b, c1c = abs(m_["erro_pp"]) - abs(c["erro_pp"]) >= 0.5, (m_["brier"] / c["brier"] - 1) >= 0.02, desce >= 3
print(f"\nC1 (vies do dia parcial e real, manha): erro {abs(m_['erro_pp']) - abs(c['erro_pp']):+.2f} pp (>=0,5?) {c1a} | "
      f"Brier {m_['brier'] / c['brier'] - 1:+.1%} (>=2%?) {c1b} | descem de faixa {desce:.2f}% (>=3%?) {c1c} -> "
      f"{'MANTIDO' if (c1a or c1b or c1c) else 'REFUTADO'}")
o = tabela.loc["ONTEM"]
c2 = (o["brier"] <= m_["brier"]) and (o["auc"] >= m_["auc"] - 0.002)
print(f"C2 (ONTEM >= MANHA): Brier {o['brier']:.4f} vs {m_['brier']:.4f} | AUC {o['auc']:.4f} vs {m_['auc']:.4f} -> {'MANTIDO' if c2 else 'REFUTADO'}")
print(f"C3 (custo do atraso, ONTEM contra COMPLETO): Brier {o['brier'] - c['brier']:+.4f} | AUC {o['auc'] - c['auc']:+.4f} | top10 {o['top10_%'] - c['top10_%']:+.2f} pt")
tabela.to_csv(saida / "dia_parcial_resumo.csv")

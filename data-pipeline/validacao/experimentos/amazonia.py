"""Quanto o modelo acerta na Amazonia (bioma 1 do IBGE)? Teste em avanco 2021-2024, todos os domingos, treino so com anos anteriores.

METRICAS FIXADAS ANTES DE RODAR (15/11/2026). Unidade: celula H3 res 4 (~1.770 km2) em um domingo. Alvo: 10 ou mais
deteccoes VIIRS nos 14 dias seguintes. "Aviso" = celula com nota >= corte.
  - taxa de fogo: parte das celulas-semana que tiveram fogo relevante (referencia ingenua: dizer sempre "sem fogo")
  - acerto geral no corte 50%: parte das celulas em que o modelo acertou (aviso e fogo, ou sem aviso e sem fogo)
  - precisao: dos avisos, quantos tiveram fogo relevante;  cobertura: dos locais com fogo relevante, quantos foram avisados
  - calibracao: na faixa de nota de 10 em 10%, a nota media prevista contra a frequencia observada, em pontos percentuais
Vieses a vigiar: (1) o acerto geral e inflado pelas celulas faceis (muitas sem fogo): por isso mostro a referencia ingenua;
(2) a temporada (ago-out) e o resto do ano tem comportamentos muito diferentes: separo; (3) so 4 anos de teste: mostro por ano;
(4) o corte de 50% e arbitrario: mostro tambem 40% e 60%; (5) semanas seguidas se sobrepoem: nao sao independentes.
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
saida = Path(r"C:\Users\user\AppData\Local\Temp\claude\7e0d63c41983d7ba\19212868-59be-4d83-8e39-80c0980fbc11\scratchpad\amazonia")
saida.mkdir(parents=True, exist_ok=True)
ANOS = [2021, 2022, 2023, 2024]
df = pd.read_parquet(velha / "risco" / "serie.parquet")
serie = rc.preparar_serie(df, bt.FIM)
unidades, m = serie["unidades"], serie["matriz"]
fogo14 = bt.somas_moveis(m, 14)
bioma = np.nan_to_num(mr.bioma_das_unidades(unidades, gpd.read_file(velha / "ibge" / "Biomas_250mil.zip")), nan=0)
amazonia = bioma == 1
print(f"celulas na Amazonia: {amazonia.sum()} de {len(unidades)}", flush=True)

P, Y, PICO, ANO = [], [], [], []
for ano in ANOS:
    print(f"== {ano}: treinando com dados ate {ano - 1}-12-31", flush=True)
    modelo = rc.treinar(df, date(ano - 1, 12, 31))["modelo"]
    d = date(ano, 1, 1)
    while d.weekday() != 6:
        d += timedelta(days=1)
    datas = []
    while d.year == ano and d <= bt.ULTIMO_DOMINGO:
        datas.append(d)
        d += timedelta(weeks=1)
    idx = np.array([(t - bt.INICIO).days for t in datas])
    y = (fogo14[:, idx + 14].T >= 10)[:, amazonia]
    pist = rc.montar_pistas(serie, datas)
    x = mr.empilhar(pist, (len(datas), len(unidades)))[:, amazonia, :]
    p = modelo.predict_proba(x.reshape(-1, x.shape[2]))[:, 1].reshape(y.shape)
    pico = np.repeat(np.array([8 <= t.month <= 10 for t in datas])[:, None], y.shape[1], 1)
    P.append(p.ravel()); Y.append(y.ravel()); PICO.append(pico.ravel()); ANO.append(np.full(p.size, ano))
    print(f"   pronto {ano}: {len(datas)} domingos", flush=True)
P, Y, PICO, ANO = (np.concatenate(v) for v in (P, Y, PICO, ANO))
pd.DataFrame({"prob": P, "fogo": Y, "pico": PICO, "ano": ANO}).to_parquet(saida / "amazonia_notas.parquet")


def resumo(mask, corte=0.5):
    p, y = P[mask], Y[mask]
    av = p >= corte
    tp, fp, fn = (av & y).sum(), (av & ~y).sum(), (~av & y).sum()
    return {"celulas_semana": int(mask.sum()), "taxa_fogo_%": y.mean() * 100, "ingenuo_acerta_%": (1 - y.mean()) * 100,
            "acerto_geral_%": ((av == y).mean()) * 100, "precisao_%": tp / max(1, tp + fp) * 100, "cobertura_%": tp / max(1, tp + fn) * 100,
            "avisos_%_das_celulas": av.mean() * 100, "media_prevista_%": p.mean() * 100, "auc": roc_auc_score(y, p) if 0 < y.sum() < len(y) else np.nan}


todos = np.ones_like(Y, bool)
print("\n1) AMAZONIA, corte de aviso em 50% (todas as semanas, 2021-2024)")
print(pd.Series(resumo(todos)).round(1).to_string())
print("\n2) POR CORTE (todas as semanas)")
print(pd.DataFrame({f"corte {int(c * 100)}%": resumo(todos, c) for c in (0.4, 0.5, 0.6)}).T[["avisos_%_das_celulas", "precisao_%", "cobertura_%", "acerto_geral_%"]].round(1).to_string())
print("\n3) TEMPORADA (ago-out) E FORA, corte 50%")
print(pd.DataFrame({"temporada": resumo(PICO), "fora": resumo(~PICO)}).T[["celulas_semana", "taxa_fogo_%", "ingenuo_acerta_%", "acerto_geral_%", "precisao_%", "cobertura_%", "auc"]].round(1).to_string())
print("\n4) POR ANO, corte 50%")
print(pd.DataFrame({a: resumo(ANO == a) for a in ANOS}).T[["taxa_fogo_%", "ingenuo_acerta_%", "acerto_geral_%", "precisao_%", "cobertura_%", "auc"]].round(1).to_string())
print("\n5) CALIBRACAO NA AMAZONIA: faixa de nota -> nota media prevista | frequencia observada | diferenca (pontos percentuais)")
bins = np.digitize(P, np.arange(0.1, 1.0, 0.1))
for b in range(10):
    k = bins == b
    if k.sum() >= 200:
        print(f"  nota {b * 10:3d}-{b * 10 + 10:3d}%: {k.sum():7d} celulas-semana | prevista {P[k].mean() * 100:5.1f}% | observada {Y[k].mean() * 100:5.1f}% | dif {P[k].mean() * 100 - Y[k].mean() * 100:+5.1f} pp")
print("\n6) FAIXAS DO MAPA NA AMAZONIA: % das celulas | frequencia observada | historica (config)")
cfg = rc.carregar_regras()["historical_share"]
for nome, lo, hi in (("very_high", 0.6, 1.01), ("high", 0.4, 0.6), ("medium", 0.2, 0.4), ("lower", 0.0, 0.2)):
    k = (P >= lo) & (P < hi)
    print(f"  {nome:9s} {k.mean() * 100:5.1f}% das celulas | observada {Y[k].mean() * 100:5.1f}% | Brasil {cfg[nome] * 100:.0f}%")
e = abs(P.mean() - Y.mean()) * 100
print(f"\nCalibracao geral na Amazonia: prevista {P.mean() * 100:.1f}% contra observada {Y.mean() * 100:.1f}% (diferenca {e:.1f} pp)")

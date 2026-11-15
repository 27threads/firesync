"""Curva de captura na Amazonia (2021-2024, treino so com anos anteriores), a partir das notas ja gravadas.
Pergunta: se a brigada olhar so para as X% de celulas de maior nota de cada domingo, que parte do fogo relevante (10+ deteccoes em 14 dias) ela pega?
Referencia: sortear X% das celulas captura X%. Area de uma celula res 4: ~1.770 km2. Semanas por ano: 52, 52, 53, 50 (celulas por semana: 2129)."""
from pathlib import Path

import numpy as np
import pandas as pd

d = pd.read_parquet(Path(r"C:\Users\user\AppData\Local\Temp\claude\7e0d63c41983d7ba\19212868-59be-4d83-8e39-80c0980fbc11\scratchpad\amazonia\amazonia_notas.parquet"))
CEL, SEMANAS = 2129, [52, 52, 53, 50]
n_sem = sum(SEMANAS)
assert len(d) == n_sem * CEL
P = d["prob"].to_numpy().reshape(n_sem, CEL)
Y = d["fogo"].to_numpy().astype(bool).reshape(n_sem, CEL)
PICO = d["pico"].to_numpy().reshape(n_sem, CEL)[:, 0]
ANO = d["ano"].to_numpy().reshape(n_sem, CEL)[:, 0]


def captura(mask_sem, fracao):
    cap, total, marcadas = 0, 0, 0
    for w in np.flatnonzero(mask_sem):
        k = max(1, int(round(fracao * CEL)))
        topo = np.argsort(-P[w])[:k]
        cap += Y[w, topo].sum()
        total += Y[w].sum()
        marcadas += k
    return cap / total * 100, marcadas


print("CAPTURA DO FOGO RELEVANTE, Amazonia 2021-2024 (sorteio capturaria o mesmo % das celulas)")
linhas = []
for nome, m in (("todas as semanas", np.ones(n_sem, bool)), ("temporada ago-out", PICO), ("resto do ano", ~PICO)):
    r = {"periodo": nome}
    for f in (0.05, 0.10, 0.20, 0.30):
        r[f"top {int(f * 100)}%"] = round(captura(m, f)[0], 1)
    linhas.append(r)
print(pd.DataFrame(linhas).set_index("periodo").to_string())

print("\nPOR ANO, top 10% das celulas: % do fogo relevante capturado")
print({int(a): round(captura(ANO == a, 0.10)[0], 1) for a in (2021, 2022, 2023, 2024)})

print("\nALARMES FALSOS no corte de 50% (por semana, na Amazonia inteira)")
av = P >= 0.5
fp = (av & ~Y).sum(axis=1)
tp = (av & Y).sum(axis=1)
print(f"  celulas avisadas por semana: {av.sum(axis=1).mean():.0f} de {CEL} ({av.mean() * 100:.1f}%)")
print(f"  avisos que se confirmaram: {tp.mean():.0f} por semana | alarmes falsos: {fp.mean():.0f} por semana (~{fp.mean() * 1770 / 1000:.0f} mil km2 avisados sem fogo relevante)")
print(f"  area total da Amazonia no recorte: ~{CEL * 1770 / 1000:.0f} mil km2; area avisada por semana: ~{av.sum(axis=1).mean() * 1770 / 1000:.0f} mil km2")

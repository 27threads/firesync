"""Validação do modelo de risco com área queimada da NASA (issue #107, RFC 0003): MCD64A1 v061, Amazônia, 2021 a 2024.

Pergunta: as faixas do mapa (muito alto, alto, médio, menor), calculadas só com dados anteriores, acompanham a área que
de fato queimou, medida por outro método? O modelo prevê detecções VIIRS a partir de detecções VIIRS. O MCD64A1 mapeia
área queimada pela mudança de reflectância do MODIS (outro método, outro sensor).

CRITÉRIO FIXADO ANTES DE RODAR (15/11/2026). Unidade: célula H3 res 4 (a mesma do banco) num domingo t de 2021 a 2024,
na Amazônia (bioma 1 do IBGE, pelo centro da célula). Modelo: o de `risco_celulas.py`, treinado só com anos anteriores ao
de t (um treino por ano), com a série do banco. Área queimada: soma dos pixels de 500 m do MCD64A1 com "Burn Date" em
t+1..t+14, a mesma janela do alvo do modelo.
  1. Em todos os anos testados, a área queimada média na faixa "muito alto" é maior que em "alto", que é maior que em
     "médio", que é maior que em "menor" (a ordem das 4 faixas se mantém).
  2. AUC da nota contra "área queimada >= 1 km² nos 14 dias seguintes" de pelo menos 0,80 na Amazônia.
Se o resultado contrariar o critério, ele é registrado assim mesmo. Sensibilidade: 0,5 e 5 km².
Também: a relação entre o alvo do modelo (10 ou mais detecções VIIRS) e a área queimada.

Vieses a vigiar: nuvem e fumaça mascaram a área queimada; queimas menores que ~25 ha quase não aparecem em 500 m; a data
de queima do MCD64A1 tem incerteza de alguns dias; células na divisa do bioma; semanas seguidas se sobrepõem (não são
independentes); o produto sai com meses de atraso (valida o passado, não a nota de hoje).

Uso (dentro de data-pipeline/; precisa de `pip install pyhdf` e de EARTHDATA_TOKEN no .env ou no ambiente):
    python validacao/area_queimada.py baixar       # 576 arquivos HDF (~2,4 GB) em data/raw/mcd64a1/
    python validacao/area_queimada.py processar    # área queimada por célula e dia -> relatorios/area_queimada/area.parquet
    python validacao/area_queimada.py avaliar      # compara com as notas do modelo -> relatorios/area_queimada/relatorio.txt
"""
import argparse
import json
import sys
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

import h3
import numpy as np
import pandas as pd

PASTA = Path(__file__).resolve().parent.parent  # data-pipeline/
sys.path.insert(0, str(PASTA))
from validacao import backtest_alerta as bt  # noqa: E402

# Grade senoidal do MODIS (blocos de 2400 x 2400 pixels de ~463 m)
RAIO = 6371007.181
X0, Y0 = -20015109.354, 10007554.677
BLOCO = 1111950.5197
PIXEL = BLOCO / 2400
PIXEL_KM2 = PIXEL * PIXEL / 1e6

BBOX = "-74,-18,-44,5.3"  # Amazônia brasileira, com folga
ANOS = [2021, 2022, 2023, 2024]
CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
DADOS = PASTA / "data" / "raw" / "mcd64a1"
SAIDA = PASTA / "relatorios" / "area_queimada"
SERIE = PASTA / "relatorios" / "serie" / "serie_banco_2026-11-14.parquet"
BIOMAS = PASTA / "data" / "raw" / "ibge" / "Biomas_250mil.zip"
LIMIARES_KM2 = (0.5, 1.0, 5.0)


def _faixas():
    regras = json.loads((PASTA.parent / "config" / "risk_rules.json").read_text(encoding="utf-8"))
    cortes = sorted(((t["tier"], t["min_prob"]) for t in regras["tiers"]), key=lambda t: -t[1])
    return [(nome, minimo, cortes[i - 1][1] if i else 1.01) for i, (nome, minimo) in enumerate(cortes)]


FAIXAS = _faixas()  # [(faixa, prob mínima, prob máxima)], da mais alta para a mais baixa, de config/risk_rules.json


# ---------------------------------------------------------------- pixels -> células

def centros_latlon(h, v, linhas, colunas):
    """Centro dos pixels (linha, coluna) do bloco hXXvYY em graus (inversa da projeção senoidal)."""
    x = X0 + h * BLOCO + (np.asarray(colunas) + 0.5) * PIXEL
    y = Y0 - v * BLOCO - (np.asarray(linhas) + 0.5) * PIXEL
    lat = y / RAIO
    return np.degrees(lat), np.degrees(x / (RAIO * np.cos(lat)))


def celula_res4(lat, lon):
    """Célula H3 res 4 como o banco faz: a mãe da célula res 6 do ponto (inteiro)."""
    res6 = np.array([h3.str_to_int(h3.latlng_to_cell(a, b, 6)) for a, b in zip(lat, lon)], dtype=np.int64)
    return (res6 & ~bt.MASCARA_RES) | bt.RES4 | bt.DIGITOS_5_6


def pixels_queimados(burn):
    """Linha, coluna e dia do ano dos pixels queimados. Burn Date: 0 não queimou, -1 sem dado, -2 água, 1..366 o dia."""
    linhas, colunas = np.nonzero((burn >= 1) & (burn <= 366))
    return linhas, colunas, burn[linhas, colunas].astype(int)


def area_por_celula_dia(unidades, datas):
    """Um pixel por elemento -> (unidade, data, km2)."""
    df = pd.DataFrame({"unidade": unidades, "data": datas})
    return df.groupby(["unidade", "data"]).size().mul(PIXEL_KM2).rename("km2").reset_index()


def matriz_area(df, unidades):
    """(unidade, data, km2) -> matriz na ordem de `unidades`, de bt.INICIO a bt.FIM. Fora da lista ou do período: ignora."""
    pos = {u: i for i, u in enumerate(unidades)}
    m = np.zeros((len(unidades), (bt.FIM - bt.INICIO).days + 1), np.float32)
    for u, d, km2 in zip(df["unidade"], df["data"], df["km2"]):
        j = (pd.Timestamp(d).date() - bt.INICIO).days
        if u in pos and 0 <= j < m.shape[1]:
            m[pos[u], j] += km2
    return m


def area_14_dias_seguintes(m, datas):
    """Área queimada em t+1..t+14 para cada domingo t: semana x unidade (a janela do alvo do modelo)."""
    s14 = bt.somas_moveis(m, bt.JANELA_GABARITO)
    return np.stack([s14[:, (t - bt.INICIO).days + bt.JANELA_GABARITO] for t in datas])


def media_por_faixa(prob, area, faixas):
    return {nome: float(area[(prob >= lo) & (prob < hi)].mean()) for nome, lo, hi in faixas}


def ordem_mantida(medias):
    """A área média cai de faixa em faixa (da mais alta para a mais baixa)."""
    valores = [medias[nome] for nome, _, _ in FAIXAS]
    return all(a > b for a, b in zip(valores, valores[1:]))


# ---------------------------------------------------------------- download e leitura

def granulos():
    """Arquivos do MCD64A1 v061 que cobrem a Amazônia de 2021 a 2024 (catálogo CMR da NASA, sem login)."""
    import requests

    saida, pagina = [], 1
    while True:
        q = {"short_name": "MCD64A1", "version": "061", "bounding_box": BBOX, "page_size": 2000, "page_num": pagina,
             "temporal": f"{ANOS[0]}-01-01T00:00:00Z,{ANOS[-1]}-12-31T23:59:59Z"}
        entradas = requests.get(CMR + "?" + urllib.parse.urlencode(q), timeout=120).json()["feed"]["entry"]
        saida += [(e["title"], float(e.get("granule_size", 0)), next(lk["href"] for lk in e["links"] if lk["href"].endswith(".hdf")))
                  for e in entradas]
        if len(entradas) < 2000:
            return saida
        pagina += 1


def baixar():
    import requests
    from pipeline import env

    token = env("EARTHDATA_TOKEN")
    DADOS.mkdir(parents=True, exist_ok=True)
    lista = granulos()
    print(f"{len(lista)} arquivos, {sum(s for _, s, _ in lista) / 1e3:.2f} GB")
    with requests.Session() as s:
        s.headers["Authorization"] = f"Bearer {token}"  # o requests não repassa o token no redirecionamento para o S3
        for i, (titulo, _, url) in enumerate(lista, 1):
            destino = DADOS / Path(urllib.parse.urlparse(url).path).name
            if destino.exists() and destino.stat().st_size > 0:
                continue
            parcial = destino.with_suffix(".part")
            with s.get(url, stream=True, timeout=300) as r:
                r.raise_for_status()
                with open(parcial, "wb") as f:
                    for bloco in r.iter_content(1 << 20):
                        f.write(bloco)
            parcial.replace(destino)
            print(f"  {i}/{len(lista)} {titulo}", flush=True)


def ler_burn_date(caminho):
    from pyhdf.SD import SD, SDC

    return SD(str(caminho), SDC.READ).select("Burn Date").get()


def processar():
    """Todos os HDF baixados -> área queimada por célula res 4 e dia."""
    partes = []
    arquivos = sorted(DADOS.glob("MCD64A1.A*.hdf"))
    for i, arq in enumerate(arquivos, 1):
        _, aaaaddd, bloco = arq.name.split(".")[:3]
        ano, h, v = int(aaaaddd[1:5]), int(bloco[1:3]), int(bloco[4:6])
        linhas, colunas, dias = pixels_queimados(ler_burn_date(arq))
        if len(dias):
            lat, lon = centros_latlon(h, v, linhas, colunas)
            datas = np.array([date(ano, 1, 1) + timedelta(int(d) - 1) for d in dias])
            partes.append(area_por_celula_dia(celula_res4(lat, lon), datas))
        if i % 48 == 0:
            print(f"  {i}/{len(arquivos)}", flush=True)
    area = pd.concat(partes).groupby(["unidade", "data"], as_index=False)["km2"].sum()
    SAIDA.mkdir(parents=True, exist_ok=True)
    area.to_parquet(SAIDA / "area.parquet", index=False)
    print(f"{len(arquivos)} arquivos -> {len(area):,} células-dia, {area.km2.sum():,.0f} km² queimados")


# ---------------------------------------------------------------- comparação com o modelo

def avaliar():
    import geopandas as gpd
    from sklearn.metrics import roc_auc_score

    import risco_celulas as rc
    from validacao import modelo_risco as mr

    df = pd.read_parquet(SERIE)
    df = df[pd.to_datetime(df["data"]) <= pd.Timestamp(bt.FIM)]
    serie = rc.preparar_serie(df, bt.FIM)
    unidades = serie["unidades"]
    amazonia = np.nan_to_num(mr.bioma_das_unidades(unidades, gpd.read_file(BIOMAS)), nan=0) == 1
    area = matriz_area(pd.read_parquet(SAIDA / "area.parquet"), unidades)
    fogo14 = bt.somas_moveis(serie["matriz"], bt.JANELA_GABARITO)
    P, A, Y, ANO = [], [], [], []
    for ano in ANOS:
        modelo = rc.treinar(df, date(ano - 1, 12, 31))["modelo"]  # só anos anteriores
        datas = [d for d in (date(ano, 1, 1) + timedelta(i) for i in range(366)) if d.year == ano and d.weekday() == 6
                 and d <= bt.ULTIMO_DOMINGO]
        x = mr.empilhar(rc.montar_pistas(serie, datas), (len(datas), len(unidades)))[:, amazonia, :]
        P.append(modelo.predict_proba(x.reshape(-1, x.shape[2]))[:, 1])
        A.append(area_14_dias_seguintes(area, datas)[:, amazonia].ravel())
        idx = np.array([(t - bt.INICIO).days + bt.JANELA_GABARITO for t in datas])
        Y.append((fogo14[:, idx].T >= 10)[:, amazonia].ravel())
        ANO.append(np.full(len(datas) * amazonia.sum(), ano))
        print(f"  {ano}: {len(datas)} domingos", flush=True)
    P, A, Y, ANO = (np.concatenate(v) for v in (P, A, Y, ANO))
    SAIDA.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"prob": P, "area_km2": A, "fogo_relevante": Y, "ano": ANO}).to_parquet(SAIDA / "notas.parquet", index=False)

    linhas = [f"Validação com área queimada (MCD64A1 v061), Amazônia, {ANOS[0]}-{ANOS[-1]}: {amazonia.sum()} células, "
              f"{len(P):,} células-domingo. Área queimada em t+1..t+14.", "",
              "1) Área queimada média (km²) por faixa do modelo, por ano. Critério: a ordem das 4 faixas se mantém."]
    passou = True
    for ano in ANOS + ["todos"]:
        k = ANO == ano if ano != "todos" else np.ones_like(Y)
        medias = media_por_faixa(P[k], A[k], FAIXAS)
        ok = ordem_mantida(medias)
        passou &= ok if ano != "todos" else True
        linhas.append(f"   {ano}: " + " | ".join(f"{n} {medias[n]:.2f}" for n, _, _ in FAIXAS) + f" | ordem {'mantida' if ok else 'QUEBRADA'}")
    linhas += ["", "2) AUC da nota contra 'área queimada >= X km² nos 14 dias seguintes' (critério: >= 0,80 com X = 1)"]
    for x in LIMIARES_KM2:
        alvo = A >= x
        por_ano = " ".join(f"{a}: {roc_auc_score(alvo[ANO == a], P[ANO == a]):.3f}" for a in ANOS)
        linhas.append(f"   X = {x} km²: {alvo.mean():.1%} das células-domingo | AUC {roc_auc_score(alvo, P):.3f} ({por_ano})")
    q = A >= 1.0
    linhas += ["", "3) O alvo do modelo (10 ou mais detecções VIIRS em 14 dias) e a área queimada (>= 1 km²)",
               f"   com fogo relevante: {q[Y].mean():.1%} tiveram área queimada | sem fogo relevante: {q[~Y].mean():.1%}",
               f"   com área queimada: {Y[q].mean():.1%} tiveram fogo relevante",
               "", f"CRITÉRIO 1 (ordem em todos os anos): {'PASSOU' if passou else 'NÃO PASSOU'} | "
               f"CRITÉRIO 2 (AUC >= 0,80 com 1 km²): {'PASSOU' if roc_auc_score(q, P) >= 0.80 else 'NÃO PASSOU'}"]
    texto = "\n".join(linhas)
    (SAIDA / "relatorio.txt").write_text(texto + "\n", encoding="utf-8")
    print(texto)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("etapa", choices=["baixar", "processar", "avaliar"])
    {"baixar": baixar, "processar": processar, "avaliar": avaliar}[ap.parse_args().etapa]()


if __name__ == "__main__":
    main()

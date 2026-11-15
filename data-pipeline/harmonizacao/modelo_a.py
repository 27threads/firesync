"""Modelo A (docs/rfcs/0002-modelo-a.md, caminho C): a chance de o MODIS (Aqua) ver um fogo que o VIIRS (S-NPP) viu.

O modelo NÃO converte a série do calendário (isso é o fator por contagens, calibrar.py). Ele entrega, para a tela de
Método, a curva de detecção (chance de o MODIS ver o fogo, por potência, de dia e de noite) e uma prova cruzada do
fator: o fator implícito no modelo comparado com o fator por contagens.

Passos:
  1. limpa os dois arquivos com as regras do pipeline.py (frente A), sem copiá-las, e atribui o bioma;
  2. forma os pares: para cada fogo do VIIRS, "o MODIS estava olhando" (há fogo do Aqua a até 50 km, na mesma data,
     no mesmo período e dentro da janela de horário) e "o MODIS viu" (um fogo do Aqua cobre o ponto: distância menor
     que metade do maior lado do pixel do MODIS mais metade do pixel do VIIRS). Só entram no treino os fogos em
     áreas que o MODIS estava olhando (ESCOLHA DA EQUIPE, com viés declarado no RFC);
  3. sorteia blocos H3 para treino e teste (semente fixa), de modo que fogos vizinhos não caiam dos dois lados;
  4. ajusta dois modelos no treino: a tabela por faixa de potência, período e bioma, e um gradient boosting;
  5. mede nos blocos de teste: separação (AUC), calibração e prova cruzada com o fator por contagens.

ATENÇÃO À JANELA DE HORÁRIO: a regra original (regras-variaveis.md, seção 4) pede até 10 minutos entre o Aqua e o
S-NPP. Isso vale quando o Aqua estava na órbita original (A-Train, até 2021). Em 2024 o Aqua passa cerca de 44
minutos (dia) e 63 minutos (noite) depois do S-NPP no mesmo lugar, e só 6% a 9% dos pares ficam dentro de 10
minutos. Por isso a janela é um parâmetro (--janela). Com janelas maiores, "viu" mistura a sensibilidade do sensor
com a mudança do fogo ao longo da hora que separa as duas passagens.

Uso (dentro de data-pipeline/), sem banco e sem gravar nada além da pasta de saída:
    python harmonizacao/modelo_a.py --modis modis.csv --viirs snpp.csv --biomas Biomas_250mil.zip --saida pasta
        [--janela 10] [--semente 42] [--bloco-res 4]

Saídas na pasta:
    curva_deteccao.csv   chance de o MODIS ver o fogo por faixa de potência, período e bioma (e "todos")
    medidas.csv          AUC, Brier e taxas, por modelo, nos blocos de teste
    calibracao.csv       chance prevista contra chance observada, em décimos, por modelo
    prova_cruzada.csv    fator do modelo (VIIRS por foco do MODIS) contra o fator por contagens
    relatorio_modelo_a.txt  resumo, com a janela usada
    curva_deteccao.png   (se o matplotlib estiver instalado) a curva para a tela de Método

Etapa B, corte no tempo (um ano de cada vez, para caber na memória): treina em alguns anos e mede em anos que o modelo
nunca viu, e mostra a curva de cada ano (a deriva do Aqua aparece aí):
    python harmonizacao/modelo_a.py --pasta firms/ --treino 2019 2020 2021 --teste 2022 2023 2024 --janela 90
        --biomas Biomas_250mil.zip --saida pasta [--cache pares/]
    A pasta tem modis_{ano}_Brazil.csv e viirs-snpp_{ano}_Brazil.csv (os arquivos anuais por país do FIRMS) ou, com os nomes
    que o `pipeline.py download` grava, modis_{ano}.csv e viirs-snpp_{ano}.csv (data/raw/country/). O --cache guarda os
    pares de cada ano e a segunda rodada não relê os CSV; ele só vale para os mesmos biomas, janela e regras de limpeza,
    e é refeito se algum deles mudar.
    medidas_por_ano.csv, calibracao_por_ano.csv, curva_por_ano.csv (e .png), totais_por_ano.csv, relatorio_temporal.txt
"""
import argparse
import sys
from pathlib import Path

import geopandas as gpd
import h3
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import clean_modis, clean_viirs, normalize  # noqa: E402  (as regras de limpeza são as da frente A)

RAIO_TERRA_KM = 6371.0088
PIXEL_VIIRS_KM = 0.375
OLHANDO_KM = 50.0          # ESCOLHA DA EQUIPE (regras-variaveis.md, seção 4)
JANELA_MINUTOS = 10        # regra original; em 2024 precisa ser maior (ver o topo do arquivo)
BLOCO_H3 = 4               # cerca de 1.770 km² por bloco. ESCOLHA DA EQUIPE
SEMENTE = 42
FAIXAS_FRP = [0.0, 2.0, 5.0, 10.0, 25.0, np.inf]   # em MW. ESCOLHA DA EQUIPE (RFC 0002)
ROTULOS_FAIXA = ["0-2", "2-5", "5-10", "10-25", "25+"]
BIOMAS = {1: "Amazônia", 2: "Caatinga", 3: "Cerrado", 4: "Mata Atlântica", 5: "Pampa", 6: "Pantanal"}
PISTAS = ["frp", "bright_ti4", "alta_confianca", "noite", "mes", "bioma", "modis_scan_mediano"]
NIVEIS_TABELA = [["faixa", "periodo", "bioma"], ["faixa", "periodo"], ["faixa"]]   # do mais fino ao mais geral


# ---------------------------------------------------------------- limpeza e biomas

def limpar_aqua(df):
    """Aqua com as regras do pipeline.py: só Aqua, type 0, FRP maior que zero, sem duplicata, confiança de 30 em diante."""
    principal, _baixa = clean_modis(normalize(df, "modis").query("satellite == 'Aqua'"), {})
    return principal


def limpar_snpp(df):
    """S-NPP com as regras do pipeline.py: type 0, FRP maior que zero, sem duplicata, confiança nominal e alta."""
    principal, _baixa = clean_viirs(normalize(df, "viirs"), {})
    return principal


def preparar_biomas(biomas):
    """GeoDataFrame do IBGE (coluna CD_Bioma) -> colunas bioma e geometry em WGS84."""
    return gpd.GeoDataFrame({"bioma": biomas["CD_Bioma"].map(BIOMAS)}, geometry=biomas.geometry.values,
                            crs=4326 if biomas.crs is None else biomas.crs).to_crs(4326)


def atribuir_bioma(df, biomas):
    """Põe a coluna bioma pelo ponto. Fogos fora dos biomas (mar, fronteira) saem."""
    pts = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["longitude"], df["latitude"]), crs=4326)
    j = gpd.sjoin(pts, biomas[["bioma", "geometry"]], predicate="within", how="inner")
    j = j[~j.index.duplicated(keep="first")]   # ponto exatamente na divisa fica no primeiro bioma
    return pd.DataFrame(j.drop(columns=["geometry", "index_right"]))


def preparar(df):
    """Minuto do dia em UTC e mês, a partir de acq_time (HHMM) e acq_date."""
    t = df["acq_time"].str.zfill(4)
    return df.assign(minuto=t.str[:2].astype(int) * 60 + t.str[2:].astype(int), mes=pd.to_datetime(df["acq_date"]).dt.month)


# ---------------------------------------------------------------- pares

def parear(snpp, aqua, janela=JANELA_MINUTOS):
    """Para cada fogo do S-NPP: `olhando`, `viu` e `modis_scan_mediano` (tamanho mediano dos pixels do Aqua a até 50 km).

    snpp: latitude, longitude, acq_date, daynight, minuto. aqua: o mesmo mais scan e track (em km).
    """
    from sklearn.neighbors import BallTree

    snpp = snpp.reset_index(drop=True)
    olhando = np.zeros(len(snpp), bool)
    viu = np.zeros(len(snpp), bool)
    scan_mediano = np.full(len(snpp), np.nan)
    aqua_por_passagem = dict(tuple(aqua.groupby(["acq_date", "daynight"])))
    for chave, gs in snpp.groupby(["acq_date", "daynight"]):
        ga = aqua_por_passagem.get(chave)
        if ga is None:
            continue
        arvore = BallTree(np.radians(ga[["latitude", "longitude"]].to_numpy()), metric="haversine")
        vizinhos, dist = arvore.query_radius(np.radians(gs[["latitude", "longitude"]].to_numpy()),
                                             r=OLHANDO_KM / RAIO_TERRA_KM, return_distance=True)
        n = np.fromiter((len(v) for v in vizinhos), dtype=int, count=len(vizinhos))
        if n.sum() == 0:
            continue
        i = np.repeat(np.arange(len(gs)), n)
        j = np.concatenate(vizinhos)
        d_km = np.concatenate(dist) * RAIO_TERRA_KM
        mesma_passagem = np.abs(ga["minuto"].to_numpy()[j] - gs["minuto"].to_numpy()[i]) <= janela
        i, j, d_km = i[mesma_passagem], j[mesma_passagem], d_km[mesma_passagem]
        lado = np.maximum(ga["scan"].to_numpy()[j], ga["track"].to_numpy()[j])
        dentro = d_km <= lado / 2 + PIXEL_VIIRS_KM / 2
        posicao = gs.index.to_numpy()
        olhando[posicao[np.unique(i)]] = True
        viu[posicao[np.unique(i[dentro])]] = True
        mediano = pd.Series(ga["scan"].to_numpy()[j]).groupby(i).median()
        scan_mediano[posicao[mediano.index.to_numpy()]] = mediano.to_numpy()
    return snpp.assign(olhando=olhando, viu=viu, modis_scan_mediano=scan_mediano)


# ---------------------------------------------------------------- blocos de treino e de teste

def atribuir_bloco(df, resolucao=BLOCO_H3):
    return df.assign(bloco=[h3.latlng_to_cell(la, lo, resolucao) for la, lo in zip(df["latitude"], df["longitude"])])


def sortear_blocos(blocos, semente=SEMENTE):
    """Metade dos blocos H3 vai para o teste, com semente fixa (o mesmo sorteio sempre)."""
    unicos = np.unique(blocos.to_numpy())
    return set(np.random.default_rng(semente).permutation(unicos)[: len(unicos) // 2])


# ---------------------------------------------------------------- modelos

def faixa_frp(frp):
    return pd.cut(frp, FAIXAS_FRP, labels=ROTULOS_FAIXA, right=False)


def ajustar_tabela(treino, minimo=30):
    """Chance de detecção por faixa de potência, período e bioma, com níveis mais gerais quando há poucos fogos."""
    niveis = []
    for cols in NIVEIS_TABELA:
        t = treino.groupby(cols, observed=True)["viu"].agg(p="mean", n="size").reset_index()
        niveis.append((cols, t[t["n"] >= minimo][cols + ["p"]]))
    return {"niveis": niveis, "global": float(treino["viu"].mean())}


def prever_tabela(tabela, df):
    p = pd.Series(np.nan, index=df.index)
    for cols, t in tabela["niveis"]:
        achado = df[cols].merge(t, on=cols, how="left")["p"].to_numpy()
        p = p.fillna(pd.Series(achado, index=df.index))
    return p.fillna(tabela["global"])


def pistas(df, biomas):
    return pd.DataFrame({
        "frp": df["frp"].to_numpy(), "bright_ti4": df["bright_ti4"].to_numpy(),
        "alta_confianca": df["high_conf"].astype(int).to_numpy(), "noite": (df["daynight"] == "N").astype(int).to_numpy(),
        "mes": df["mes"].to_numpy(), "bioma": pd.Categorical(df["bioma"], categories=biomas),
        "modis_scan_mediano": df["modis_scan_mediano"].to_numpy()})[PISTAS]


def ajustar_boosting(treino, biomas, semente=SEMENTE):
    from sklearn.ensemble import HistGradientBoostingClassifier

    modelo = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, categorical_features="from_dtype",
                                            random_state=semente)
    return modelo.fit(pistas(treino, biomas), treino["viu"].astype(int))


def prever_boosting(modelo, df, biomas):
    return pd.Series(modelo.predict_proba(pistas(df, biomas))[:, 1], index=df.index)


# ---------------------------------------------------------------- medidas

def medir(y, p):
    """Separação (AUC, 1 é perfeito e 0,5 é sorteio), erro quadrático das chances (Brier) e as taxas."""
    from sklearn.metrics import brier_score_loss, roc_auc_score

    y = y.astype(int)
    auc = roc_auc_score(y, p) if y.nunique() == 2 else np.nan
    return {"auc": auc, "brier": brier_score_loss(y, p), "taxa_observada": float(y.mean()), "taxa_prevista": float(p.mean())}


def calibracao(y, p, modelo):
    """Chance prevista contra chance observada, em décimos das previsões."""
    faixas = pd.qcut(p, 10, duplicates="drop")
    t = pd.DataFrame({"p": p, "y": y.astype(int)}).groupby(faixas, observed=True).agg(
        prevista=("p", "mean"), observada=("y", "mean"), n=("y", "size")).reset_index(drop=True)
    return t.assign(modelo=modelo)


def prova_cruzada(snpp, aqua, coluna_p, chaves, snpp_todos):
    """Fator do modelo (fogos do VIIRS por foco do MODIS que ele espera) contra o fator por contagens.

    snpp: fogos do VIIRS em áreas olhadas, nos blocos de teste, com a chance prevista em `coluna_p` e as `chaves`.
    aqua: fogos do Aqua nos mesmos blocos, com as mesmas `chaves`.
    snpp_todos: todos os fogos do VIIRS dos blocos de teste (olhados ou não), com as mesmas `chaves`.

    O CSV expõe os dois fatores por contagens: `fator_contagens` na mesma população do modelo (só os olhados, e é
    com ele que a razão é calculada) e `fator_contagens_total` com todos os fogos do VIIRS, que é o da série.
    """
    esperado = snpp.groupby(chaves, observed=True).agg(n_viirs=(coluna_p, "size"), esperado_modis=(coluna_p, "sum")).reset_index()
    contados = aqua.groupby(chaves, observed=True).size().rename("n_modis").reset_index()
    total = snpp_todos.groupby(chaves, observed=True).size().rename("n_viirs_total").reset_index()
    t = esperado.merge(contados, on=chaves, how="left").merge(total, on=chaves, how="left").fillna({"n_modis": 0})
    n_modis = t["n_modis"].where(t["n_modis"] > 0)
    t["fator_modelo"] = t["n_viirs"] / t["esperado_modis"].where(t["esperado_modis"] > 0)
    t["fator_contagens"] = t["n_viirs"] / n_modis
    t["fator_contagens_total"] = t["n_viirs_total"] / n_modis
    t["razao_modelo_contagens"] = t["fator_modelo"] / t["fator_contagens"]
    return t


# ---------------------------------------------------------------- execução

def executar(aqua_bruto, snpp_bruto, biomas, janela=JANELA_MINUTOS, semente=SEMENTE, bloco_res=BLOCO_H3, minimo_tabela=30):
    """Roda os cinco passos. Devolve DataFrames (curva, medidas, calibracao, prova, grupos) e o texto do relatório."""
    aqua = preparar(atribuir_bioma(limpar_aqua(aqua_bruto), biomas))
    snpp = preparar(atribuir_bioma(limpar_snpp(snpp_bruto), biomas))
    snpp = atribuir_bloco(parear(snpp, aqua, janela), bloco_res)
    aqua = atribuir_bloco(aqua, bloco_res)
    teste_blocos = sortear_blocos(pd.concat([aqua["bloco"], snpp["bloco"]]), semente)
    snpp["grupo"] = np.where(snpp["bloco"].isin(teste_blocos), "teste", "treino")
    aqua["grupo"] = np.where(aqua["bloco"].isin(teste_blocos), "teste", "treino")

    base = snpp[snpp["olhando"]].assign(periodo=lambda d: d["daynight"], faixa=lambda d: faixa_frp(d["frp"]))
    treino, teste = base[base["grupo"] == "treino"], base[base["grupo"] == "teste"].copy()
    lista_biomas = sorted(biomas["bioma"].dropna().unique())
    tabela = ajustar_tabela(treino, minimo_tabela)
    boosting = ajustar_boosting(treino, lista_biomas, semente)
    teste["p_referencia"] = float(treino["viu"].mean())
    teste["p_tabela"] = prever_tabela(tabela, teste)
    teste["p_boosting"] = prever_boosting(boosting, teste, lista_biomas)

    modelos = {"referencia": "p_referencia", "tabela": "p_tabela", "boosting": "p_boosting"}
    medidas = pd.DataFrame([{"modelo": nome, **medir(teste["viu"], teste[col])} for nome, col in modelos.items()])
    calib = pd.concat([calibracao(teste["viu"], teste[col], nome) for nome, col in modelos.items() if nome != "referencia"])

    por_bioma = base.groupby(["bioma", "periodo", "faixa"], observed=True)["viu"].agg(taxa_viu="mean", n="size").reset_index()
    todos = base.groupby(["periodo", "faixa"], observed=True)["viu"].agg(taxa_viu="mean", n="size").reset_index().assign(bioma="todos")
    curva = pd.concat([todos, por_bioma], ignore_index=True)[["bioma", "periodo", "faixa", "taxa_viu", "n"]]

    snpp_teste = snpp[snpp["grupo"] == "teste"].assign(periodo=lambda d: d["daynight"])
    aqua_teste = aqua[aqua["grupo"] == "teste"].assign(periodo=lambda d: d["daynight"])
    esperado = teste.assign(p=teste["p_boosting"])
    prova = pd.concat([
        prova_cruzada(esperado, aqua_teste, "p", ["bioma", "periodo"], snpp_teste).assign(mes=np.nan),
        prova_cruzada(esperado, aqua_teste, "p", ["bioma", "periodo", "mes"], snpp_teste),
    ], ignore_index=True)

    relatorio = "\n".join([
        "Modelo A (RFC 0002): chance de o MODIS (Aqua) ver um fogo do VIIRS (S-NPP)",
        f"janela de horário entre os sensores: {janela} minutos | área olhada: {OLHANDO_KM:.0f} km | blocos H3 de resolução {bloco_res}",
        f"fogos do S-NPP limpos: {len(snpp):,} | em áreas que o MODIS olhava: {int(snpp['olhando'].sum()):,} "
        f"({snpp['olhando'].mean():.1%}) | vistos pelo MODIS: {int(snpp['viu'].sum()):,} ({base['viu'].mean():.1%} dos olhados)",
        f"fogos do Aqua limpos: {len(aqua):,} | treino: {len(treino):,} | teste: {len(teste):,}",
        "", "Medidas nos blocos de teste (AUC: 1 é perfeito, 0,5 é sorteio; Brier: menor é melhor)",
        medidas.round(4).to_string(index=False)])
    return {"curva": curva, "medidas": medidas, "calibracao": calib, "prova": prova,
            "grupos": snpp[["grupo"]], "relatorio": relatorio}


# ---------------------------------------------------------------- etapa B: corte no tempo, ano a ano

COLUNAS_OLHADAS = ["acq_date", "daynight", "frp", "bright_ti4", "high_conf", "mes", "bioma", "modis_scan_mediano", "viu",
                   "olhando"]


def preparar_ano(aqua_bruto, snpp_bruto, biomas, janela=JANELA_MINUTOS):
    """Um ano inteiro: limpa, atribui o bioma e forma os pares. Guarda só os fogos olhados e os totais do ano.

    É o que cabe na memória: cada ano é processado sozinho (o resto do código só precisa dos fogos olhados).
    """
    aqua = preparar(atribuir_bioma(limpar_aqua(aqua_bruto), biomas))
    snpp = preparar(atribuir_bioma(limpar_snpp(snpp_bruto), biomas))
    if snpp.empty:
        raise ValueError("sem fogos do S-NPP depois da limpeza")
    snpp = parear(snpp, aqua, janela)
    olhados = snpp.loc[snpp["olhando"], COLUNAS_OLHADAS].reset_index(drop=True)
    olhados["acq_date"] = olhados["acq_date"].astype(str)
    ano = int(snpp["acq_date"].astype(str).str[:4].mode().iloc[0])
    totais = {"ano": ano, "snpp": int(len(snpp)), "aqua": int(len(aqua)), "olhando": int(len(olhados)),
              "viram": int(olhados["viu"].sum()), "janela": int(janela)}
    return {"olhados": olhados, "totais": totais}


def _base_do_ano(pares, anos):
    d = pd.concat([pares[a]["olhados"] for a in anos], ignore_index=True)
    return d.assign(periodo=d["daynight"], faixa=faixa_frp(d["frp"]))


def executar_temporal(pares, anos_treino, anos_teste, biomas, semente=SEMENTE, minimo_tabela=30):
    """Treina nos anos de treino e mede em cada ano de teste, que o modelo nunca viu (corte no tempo).

    pares: {ano: resultado de preparar_ano}. Devolve DataFrames (medidas, calibracao, curva_por_ano, totais_por_ano)
    e o texto do relatório. Mostra se a curva e o modelo valem em anos novos, ou se a deriva do Aqua atrapalha.
    """
    if set(anos_treino) & set(anos_teste):
        raise ValueError(f"anos em treino e teste ao mesmo tempo: {sorted(set(anos_treino) & set(anos_teste))}")
    faltam = sorted((set(anos_treino) | set(anos_teste)) - set(pares))
    if faltam:
        raise ValueError(f"sem dados para os anos {faltam}")
    treino = _base_do_ano(pares, sorted(anos_treino))
    lista_biomas = sorted(biomas["bioma"].dropna().unique())
    tabela = ajustar_tabela(treino, minimo_tabela)
    boosting = ajustar_boosting(treino, lista_biomas, semente)
    medidas, calib = [], []
    for ano in sorted(anos_teste):
        teste = _base_do_ano(pares, [ano])
        if teste.empty:
            raise ValueError(f"sem dados: o ano {ano} não tem fogos em áreas que o MODIS olhava")
        previsoes = {"referencia": pd.Series(float(treino["viu"].mean()), index=teste.index),
                     "tabela": prever_tabela(tabela, teste), "boosting": prever_boosting(boosting, teste, lista_biomas)}
        for nome, p in previsoes.items():
            medidas.append({"ano": ano, "modelo": nome, "n": int(len(teste)), **medir(teste["viu"], p)})
            if nome != "referencia":
                calib.append(calibracao(teste["viu"], p, nome).assign(ano=ano))
    curvas = []
    for ano in sorted(set(anos_treino) | set(anos_teste)):
        base = _base_do_ano(pares, [ano])
        por_bioma = base.groupby(["bioma", "periodo", "faixa"], observed=True)["viu"].agg(taxa_viu="mean", n="size").reset_index()
        todos = base.groupby(["periodo", "faixa"], observed=True)["viu"].agg(taxa_viu="mean", n="size").reset_index().assign(bioma="todos")
        curvas.append(pd.concat([todos, por_bioma], ignore_index=True).assign(ano=ano))
    curva_por_ano = pd.concat(curvas, ignore_index=True)[["ano", "bioma", "periodo", "faixa", "taxa_viu", "n"]]
    totais = pd.DataFrame([{**pares[a]["totais"], "papel": "treino" if a in anos_treino else "teste"}
                           for a in sorted(set(anos_treino) | set(anos_teste))])
    medidas = pd.DataFrame(medidas)
    janelas = sorted(totais["janela"].unique())
    relatorio = "\n".join([
        "Modelo A, etapa B (RFC 0002): corte no tempo. O modelo treina nos anos de treino e é medido em anos que nunca viu",
        f"treino: {sorted(anos_treino)} | teste: {sorted(anos_teste)} | janela de horário: {', '.join(map(str, janelas))} minutos"
        f" | área olhada: {OLHANDO_KM:.0f} km",
        f"fogos olhados no treino: {len(treino):,} | vistos pelo MODIS: {treino['viu'].mean():.1%}",
        "", "Totais por ano (snpp e aqua: fogos limpos; olhando: fogos em áreas que o MODIS olhava; viram: os que ele viu)",
        totais.to_string(index=False),
        "", "Medidas por ano de teste (AUC: 1 é perfeito, 0,5 é sorteio; Brier: menor é melhor;"
        " taxa prevista contra observada mostra se a deriva do Aqua desalinha o modelo)",
        medidas.round(4).to_string(index=False)])
    return {"medidas": medidas, "calibracao": pd.concat(calib, ignore_index=True), "curva_por_ano": curva_por_ano,
            "totais_por_ano": totais, "relatorio": relatorio}


def grafico_por_ano(curva_por_ano, saida):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return "matplotlib não instalado: gráfico por ano não gerado (a curva está no CSV)."
    todos = curva_por_ano[curva_por_ano["bioma"] == "todos"]
    fig, eixos = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for eixo, (periodo, titulo) in zip(eixos, (("D", "Day"), ("N", "Night"))):
        for ano, g in todos[todos["periodo"] == periodo].groupby("ano"):
            g = g.set_index("faixa").reindex(ROTULOS_FAIXA)
            eixo.plot(ROTULOS_FAIXA, g["taxa_viu"] * 100, marker="o", label=str(ano))
        eixo.set_title(titulo)
        eixo.set_xlabel("Fire radiative power of the VIIRS detection (MW)")
        eixo.set_ylim(0, 100)
    eixos[0].set_ylabel("Chance that MODIS also sees the fire (%)")
    com_curvas = next((e for e in eixos if e.get_legend_handles_labels()[0]), None)
    if com_curvas is not None:
        com_curvas.legend(frameon=False, title="Year")
    fig.tight_layout()
    fig.savefig(saida / "curva_por_ano.png", dpi=130)
    plt.close(fig)
    return "Gráfico: curva_por_ano.png"


def chave_do_cache(biomas, janela):
    """Identifica com o que os pares foram feitos: os biomas, a janela, as regras do pareamento e o código da limpeza.

    Se qualquer um mudar, o cache velho não vale (e não é reaproveitado em silêncio).
    """
    import hashlib
    import inspect

    h = hashlib.sha256()
    h.update(b"".join(biomas.geometry.to_wkb()))
    h.update("|".join(map(str, biomas["bioma"])).encode())
    h.update(f"|{janela}|{OLHANDO_KM}|{PIXEL_VIIRS_KM}".encode())
    for funcao in (normalize, clean_modis, clean_viirs):
        h.update(inspect.getsource(funcao).encode())
    return h.hexdigest()


def arquivo_do_ano(pasta, fonte, ano):
    """Acha o CSV anual do FIRMS: `{fonte}_{ano}_Brazil.csv` (download manual) ou `{fonte}_{ano}.csv` (o do `pipeline.py download`)."""
    for nome in (f"{fonte}_{ano}_Brazil.csv", f"{fonte}_{ano}.csv"):
        if (Path(pasta) / nome).exists():
            return Path(pasta) / nome
    raise FileNotFoundError(f"{fonte}_{ano}_Brazil.csv ou {fonte}_{ano}.csv não está em {pasta}")


def pares_do_ano(pasta, ano, biomas, janela, cache=None):
    """Lê os CSV do ano e forma os pares, ou lê o cache (só se ele foi feito com os mesmos biomas, janela e regras)."""
    import json

    import pyarrow as pa
    import pyarrow.parquet as pq

    arquivo = Path(cache) / f"pares_{ano}_j{janela}.parquet" if cache else None
    chave = chave_do_cache(biomas, janela).encode()
    if arquivo is not None and arquivo.exists():
        tabela = pq.read_table(arquivo)
        if (tabela.schema.metadata or {}).get(b"chave") == chave:
            return {"olhados": tabela.to_pandas(), "totais": json.loads(tabela.schema.metadata[b"totais"])}
    tipos = {"acq_time": str, "version": str, "confidence": str}
    r = preparar_ano(pd.read_csv(arquivo_do_ano(pasta, "modis", ano), dtype=tipos),
                     pd.read_csv(arquivo_do_ano(pasta, "viirs-snpp", ano), dtype=tipos), biomas, janela)
    if arquivo is not None:
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        tabela = pa.Table.from_pandas(r["olhados"], preserve_index=False)
        pq.write_table(tabela.replace_schema_metadata({**(tabela.schema.metadata or {}), b"totais": json.dumps(r["totais"]).encode(),
                                                       b"chave": chave}), arquivo)
    return r


def grafico(curva, saida):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return "matplotlib não instalado: gráfico não gerado (a curva está no CSV)."
    todos = curva[curva["bioma"] == "todos"]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for periodo, cor, rotulo in (("D", "#00204d", "Day"), ("N", "#c9a900", "Night")):
        g = todos[todos["periodo"] == periodo].set_index("faixa").reindex(ROTULOS_FAIXA)
        ax.plot(ROTULOS_FAIXA, g["taxa_viu"] * 100, marker="o", color=cor, label=rotulo)
    ax.set_xlabel("Fire radiative power of the VIIRS detection (MW)")
    ax.set_ylabel("Chance that MODIS also sees the fire (%)")
    ax.set_title("Detection curve: how often MODIS sees what VIIRS sees")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(saida / "curva_deteccao.png", dpi=130)
    plt.close(fig)
    return "Gráfico: curva_deteccao.png"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modis", help="CSV do Archive Download (MODIS: Terra e Aqua juntos)")
    ap.add_argument("--viirs", help="CSV do Archive Download (VIIRS S-NPP)")
    ap.add_argument("--biomas", required=True, help="Biomas do IBGE (zip ou GeoJSON, com a coluna CD_Bioma)")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--janela", type=int, default=JANELA_MINUTOS)
    ap.add_argument("--semente", type=int, default=SEMENTE)
    ap.add_argument("--bloco-res", type=int, default=BLOCO_H3)
    ap.add_argument("--pasta", help="etapa B: pasta com modis_{ano}_Brazil.csv e viirs-snpp_{ano}_Brazil.csv, um por ano")
    ap.add_argument("--treino", type=int, nargs="+", help="etapa B: anos de treino")
    ap.add_argument("--teste", type=int, nargs="+", help="etapa B: anos de teste (nunca vistos no treino)")
    ap.add_argument("--cache", help="etapa B: pasta onde guardar os pares de cada ano, para não refazer")
    a = ap.parse_args()

    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    if a.pasta:
        if not a.treino or not a.teste:
            ap.error("--pasta pede --treino e --teste")
        biomas = preparar_biomas(gpd.read_file(a.biomas))
        pares = {ano: pares_do_ano(a.pasta, ano, biomas, a.janela, a.cache) for ano in sorted(set(a.treino) | set(a.teste))}
        r = executar_temporal(pares, a.treino, a.teste, biomas, a.semente)
        r["medidas"].to_csv(saida / "medidas_por_ano.csv", index=False)
        r["calibracao"].to_csv(saida / "calibracao_por_ano.csv", index=False)
        r["curva_por_ano"].to_csv(saida / "curva_por_ano.csv", index=False)
        r["totais_por_ano"].to_csv(saida / "totais_por_ano.csv", index=False)
        texto = r["relatorio"] + "\n\n" + grafico_por_ano(r["curva_por_ano"], saida)
        (saida / "relatorio_temporal.txt").write_text(texto, encoding="utf-8")
        print(texto)
        return
    if not a.modis or not a.viirs:
        ap.error("sem --pasta, --modis e --viirs são obrigatórios")
    tipos = {"acq_time": str, "version": str, "confidence": str}
    r = executar(pd.read_csv(a.modis, dtype=tipos), pd.read_csv(a.viirs, dtype=tipos),
                 preparar_biomas(gpd.read_file(a.biomas)), a.janela, a.semente, a.bloco_res)
    r["curva"].to_csv(saida / "curva_deteccao.csv", index=False)
    r["medidas"].to_csv(saida / "medidas.csv", index=False)
    r["calibracao"].to_csv(saida / "calibracao.csv", index=False)
    r["prova"].to_csv(saida / "prova_cruzada.csv", index=False)
    texto = r["relatorio"] + "\n\n" + grafico(r["curva"], saida)
    (saida / "relatorio_modelo_a.txt").write_text(texto, encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()

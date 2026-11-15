"""Modelo de risco (RFC 0003): a chance de "muito fogo" nos 14 dias seguintes, por célula H3 res 4. Não usa o banco.

Alvo: o gabarito do backtest do alerta (RFC 0001, backtest_alerta.py), sem mudar nada nele: os 14 dias t+1..t+14
acima do P90 do normal e com pelo menos 10 detecções. O modelo é comparado com a v1 do alerta (piso contínuo, a
regra que vai para a tela), com a regra antiga (piso só na mediana zero, referência histórica) e com a regra
ingênua, sempre com o MESMO número de alertas em cada ano.

Pistas (todas só com dias até o domingo t):
  fogo    detecções em 7, 14 e 30 dias, tendência, potência (FRP) em 7 dias, células vizinhas, os 14 dias seguintes
          à mesma data no ano anterior e na média dos anos anteriores, semana do ano, posição e bioma da célula;
  oni     índice El Niño/La Niña (NOAA CPC), da última estação já publicada (termina 2 meses antes). Só como
          comparação (--oni): na primeira rodada ele piorou o modelo, e o clima não parte dele;
  clima   chuva em 30 e 90 dias, dias secos, temperatura máxima, umidade e vento em 7 dias (NASA POWER).

Validação em avanço: para cada ano de teste, treina só com as semanas cujo gabarito termina antes daquele ano.
O --ano-final fica fora de qualquer escolha e é rodado uma vez, no fim.

Uso (dentro de data-pipeline/):
    python validacao/modelo_risco.py --viirs viirs-snpp_2012_Brazil.csv ... --gravar-serie serie.parquet
    python validacao/modelo_risco.py --serie serie.parquet --oni oni.ascii.txt [--clima pasta] [--biomas Biomas.zip]
        --saida relatorios/risco [--anos-teste 2017 ... 2023] [--ano-final 2024]

Saídas na pasta --saida:
    medidas_por_ano.csv   acerto do modelo, da regra e da ingênua, AUC e precisão média, por conjunto de pistas e ano
    importancia.csv       quanto cada pista pesa no ano final (queda da precisão média ao embaralhar a pista)
    relatorio.txt         resumo
"""
import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

import h3
import numpy as np
import pandas as pd

PASTA = Path(__file__).resolve().parent.parent  # data-pipeline/
sys.path.insert(0, str(PASTA))
from pipeline import clean_viirs, normalize  # noqa: E402  (as regras de limpeza são as da frente A)
from validacao import backtest_alerta as bt  # noqa: E402

RES = 4
SEMENTE = 42
ESTACOES = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
ATRASO_ONI_MESES = 2      # a estação que termina no mês m sai no começo de m+1; com 2 meses ela já está publicada
DIA_SECO_MM = 1.0         # ESCOLHA DA EQUIPE: dia com menos de 1 mm de chuva conta como seco
CLIMA = {"PRECTOTCORR": "chuva", "T2M_MAX": "tmax7", "RH2M": "umid7", "WS2M": "vento7"}
ANOS_TESTE = list(range(2017, 2024))
ANO_FINAL = 2024
TIPOS = {"acq_time": str, "version": str, "confidence": str}


# ---------------------------------------------------------------- série diária

def serie_diaria(viirs_bruto):
    """CSV do Archive Download (VIIRS S-NPP) -> detecções e FRP somado por célula H3 res 4 e dia, com a limpeza
    do pipeline.py: type 0, FRP maior que zero, sem duplicata, confiança nominal e alta."""
    limpo, _baixa = clean_viirs(normalize(viirs_bruto, "viirs"), {})
    unidade = [h3.str_to_int(h3.latlng_to_cell(la, lo, RES)) for la, lo in zip(limpo["latitude"], limpo["longitude"])]
    d = pd.DataFrame({"unidade": unidade, "data": limpo["acq_date"].astype(str).str[:10].to_numpy(),
                      "frp": limpo["frp"].to_numpy(float)})
    return d.groupby(["unidade", "data"]).agg(n=("frp", "size"), frp=("frp", "sum")).reset_index()


def matrizes(df):
    """(unidade, data, n, frp) -> (unidades, contagem, FRP), matrizes unidade x dia de INICIO a FIM do backtest."""
    datas = pd.to_datetime(df["data"])
    df = df[(datas >= pd.Timestamp(bt.INICIO)) & (datas <= pd.Timestamp(bt.FIM))]
    unidades, u = np.unique(df["unidade"].to_numpy(), return_inverse=True)
    d = (pd.to_datetime(df["data"]) - pd.Timestamp(bt.INICIO)).dt.days.to_numpy()
    forma = (len(unidades), (bt.FIM - bt.INICIO).days + 1)
    m_n, m_frp = np.zeros(forma, np.float32), np.zeros(forma, np.float32)
    np.add.at(m_n, (u, d), df["n"].to_numpy(np.float32))
    np.add.at(m_frp, (u, d), df["frp"].to_numpy(np.float32))
    return unidades, m_n, m_frp


def vizinhos(unidades):
    """Pares (linha, coluna): para cada unidade (linha), as células H3 ao lado que existem na série (coluna)."""
    posicao = {int(u): j for j, u in enumerate(unidades)}
    linhas, colunas = [], []
    for u, j in posicao.items():
        celula = h3.int_to_str(u)
        for v in h3.grid_disk(celula, 1):
            k = posicao.get(h3.str_to_int(v))
            if v != celula and k is not None:
                linhas.append(j)
                colunas.append(k)
    return np.array(linhas, int), np.array(colunas, int)


def posicao_das_unidades(unidades):
    centros = np.array([h3.cell_to_latlng(h3.int_to_str(int(u))) for u in unidades], np.float32)
    return centros[:, 0], centros[:, 1]


def bioma_das_unidades(unidades, biomas):
    """Código do bioma (coluna CD_Bioma do IBGE) no centro de cada célula. Fora dos biomas = NaN."""
    import geopandas as gpd

    lat, lon = posicao_das_unidades(unidades)
    pts = gpd.GeoDataFrame({"j": np.arange(len(unidades))}, geometry=gpd.points_from_xy(lon, lat), crs=4326)
    j = gpd.sjoin(pts, biomas.to_crs(4326)[["CD_Bioma", "geometry"]], predicate="within", how="left")
    j = j[~j.index.duplicated(keep="first")]
    return pd.to_numeric(j["CD_Bioma"], errors="coerce").to_numpy(np.float32)


# ---------------------------------------------------------------- pistas

def pistas_fogo(m_n, m_frp, semanas, viz):
    """Pistas do histórico de fogo, semana x unidade. Nenhuma usa dias depois do domingo t."""
    s3, s7, s14, s30 = (bt.somas_moveis(m_n, k) for k in (3, 7, 14, 30))
    f7 = bt.somas_moveis(m_frp, 7)
    linhas, colunas = viz
    forma = (len(semanas), m_n.shape[0])
    p = {c: np.full(forma, np.nan, np.float32)
         for c in ("s7", "s14", "s30", "tendencia", "frp7", "viz7", "ano_anterior", "normal_passado")}
    for w, t in enumerate(semanas):
        i = (t - bt.INICIO).days
        p["s7"][w], p["s14"][w], p["s30"][w], p["frp7"][w] = s7[:, i], s14[:, i], s30[:, i], f7[:, i]
        p["tendencia"][w] = s3[:, i] - s3[:, i - 3]
        soma_viz = np.zeros(m_n.shape[0], np.float32)
        np.add.at(soma_viz, linhas, s7[colunas, i])
        p["viz7"][w] = soma_viz
        # os 14 dias seguintes à mesma data (t+1..t+14) nos anos anteriores: 364 dias = 52 semanas exatas
        passados = [k for k in range(i + bt.JANELA_GABARITO - 364, bt.JANELA_GABARITO - 2, -364)]
        if passados:
            p["ano_anterior"][w] = s14[:, passados[0]]
            p["normal_passado"][w] = s14[:, passados].mean(axis=1)
    return p


def ler_oni(caminho):
    """oni.ascii.txt da NOAA CPC (SEAS YR TOTAL ANOM) -> DataFrame com o último mês da estação (ano*12 + mês-1)."""
    t = pd.read_csv(caminho, sep=r"\s+")
    centro = t["SEAS"].map({s: k + 1 for k, s in enumerate(ESTACOES)})   # DJF tem centro em janeiro, NDJ em dezembro
    return pd.DataFrame({"fim": t["YR"] * 12 + centro, "anom": t["ANOM"].astype(float)}).sort_values("fim")


def pista_oni(oni, semanas):
    """O ONI da última estação que termina até 2 meses antes do mês de t (já publicada naquele dia)."""
    limite = np.array([t.year * 12 + t.month - 1 - ATRASO_ONI_MESES for t in semanas])
    k = np.searchsorted(oni["fim"].to_numpy(), limite, side="right") - 1
    return np.where(k >= 0, oni["anom"].to_numpy()[np.clip(k, 0, None)], np.nan).astype(np.float32)


def clima_por_unidade(pasta, unidades):
    """Parquets do NASA POWER (VAR_ANO.parquet: LAT, LON, YEAR, DOY, VAR) -> {VAR: matriz unidade x dia}.

    Cada célula recebe o ponto da grade do POWER mais perto do seu centro. Dia sem dado (-999) vira NaN.
    """
    lat, lon = posicao_das_unidades(unidades)
    n_dias = (bt.FIM - bt.INICIO).days + 1
    clima = {}
    for var in CLIMA:
        arquivos = sorted(Path(pasta).glob(f"{var}_*.parquet"))
        if not arquivos:
            continue
        m = np.full((len(unidades), n_dias), np.nan, np.float32)
        for arq in arquivos:
            g = pd.read_parquet(arq)
            g = g[g[var] > -900]
            dia = (pd.to_datetime(g["YEAR"].astype(str), format="%Y") + pd.to_timedelta(g["DOY"] - 1, unit="D")
                   - pd.Timestamp(bt.INICIO)).dt.days.to_numpy()
            g = g.assign(dia=dia)[(dia >= 0) & (dia < n_dias)]
            lats, lons = np.sort(g["LAT"].unique()), np.sort(g["LON"].unique())
            grade = np.full((len(lats), len(lons), n_dias), np.nan, np.float32)
            grade[np.searchsorted(lats, g["LAT"]), np.searchsorted(lons, g["LON"]), g["dia"]] = g[var].to_numpy()
            i = np.abs(lats[None, :] - lat[:, None]).argmin(axis=1)
            j = np.abs(lons[None, :] - lon[:, None]).argmin(axis=1)
            dias = np.unique(g["dia"])
            m[:, dias] = grade[i, j][:, dias]
        clima[var] = m
    return clima


def pistas_clima(clima, semanas):
    """Pistas do clima, semana x unidade, só com dias até o domingo t. clima: {variável do POWER: unidade x dia}."""
    prontas = {}
    if "PRECTOTCORR" in clima:
        chuva = clima["PRECTOTCORR"]
        prontas.update(chuva30=bt.somas_moveis(chuva, 30), chuva90=bt.somas_moveis(chuva, 90),
                       dias_secos30=bt.somas_moveis((chuva < DIA_SECO_MM).astype(np.float32), 30))
    for var in ("T2M_MAX", "RH2M", "WS2M"):
        if var in clima:
            prontas[CLIMA[var]] = bt.somas_moveis(clima[var], 7) / 7
    dias = [(t - bt.INICIO).days for t in semanas]
    p = {nome: s[:, dias].T.copy() for nome, s in prontas.items()}
    for nome in ("chuva30", "chuva90", "tmax7", "umid7"):   # o valor em relação ao normal da região e da época
        if nome in p:
            p[f"{nome}_anom"] = anomalia(p[nome])
    return p


def anomalia(x):
    """Semana x unidade -> o valor menos a média das mesmas semanas dos anos ANTERIORES (NaN no primeiro ano).

    Um ano atrás são round(365,25 / 7) = 52 semanas, dois anos 104, três 157 (o ano não tem semanas inteiras).
    Só olha para trás: o valor de uma semana nunca depende de semanas depois dela.
    """
    soma, n = np.zeros(x.shape, np.float64), np.zeros(x.shape, np.int32)
    for k in range(1, len(x) // 52 + 1):
        d = round(k * 365.25 / 7)
        if d >= len(x):
            break
        soma[d:] += np.nan_to_num(x[:-d])
        n[d:] += ~np.isnan(x[:-d])
    media = np.where(n > 0, soma / np.maximum(n, 1), np.nan)
    return (x - media).astype(np.float32)


# ---------------------------------------------------------------- modelo e medidas

def ajustar(x, y, categoricas, semente):
    from sklearn.ensemble import HistGradientBoostingClassifier

    modelo = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, random_state=semente,
                                            categorical_features=list(categoricas) or None)
    return modelo.fit(x, y)


def os_k_maiores(valor, k):
    alerta = np.zeros(valor.size, bool)
    if k:
        alerta[np.argpartition(-valor, k - 1)[:k]] = True
    return alerta


def acerto_com_k_alertas(y, p, score, k):
    """Acerto do modelo e da ingênua quando cada um dá exatamente k alertas."""
    if not k:
        return np.nan, np.nan
    return float(y[os_k_maiores(p, k)].mean()), float(y[os_k_maiores(score, k)].mean())


def medidas_ano(y, p, critico, score, critico_continuo=None):
    """Acerto do modelo, da regra (Crítico) e da ingênua com o mesmo número de alertas; AUC e precisão média.

    Com `critico_continuo` (a regra do piso contínuo, escolhida em 15/11/2026, que dá menos alertas), mede também o
    modelo e a ingênua com o número de alertas dela. É a comparação mais difícil de bater.
    """
    from sklearn.metrics import average_precision_score, roc_auc_score

    y = np.asarray(y, bool)
    k = int(critico.sum())
    modelo, ingenua = acerto_com_k_alertas(y, p, score, k)
    regra = float(y[critico].mean()) if k else np.nan
    duas_classes = y.any() and not y.all()
    r = {"semanas_unidade": int(y.size), "prevalencia": float(y.mean()), "alertas": k,
         "acerto_modelo": modelo, "acerto_regra": regra, "acerto_ingenua": ingenua,
         "ganho_sobre_regra": modelo - regra, "ganho_sobre_ingenua": modelo - ingenua,
         "auc": float(roc_auc_score(y, p)) if duas_classes else np.nan,
         "precisao_media": float(average_precision_score(y, p)) if duas_classes else np.nan}
    if critico_continuo is not None:
        k2 = int(critico_continuo.sum())
        modelo2, ingenua2 = acerto_com_k_alertas(y, p, score, k2)
        regra2 = float(y[critico_continuo].mean()) if k2 else np.nan
        r.update(alertas_continua=k2, acerto_regra_continua=regra2, acerto_modelo_k_continua=modelo2,
                 acerto_ingenua_k_continua=ingenua2, ganho_sobre_regra_continua=modelo2 - regra2)
    return r


def empilhar(pistas, forma):
    """{nome: semana x unidade, ou um valor por semana, ou um valor por unidade} -> array semana x unidade x pista."""
    x = np.empty((*forma, len(pistas)), np.float32)
    for f, v in enumerate(pistas.values()):
        v = np.asarray(v, np.float32)
        x[:, :, f] = v if v.ndim == 2 else (v[:, None] if v.size == forma[0] else v[None, :])
    return x


def cortes(semanas, ano):
    """Semanas de treino (o gabarito termina antes do ano) e de teste (domingos do ano)."""
    fim = np.array([(t + timedelta(bt.JANELA_GABARITO)).year for t in semanas])
    return fim < ano, np.array([t.year for t in semanas]) == ano


def validar_em_avanco(pistas, gab, semanas, critico, score, anos_teste, categoricas=(), semente=SEMENTE,
                      critico_continuo=None):
    """Uma linha por ano de teste. O modelo de cada ano só vê semanas cujo gabarito termina antes daquele ano."""
    x = empilhar(pistas, gab.shape)
    cat = [list(pistas).index(c) for c in categoricas]
    linhas = []
    for ano in anos_teste:
        treino, teste = cortes(semanas, ano)
        modelo = ajustar(x[treino].reshape(-1, x.shape[2]), gab[treino].ravel(), cat, semente)
        p = modelo.predict_proba(x[teste].reshape(-1, x.shape[2]))[:, 1]
        continua = None if critico_continuo is None else critico_continuo[teste].ravel()
        linhas.append({"ano": ano, **medidas_ano(gab[teste].ravel(), p, critico[teste].ravel(), score[teste].ravel(), continua)})
    return pd.DataFrame(linhas)


def importancia(pistas, gab, semanas, ano, categoricas=(), semente=SEMENTE, amostra=200_000):
    """Queda da precisão média no ano de teste ao embaralhar cada pista (quanto maior, mais a pista pesa)."""
    from sklearn.inspection import permutation_importance

    x = empilhar(pistas, gab.shape)
    treino, teste = cortes(semanas, ano)
    modelo = ajustar(x[treino].reshape(-1, x.shape[2]), gab[treino].ravel(), [list(pistas).index(c) for c in categoricas], semente)
    xt, yt = x[teste].reshape(-1, x.shape[2]), gab[teste].ravel()
    if len(yt) > amostra:
        escolha = np.random.default_rng(semente).choice(len(yt), amostra, replace=False)
        xt, yt = xt[escolha], yt[escolha]
    r = permutation_importance(modelo, xt, yt, scoring="average_precision", n_repeats=3, random_state=semente)
    return pd.DataFrame({"pista": list(pistas), "queda_precisao_media": r.importances_mean}).sort_values(
        "queda_precisao_media", ascending=False)


# ---------------------------------------------------------------- execução

def relatorio(medidas, imp, ano_final):
    cols = ["acerto_modelo", "acerto_regra", "acerto_ingenua", "ganho_sobre_regra", "ganho_sobre_ingenua", "auc", "precisao_media"]
    continua = ["alertas_continua", "acerto_modelo_k_continua", "acerto_regra_continua", "acerto_ingenua_k_continua",
                "ganho_sobre_regra_continua"]
    tem_continua = continua[0] in medidas
    avanco = medidas[medidas["papel"] == "avanco"]
    media = avanco.groupby("conjunto", sort=False)[cols].mean().round(4)
    ganhou = avanco.assign(g=avanco["ganho_sobre_regra"] > 0).groupby("conjunto", sort=False)["g"].agg(["sum", "size"])
    final = medidas[medidas["papel"] == "final"].set_index("conjunto")[cols].round(4)
    texto = [
        "Modelo de risco (RFC 0003): chance de muito fogo nos 14 dias seguintes, células H3 res 4.",
        f"Alvo: gabarito do backtest (P{bt.GABARITO[0]} do normal e >= {bt.GABARITO[1]} detecções em 14 dias).",
        "Acerto = parte dos alertas seguida de muito fogo. Modelo, regra e ingênua dão o MESMO número de alertas por ano.",
        "", "Validação em avanço (média dos anos de teste; cada ano treinado só com os anteriores). "
        "Aqui 'regra' é a regra ANTIGA (piso só na mediana zero); a v1 vem mais abaixo:", media.to_string(),
        "", "Anos de teste em que o modelo ganha da regra:",
        "\n".join(f"  {c}: {int(r['sum'])} de {int(r['size'])}" for c, r in ganhou.iterrows()),
        "", f"Ano final ({ano_final}), rodado uma vez, fora de qualquer escolha:", final.to_string()]
    if tem_continua:
        texto += ["", "Contra a regra do piso contínuo (a v1 escolhida; menos alertas, o modelo e a ingênua usam o número dela):",
                  "média dos anos de teste:", avanco.groupby("conjunto", sort=False)[continua].mean().round(4).to_string(),
                  f"ano final ({ano_final}):", medidas[medidas["papel"] == "final"].set_index("conjunto")[continua].round(4).to_string()]
    return "\n".join(texto + ["", "Pistas que mais pesam no ano final (queda da precisão média ao embaralhar):",
                              imp.head(12).round(4).to_string(index=False)])


def ler_serie(caminho):
    caminho = Path(caminho)
    return pd.read_parquet(caminho) if caminho.suffix == ".parquet" else pd.read_csv(caminho)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--viirs", nargs="+", help="CSVs anuais do Archive Download (VIIRS S-NPP), para montar a série")
    ap.add_argument("--gravar-serie", type=Path, help="grava a série diária montada de --viirs e termina")
    ap.add_argument("--serie", help="série diária já montada (parquet ou CSV: unidade, data, n, frp)")
    ap.add_argument("--oni", help="oni.ascii.txt da NOAA CPC")
    ap.add_argument("--clima", help="pasta com os parquets do NASA POWER")
    ap.add_argument("--biomas", help="biomas do IBGE (zip ou GeoJSON, com a coluna CD_Bioma)")
    ap.add_argument("--regras", type=Path, default=PASTA.parent / "config" / "alert_rules.json")
    ap.add_argument("--saida", type=Path, default=PASTA / "relatorios" / "risco")
    ap.add_argument("--anos-teste", type=int, nargs="+", default=ANOS_TESTE)
    ap.add_argument("--ano-final", type=int, default=ANO_FINAL)
    a = ap.parse_args()

    if a.viirs:
        partes = [serie_diaria(pd.read_csv(arq, dtype=TIPOS)) for arq in a.viirs]   # um ano de cada vez, por memória
        serie = pd.concat(partes).groupby(["unidade", "data"], as_index=False).sum()
        a.gravar_serie.parent.mkdir(parents=True, exist_ok=True)
        serie.to_parquet(a.gravar_serie, index=False)
        print(f"série diária: {len(serie):,} linhas, {serie['unidade'].nunique():,} células, {int(serie['n'].sum()):,} detecções")
        return

    regra = json.loads(a.regras.read_text(encoding="utf-8"))
    unidades, m_n, m_frp = matrizes(ler_serie(a.serie))
    semanas, av = bt.avaliar(m_n, regra)
    gab = bt.gabarito(av, *bt.GABARITO)
    crit = regra["levels"]["critical"]
    # regra antiga (piso só onde a mediana é zero), só como referência histórica; a v1 é a de piso contínuo
    critico = bt.nivel(av, crit["min_ratio_to_median"], crit["requires_rising_trend"],
                       regra["levels"]["attention"]["above_percentile"], crit["min_detections"]) == 2
    critico_continuo = bt.nivel_da_regra(av, regra) == 2

    lat, lon = posicao_das_unidades(unidades)
    fogo = {**pistas_fogo(m_n, m_frp, semanas, vizinhos(unidades)),
            "semana_do_ano": np.array([t.isocalendar()[1] for t in semanas]), "lat": lat, "lon": lon}
    categoricas = []
    if a.biomas:
        import geopandas as gpd

        fogo["bioma"] = bioma_das_unidades(unidades, gpd.read_file(a.biomas))
        categoricas = ["bioma"]
    conjuntos = {"fogo": fogo}
    if a.oni:
        conjuntos["fogo+oni"] = {**fogo, "oni": pista_oni(ler_oni(a.oni), semanas)}
    if a.clima:  # o clima parte das pistas de fogo, sem o ONI (que não ajudou: RFC 0003)
        clima = pistas_clima(clima_por_unidade(a.clima, unidades), semanas)
        conjuntos["fogo+anomalia"] = {**fogo, **{k: v for k, v in clima.items() if k.endswith("_anom")}}
        conjuntos["fogo+clima"] = {**fogo, **clima}       # o último conjunto é o da importância das pistas

    partes = []
    for nome, pistas in conjuntos.items():
        r = validar_em_avanco(pistas, gab, semanas, critico, av["score"], [*a.anos_teste, a.ano_final], categoricas,
                           critico_continuo=critico_continuo)
        partes.append(r.assign(conjunto=nome, papel=np.where(r["ano"] == a.ano_final, "final", "avanco")))
        print(f"{nome}: pronto", flush=True)
    medidas = pd.concat(partes, ignore_index=True)
    completo = list(conjuntos)[-1]
    imp = importancia(conjuntos[completo], gab, semanas, a.ano_final, categoricas).assign(conjunto=completo)

    a.saida.mkdir(parents=True, exist_ok=True)
    medidas.to_csv(a.saida / "medidas_por_ano.csv", index=False)
    imp.to_csv(a.saida / "importancia.csv", index=False)
    texto = relatorio(medidas, imp, a.ano_final)
    (a.saida / "relatorio.txt").write_text(texto + "\n", encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()

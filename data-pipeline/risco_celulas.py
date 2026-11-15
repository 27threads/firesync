"""Risco por célula (RFC 0003, decisão de 15/11/2026): o modelo treinado de "onde vai ter fogo nos próximos 14 dias".

Para cada célula H3 de resolução 4 (cerca de 1.770 km²), calcula a chance de ela ter fogo relevante (10 ou mais detecções
do VIIRS) nos 14 dias seguintes, e a faixa de risco dessa chance (muito alto, alto, médio ou menor, em
config/risk_rules.json). O cálculo roda aqui, fora da API; a API só lê a tabela `risco_celulas`.

Modelo: gradient boosting (scikit-learn) com 10 variáveis, todas da contagem diária de detecções por célula
(`agregados_diarios`): fogo de 7, 14 e 30 dias, tendência, fogo nas células vizinhas, o que aconteceu na mesma época em
anos anteriores, semana do ano e posição. Reaproveita as funções testadas do experimento (validacao/modelo_risco.py).
Treino sempre só com semanas cujos 14 dias seguintes já terminaram até o fim dos dados.

Uso (dentro de data-pipeline/):
    python risco_celulas.py --gravar                       # banco: treina, pontua a data mais recente coberta e grava
    python risco_celulas.py --serie serie.parquet --data-ref 2020-07-19 --saida pasta
        # arquivo (unidade, data, n): treina só com o que existia até a data e grava risco_celulas.csv, modelo e relatório
"""
import argparse
import io
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import h3
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from validacao import backtest_alerta as bt  # noqa: E402
from validacao import modelo_risco as mr  # noqa: E402

FEATURES = ["s7", "s14", "s30", "tendencia", "viz7", "ano_anterior", "normal_passado", "semana", "lat", "lon"]
HORIZONTE, MINIMO = bt.JANELA_GABARITO, 10
LINHAS_TREINO = 1_200_000
SEMENTE = 42
CAMINHO_REGRAS = ROOT.parent / "config" / "risk_rules.json"
SQL_SERIE = f"""COPY (
SELECT ((h3 & ~{bt.MASCARA_RES}::bigint) | {bt.RES4 | bt.DIGITOS_5_6}::bigint) AS unidade, data, sum(focos_brutos) AS n
FROM agregados_diarios WHERE data >= '{bt.INICIO}' GROUP BY 1, 2) TO STDOUT WITH CSV HEADER"""


def carregar_regras(caminho=CAMINHO_REGRAS):
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def faixa_de(prob, regras):
    """Faixa de risco de uma chance: o primeiro corte (do maior para o menor) que ela alcança."""
    for t in sorted(regras["tiers"], key=lambda t: -t["min_prob"]):
        if prob >= t["min_prob"]:
            return t["tier"]
    return regras["tiers"][-1]["tier"]


# ---------------------------------------------------------------- série e variáveis

def preparar_serie(df, fim):
    """(unidade, data, n) -> {unidades, matriz unidade x dia de INICIO até `fim`, fim}. Dia sem linha = 0 detecções."""
    df = df[pd.to_datetime(df["data"]) <= pd.Timestamp(fim)]
    unidades, u = np.unique(df["unidade"].to_numpy(), return_inverse=True)
    d = (pd.to_datetime(df["data"]) - pd.Timestamp(bt.INICIO)).dt.days.to_numpy()
    matriz = np.zeros((len(unidades), (fim - bt.INICIO).days + 1), np.float32)
    np.add.at(matriz, (u, d), df["n"].to_numpy(np.float32))
    return {"unidades": unidades, "matriz": matriz, "fim": fim}


def montar_pistas(serie, datas):
    """Variáveis do modelo, semana x unidade, só com dias até cada data (nenhuma olha o futuro)."""
    unidades, m = serie["unidades"], serie["matriz"]
    p = mr.pistas_fogo(m, np.zeros_like(m), datas, mr.vizinhos(unidades))
    lat, lon = mr.posicao_das_unidades(unidades)
    forma = (len(datas), len(unidades))
    p.update(semana=np.repeat(np.array([d.isocalendar()[1] for d in datas], np.float32)[:, None], forma[1], 1),
             lat=np.tile(lat, (forma[0], 1)), lon=np.tile(lon, (forma[0], 1)))
    return {k: p[k] for k in FEATURES}


def domingos_de_treino(serie):
    """Domingos cujos 14 dias seguintes já terminaram até o fim dos dados."""
    ultimo = (serie["fim"] - bt.INICIO).days
    t, saida = bt.PRIMEIRO_DOMINGO, []
    while (t - bt.INICIO).days + HORIZONTE <= ultimo:
        saida.append(t)
        t += timedelta(weeks=1)
    return saida


# ---------------------------------------------------------------- treino e nota

def treinar(df, fim, semente=SEMENTE, max_linhas=LINHAS_TREINO):
    """Treina com os dados até `fim`. Devolve {modelo, features, treinado_ate, n_linhas, versao}."""
    serie = preparar_serie(df, fim)
    datas = domingos_de_treino(serie)
    if not datas:
        raise ValueError("sem semanas para treinar: os dados terminam cedo demais")
    dias = np.array([(t - bt.INICIO).days for t in datas])
    alvo = (bt.somas_moveis(serie["matriz"], HORIZONTE)[:, dias + HORIZONTE].T >= MINIMO)
    x = mr.empilhar(montar_pistas(serie, datas), alvo.shape)
    linhas = x.reshape(-1, x.shape[2])
    y = alvo.ravel()
    if len(y) > max_linhas:
        escolha = np.random.default_rng(semente).choice(len(y), max_linhas, replace=False)
        linhas, y = linhas[escolha], y[escolha]
    modelo = mr.ajustar(linhas, y, [], semente)
    return {"modelo": modelo, "features": list(FEATURES), "fim": fim, "n_linhas": int(len(y)),
            "versao": f"gb-{fim.isoformat()}-s{semente}"}


def pontuar(modelo, df, data_ref, regras=None):
    """Nota de cada célula na `data_ref`, só com dias até ela. Devolve DataFrame h3, prob, faixa."""
    regras = regras or carregar_regras()
    serie = preparar_serie(df, data_ref)
    x = mr.empilhar(montar_pistas(serie, [data_ref]), (1, len(serie["unidades"])))[0]
    prob = modelo["modelo"].predict_proba(x)[:, 1]
    return pd.DataFrame({"h3": serie["unidades"], "prob": prob, "faixa": [faixa_de(p, regras) for p in prob]})


# ---------------------------------------------------------------- banco

def serie_do_banco(conn):
    with conn.cursor().copy(SQL_SERIE) as cp:
        return pd.read_csv(io.BytesIO(b"".join(bytes(b) for b in cp)))


def data_de_referencia(conn, agora):
    """Último dia coberto pelo VIIRS, nunca depois do relógio (não depende de ter havido focos nesse dia)."""
    linha = conn.execute("SELECT least(max(data_fim), %s::date) FROM cobertura WHERE satelite IN ('SNPP', 'N20') AND data_inicio <= %s",
                         (agora.date(), agora.date())).fetchone()
    if linha[0] is None:
        raise SystemExit("sem cobertura do VIIRS no banco: nada a pontuar")
    return linha[0]


def gravar(conn, notas, data_ref, versao):
    """Grava (ou atualiza) as notas da data, numa transação só. Devolve quantas linhas."""
    calculado = datetime.now(timezone.utc)
    linhas = [(int(h), data_ref, float(p), f, versao, calculado) for h, p, f in zip(notas["h3"], notas["prob"], notas["faixa"])]
    with conn.transaction():
        conn.cursor().executemany(
            "INSERT INTO risco_celulas (h3, data_ref, prob, faixa, modelo_versao, calculado_em) VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (h3, data_ref) DO UPDATE SET prob = EXCLUDED.prob, faixa = EXCLUDED.faixa, "
            "modelo_versao = EXCLUDED.modelo_versao, calculado_em = EXCLUDED.calculado_em", linhas)
    return len(linhas)


# ---------------------------------------------------------------- execução

def relatorio(modelo, notas, data_ref, regras):
    contagem = notas["faixa"].value_counts().reindex([t["tier"] for t in regras["tiers"]]).fillna(0).astype(int)
    taxa = regras.get("historical_share", {})
    linhas = [f"Risco por célula (RFC 0003): chance de fogo relevante (>= {MINIMO} detecções) nos próximos {HORIZONTE} dias",
              f"data de referência: {data_ref} | treinado com dados até {modelo['fim']} (nada depois dela) | "
              f"{modelo['n_linhas']:,} linhas | modelo {modelo['versao']}",
              f"variáveis: {', '.join(modelo['features'])}", f"regras {regras['version']} | células pontuadas: {len(notas)}", "",
              "Células por faixa (e com que frequência a faixa teve fogo relevante nos 14 dias seguintes, no passado):"]
    linhas += [f"  {faixa:10s} {n:6d} células" + (f" | taxa histórica {taxa[faixa]:.0%}" if faixa in taxa else "") for faixa, n in contagem.items()]
    return "\n".join(linhas)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gravar", action="store_true", help="usa o banco (DATABASE_URL): treina, pontua e grava em risco_celulas")
    ap.add_argument("--serie", help="arquivo parquet ou CSV (unidade, data, n), em vez do banco")
    ap.add_argument("--data-ref", help="data a pontuar (AAAA-MM-DD); só com --serie. O treino usa só o que existia até ela")
    ap.add_argument("--saida", type=Path, help="pasta de saída (com --serie)")
    ap.add_argument("--regras", type=Path, default=CAMINHO_REGRAS)
    ap.add_argument("--semente", type=int, default=SEMENTE)
    a = ap.parse_args()
    regras = carregar_regras(a.regras)

    if a.serie:
        if not a.data_ref or not a.saida:
            ap.error("--serie pede --data-ref e --saida")
        df = pd.read_parquet(a.serie) if a.serie.endswith(".parquet") else pd.read_csv(a.serie)
        data_ref = date.fromisoformat(a.data_ref)
        modelo = treinar(df, data_ref, a.semente)       # só o que existia até a data: nada depois dela
        notas = pontuar(modelo, df, data_ref, regras)
        a.saida.mkdir(parents=True, exist_ok=True)
        saida = notas.assign(h3_texto=[h3.int_to_str(int(h)) for h in notas["h3"]], data_ref=data_ref.isoformat(),
                             modelo_versao=modelo["versao"])[["h3", "h3_texto", "data_ref", "prob", "faixa", "modelo_versao"]]
        saida.to_csv(a.saida / "risco_celulas.csv", index=False)
        import joblib
        joblib.dump(modelo, a.saida / "modelo_risco.joblib")
        texto = relatorio(modelo, notas, data_ref, regras)
        (a.saida / "relatorio_risco.txt").write_text(texto, encoding="utf-8")
        print(texto)
        return
    if not a.gravar:
        ap.error("use --gravar (banco) ou --serie (arquivo)")
    from pipeline import db
    conn = db()
    agora = datetime.now(timezone.utc)
    data_ref = data_de_referencia(conn, agora)
    df = serie_do_banco(conn)
    modelo = treinar(df, data_ref, a.semente)
    notas = pontuar(modelo, df, data_ref, regras)
    n = gravar(conn, notas, data_ref, modelo["versao"])
    print(relatorio(modelo, notas, data_ref, regras))
    print(f"\n{n} células gravadas em risco_celulas para {data_ref}.")


if __name__ == "__main__":
    main()

"""B6. Compara a série harmonizada do firesync com a série mensal do INPE (Programa Queimadas).

Os valores absolutos não batem por construção: o firesync está na escala do VIIRS, e o INPE conta na escala de um
satélite só (o Aqua, "AQUA_M-T"). O que precisa bater é a FORMA da série. Medidas, por bioma:

  - correlação mensal e anual entre as duas séries (Pearson e Spearman);
  - os 5 anos com mais fogo em cada série, e quantos coincidem;
  - o mês de pico de cada ano: em quantos anos coincide (com tolerância de 1 mês);
  - a sazonalidade média (perfil dos 12 meses, normalizado);
  - o DEGRAU EM 2012: razão anual firesync / INPE antes (2003-2011) e depois (2013 em diante) da troca de satélite.
    O INPE usa o Aqua o tempo todo; o firesync troca de Aqua x fator para o VIIRS observado em fev/2012.
    Se a harmonização funciona, a razão fica estável e o degrau fica perto de zero.

Uso (dentro de data-pipeline/):
    python harmonizacao/validar_inpe.py --saida relatorios/b6                     # lê o banco (agregados + fatores)
    python harmonizacao/validar_inpe.py --serie serie.csv --saida pasta           # sem banco, a partir da série exportada

Opções:
    --inpe CAMINHO     CSV do INPE (padrão: referencia/inpe_mensal_biomas.csv). Usa só satelite = AQUA_M-T e
                       parcial = false quando essas colunas existem (PR #21).
    --ate ANO          último ano completo comparado (padrão 2025)

Saídas na pasta --saida:
    serie_firesync_vs_inpe.csv   bioma, ano, mes, firesync (valor central), band_low, band_high, origem, inpe
    metricas_b6.csv              as medidas acima, por bioma
    relatorio_b6.txt             resumo
    grafico_<bioma>.png          (se o matplotlib estiver instalado) totais anuais, razão por ano e sazonalidade
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from calibrar import FAIXA  # noqa: E402  (mesmos percentis da API e da calibração)

ANO_INICIO = 2003
INICIO_VIIRS = (2012, 2)  # fev/2012: primeiro mês observado pelo VIIRS
TOLERANCIA_PICO = 1       # meses

SQL_AGREGADOS = """
SELECT r.nome AS bioma, a.ano, a.mes, a.satelite, a.periodo, sum(a.focos_brutos) AS focos
FROM agregados a JOIN regioes r ON r.id = a.regiao_id
WHERE a.ano >= %(ini)s AND a.ano <= %(fim)s
GROUP BY 1, 2, 3, 4, 5
"""
SQL_FATORES = """
SELECT r.nome AS bioma, f.mes, f.periodo, f.ano_calibracao, f.fator
FROM fatores_harmonizacao f JOIN regioes r ON r.id = f.regiao_id
WHERE f.satelite_origem = 'Aqua' AND f.satelite_destino = 'SNPP'
"""


# ---------------------------------------------------------------- série harmonizada

def harmonizar(contagens, fatores):
    """Mesma conta da API (importacao-regioes.md, "Fórmula do calendário"), no bioma inteiro.

    contagens: bioma, ano, mes, satelite, periodo, focos (só o satélite do mês, como em agregados)
    fatores:   bioma, mes, periodo, ano_calibracao, fator
    """
    f = fatores.pivot_table(index=["bioma", "mes", "periodo"], columns="ano_calibracao", values="fator")
    linhas = []
    for (bioma, ano, mes), g in contagens.groupby(["bioma", "ano", "mes"]):
        observado = (ano, mes) >= INICIO_VIIRS
        if observado:
            linhas.append((bioma, ano, mes, float(g["focos"].sum()), np.nan, np.nan, "observado_viirs"))
            continue
        e = None
        for _, r in g.iterrows():
            chave = (bioma, mes, r["periodo"])
            if chave not in f.index:
                continue
            parcela = r["focos"] * f.loc[chave]  # um valor por cenário
            # soma simples: cenário sem fator num período com focos vira vazio e sai (mesma regra do calibrar.py)
            e = parcela if e is None else e + parcela
        if e is None or e.dropna().empty:
            linhas.append((bioma, ano, mes, 0.0, 0.0, 0.0, "estimado_modis"))
            continue
        e = e.dropna().to_numpy()
        linhas.append((bioma, ano, mes, float(np.median(e)), float(np.percentile(e, FAIXA[0])),
                       float(np.percentile(e, FAIXA[1])), "estimado_modis"))
    return pd.DataFrame(linhas, columns=["bioma", "ano", "mes", "firesync", "band_low", "band_high", "origem"])


def serie_do_banco(ate):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from pipeline import db
    conn = db()
    cont = pd.DataFrame(conn.execute(SQL_AGREGADOS, {"ini": ANO_INICIO, "fim": ate}).fetchall(),
                        columns=["bioma", "ano", "mes", "satelite", "periodo", "focos"])
    fat = pd.DataFrame(conn.execute(SQL_FATORES).fetchall(),
                       columns=["bioma", "mes", "periodo", "ano_calibracao", "fator"])
    if fat.empty:
        sys.exit("fatores_harmonizacao está vazia: rode a calibração (calibrar.py --gravar) antes")
    return harmonizar(cont, fat)


def ler_inpe(caminho, ate):
    d = pd.read_csv(caminho)
    if "satelite" in d.columns:
        d = d[d["satelite"] == "AQUA_M-T"]
    if "parcial" in d.columns:
        d = d[~d["parcial"].astype(str).str.lower().isin(["true", "1"])]
    d = d[(d["ano"] >= ANO_INICIO) & (d["ano"] <= ate)]
    return d[["bioma", "ano", "mes", "focos"]].rename(columns={"focos": "inpe"})


# ---------------------------------------------------------------- comparação

def comparar(s):
    """s: bioma, ano, mes, firesync, inpe (só meses presentes nas duas séries). Uma linha de medidas por bioma."""
    linhas = []
    for bioma, g in s.groupby("bioma"):
        g = g.sort_values(["ano", "mes"])
        anual = g.groupby("ano")[["firesync", "inpe"]].sum()
        anual = anual[g.groupby("ano").size().reindex(anual.index) == 12]  # só anos completos
        top_f = set(anual["firesync"].nlargest(5).index)
        top_i = set(anual["inpe"].nlargest(5).index)
        pico = g.loc[g.groupby("ano")["firesync"].idxmax(), ["ano", "mes"]].set_index("ano")["mes"]
        pico_i = g.loc[g.groupby("ano")["inpe"].idxmax(), ["ano", "mes"]].set_index("ano")["mes"]
        dif = (pico - pico_i.reindex(pico.index)).abs()
        dif = np.minimum(dif, 12 - dif)  # dezembro e janeiro são vizinhos
        saz_f = g.groupby("mes")["firesync"].mean()
        saz_i = g.groupby("mes")["inpe"].mean()
        razao = (anual["firesync"] / anual["inpe"]).replace([np.inf, -np.inf], np.nan)
        antes = razao[(razao.index >= ANO_INICIO) & (razao.index <= 2011)].mean()
        depois = razao[razao.index >= 2013].mean()
        linhas.append({
            "bioma": bioma,
            "meses": len(g),
            "anos_completos": len(anual),
            "corr_mensal_pearson": g["firesync"].corr(g["inpe"]),
            # Spearman = Pearson dos postos (sem depender do scipy, que não está no requirements)
            "corr_mensal_spearman": g["firesync"].rank().corr(g["inpe"].rank()),
            "corr_anual_pearson": anual["firesync"].corr(anual["inpe"]),
            "top5_anos_firesync": " ".join(map(str, sorted(top_f))),
            "top5_anos_inpe": " ".join(map(str, sorted(top_i))),
            "top5_em_comum": len(top_f & top_i),
            "pico_igual_tolerancia_1_mes": float((dif <= TOLERANCIA_PICO).mean()),
            "corr_sazonalidade": saz_f.corr(saz_i),
            "razao_media_2003_2011": antes,
            "razao_media_2013_em_diante": depois,
            "degrau_2012": depois / antes - 1 if antes else np.nan,
        })
    return pd.DataFrame(linhas)


def graficos(s, saida, biomas):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return "matplotlib não instalado: gráficos não gerados (a série e as medidas estão nos CSVs)."
    feitos = []
    for bioma in biomas:
        g = s[s["bioma"] == bioma]
        if g.empty:
            continue
        anual = g.groupby("ano")[["firesync", "inpe", "band_low", "band_high"]].sum(min_count=1)
        fig, ax = plt.subplots(1, 3, figsize=(16, 4.5))
        a = ax[0]
        a.plot(anual.index, anual["firesync"], color="#00204d", label="firesync (VIIRS scale)")
        est = anual[anual.index <= 2011]
        a.fill_between(est.index, est["band_low"], est["band_high"], color="#00204d", alpha=0.15,
                       label=f"uncertainty band (P{FAIXA[0]}-P{FAIXA[1]})")
        a2 = a.twinx()
        a2.plot(anual.index, anual["inpe"], color="#c9a900", label="INPE (Aqua reference)")
        a.axvline(2012, color="gray", ls="--", lw=1)
        a.set_title(f"{bioma}: annual fire detections")
        a.legend(loc="upper left", fontsize=8); a2.legend(loc="upper right", fontsize=8)
        b = ax[1]
        r = anual["firesync"] / anual["inpe"]
        b.plot(r.index, r.values, marker="o", color="#00204d")
        b.axvline(2012, color="gray", ls="--", lw=1)
        b.set_ylim(0, np.nanmax(r.values) * 1.3)  # eixo a partir de zero: sem isso, variações de 2% parecem saltos
        b.set_title("Ratio firesync / INPE (flat = no jump at the sensor switch)")
        c = ax[2]
        saz = g.groupby("mes")[["firesync", "inpe"]].mean()
        (saz / saz.sum()).plot(ax=c, color=["#00204d", "#c9a900"])
        c.set_title("Seasonality (share of the year by month)")
        c.set_xticks(range(1, 13))
        c.set_xlabel("month")
        fig.tight_layout()
        nome = saida / f"grafico_{bioma.replace(' ', '_')}.png"
        fig.savefig(nome, dpi=130)
        plt.close(fig)
        feitos.append(nome.name)
    return "Gráficos: " + ", ".join(feitos)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--serie", help="CSV já exportado (bioma, ano, mes, firesync, band_low, band_high, origem)")
    ap.add_argument("--inpe", default=str(Path(__file__).resolve().parent.parent / "referencia" / "inpe_mensal_biomas.csv"))
    ap.add_argument("--ate", type=int, default=2025)
    ap.add_argument("--saida", required=True)
    a = ap.parse_args()

    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    fs = pd.read_csv(a.serie) if a.serie else serie_do_banco(a.ate)
    fs = fs[(fs["ano"] >= ANO_INICIO) & (fs["ano"] <= a.ate)]
    inpe = ler_inpe(a.inpe, a.ate)
    s = fs.merge(inpe, on=["bioma", "ano", "mes"], how="inner")
    s.to_csv(saida / "serie_firesync_vs_inpe.csv", index=False)

    m = comparar(s)
    m.to_csv(saida / "metricas_b6.csv", index=False)
    rel = [f"B6: firesync x INPE (AQUA_M-T, meses completos), {ANO_INICIO} a {a.ate}",
           "Forma da série: correlações perto de 1 e picos coincidentes = mesma forma. Degrau em 2012 perto de 0 = "
           "a troca de satélite não criou salto artificial.", "",
           m.round(3).to_string(index=False), "", graficos(s, saida, ["Amazônia", "Pantanal"])]
    texto = "\n".join(rel)
    (saida / "relatorio_b6.txt").write_text(texto, encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()

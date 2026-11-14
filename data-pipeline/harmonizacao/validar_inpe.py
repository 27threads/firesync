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

Regras da conta (as mesmas da API, docs/importacao-regioes.md, "Fórmula do calendário"):
  - mês sem linha em `agregados` é ZERO detecções (dado, não falta de dado) e entra na série;
  - totais do ano são somados POR CENÁRIO, e só depois saem a mediana e a faixa: a soma dos percentis dos meses
    não é o percentil da soma;
  - cenário sem fator para um período com focos não entra naquele mês (nem no ano); mês sem nenhum cenário
    válido fica sem estimativa e é contado no relatório, nunca vira zero.

Uso (dentro de data-pipeline/):
    python harmonizacao/validar_inpe.py --saida relatorios/b6                       # lê o banco (agregados + fatores)
    python harmonizacao/validar_inpe.py --contagens c.csv --fatores f.csv --saida pasta   # sem banco (testes)

Opções:
    --inpe CAMINHO     CSV do INPE (padrão: referencia/inpe_mensal_biomas.csv). Usa só satelite = AQUA_M-T e
                       parcial = false quando essas colunas existem (PR #21).
    --ate ANO          último ano completo comparado (padrão 2025)

Saídas na pasta --saida:
    serie_firesync_vs_inpe.csv   bioma, ano, mes, firesync (valor central), band_low, band_high, origem, inpe
    serie_anual_firesync.csv     bioma, ano, firesync, band_low, band_high, origem (faixa somada por cenário)
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

def por_cenario(contagens, fatores, ate=None):
    """Valor harmonizado de cada mês em cada cenário: bioma, ano, mes, cenario, valor, origem.

    contagens: bioma, ano, mes, satelite, periodo, focos (só o satélite do mês, como em `agregados`)
    fatores:   bioma, mes, periodo, ano_calibracao, fator
    ate:       último ano da série (padrão: o último ano das contagens). Mês sem linha entra com zero.

    Mês observado pelo VIIRS tem o mesmo valor em todos os cenários. Mês estimado: soma de focos x fator do
    cenário; se falta o fator de um período COM focos, o valor daquele cenário fica vazio.
    """
    ate = int(contagens["ano"].max()) if ate is None else ate
    c = contagens[(contagens["ano"] >= ANO_INICIO) & (contagens["ano"] <= ate)]
    c = c.groupby(["bioma", "ano", "mes", "periodo"], as_index=False)["focos"].sum()
    grade = pd.MultiIndex.from_product(
        [sorted(c["bioma"].unique()), range(ANO_INICIO, ate + 1), range(1, 13), ["D", "N"], sorted(fatores["ano_calibracao"].unique())],
        names=["bioma", "ano", "mes", "periodo", "cenario"]).to_frame(index=False)
    g = grade.merge(c, on=["bioma", "ano", "mes", "periodo"], how="left").fillna({"focos": 0})
    g = g.merge(fatores.rename(columns={"ano_calibracao": "cenario"}), on=["bioma", "mes", "periodo", "cenario"], how="left")
    observado = (g["ano"] > INICIO_VIIRS[0]) | ((g["ano"] == INICIO_VIIRS[0]) & (g["mes"] >= INICIO_VIIRS[1]))
    g["valor"] = np.where(observado, g["focos"], np.where(g["focos"] > 0, g["focos"] * g["fator"], 0.0))
    g["falta"] = g["valor"].isna()
    g["origem"] = np.where(observado, "observado_viirs", "estimado_modis")
    s = g.groupby(["bioma", "ano", "mes", "cenario", "origem"], as_index=False).agg(valor=("valor", "sum"), falta=("falta", "any"))
    s.loc[s["falta"], "valor"] = np.nan
    return s.drop(columns="falta")


def resumir(cen, chaves):
    """Soma por `chaves` DENTRO de cada cenário e só depois tira a mediana e a faixa entre os cenários."""
    soma = cen.groupby(chaves + ["cenario"])["valor"].agg(lambda v: v.sum(skipna=False)).reset_index()
    origens = cen.groupby(chaves)["origem"].agg(lambda o: o.iloc[0] if o.nunique() == 1 else "misto")
    linhas = []
    for chave, g in soma.groupby(chaves):
        e = g["valor"].dropna().to_numpy()
        origem = origens.loc[chave]
        if len(e) == 0:
            valores = (np.nan, np.nan, np.nan)
        elif origem == "observado_viirs":
            valores = (float(e[0]), np.nan, np.nan)
        else:
            valores = (float(np.median(e)), float(np.percentile(e, FAIXA[0])), float(np.percentile(e, FAIXA[1])))
        linhas.append((*chave, *valores, origem))
    return pd.DataFrame(linhas, columns=chaves + ["firesync", "band_low", "band_high", "origem"])


def harmonizar(contagens, fatores, ate=None):
    """Série mensal: bioma, ano, mes, firesync (valor central), band_low, band_high, origem."""
    return resumir(por_cenario(contagens, fatores, ate), ["bioma", "ano", "mes"])


def anual(contagens, fatores, ate=None):
    """Totais do ano, com a faixa somada por cenário: bioma, ano, firesync, band_low, band_high, origem."""
    return resumir(por_cenario(contagens, fatores, ate), ["bioma", "ano"])


def dados_do_banco(ate):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from pipeline import db
    conn = db()
    cont = pd.DataFrame(conn.execute(SQL_AGREGADOS, {"ini": ANO_INICIO, "fim": ate}).fetchall(),
                        columns=["bioma", "ano", "mes", "satelite", "periodo", "focos"])
    fat = pd.DataFrame(conn.execute(SQL_FATORES).fetchall(),
                       columns=["bioma", "mes", "periodo", "ano_calibracao", "fator"])
    if fat.empty:
        sys.exit("fatores_harmonizacao está vazia: rode a calibração (calibrar.py --gravar) antes")
    return cont, fat


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
    """s: bioma, ano, mes, firesync, inpe (meses presentes nas duas séries). Uma linha de medidas por bioma."""
    linhas = []
    for bioma, g in s.dropna(subset=["firesync"]).groupby("bioma"):
        g = g.sort_values(["ano", "mes"])
        anual_ = g.groupby("ano")[["firesync", "inpe"]].sum()
        anual_ = anual_[g.groupby("ano").size().reindex(anual_.index) == 12]  # só anos completos
        top_f = set(anual_["firesync"].nlargest(5).index)
        top_i = set(anual_["inpe"].nlargest(5).index)
        pico = g.loc[g.groupby("ano")["firesync"].idxmax(), ["ano", "mes"]].set_index("ano")["mes"]
        pico_i = g.loc[g.groupby("ano")["inpe"].idxmax(), ["ano", "mes"]].set_index("ano")["mes"]
        dif = (pico - pico_i.reindex(pico.index)).abs()
        dif = np.minimum(dif, 12 - dif)  # dezembro e janeiro são vizinhos
        saz_f = g.groupby("mes")["firesync"].mean()
        saz_i = g.groupby("mes")["inpe"].mean()
        razao = (anual_["firesync"] / anual_["inpe"]).replace([np.inf, -np.inf], np.nan)
        antes = razao[(razao.index >= ANO_INICIO) & (razao.index <= 2011)].mean()
        depois = razao[razao.index >= 2013].mean()
        linhas.append({
            "bioma": bioma,
            "meses": len(g),
            "anos_completos": len(anual_),
            "corr_mensal_pearson": g["firesync"].corr(g["inpe"]),
            # Spearman = Pearson dos postos (sem depender do scipy, que não está no requirements)
            "corr_mensal_spearman": g["firesync"].rank().corr(g["inpe"].rank()),
            "corr_anual_pearson": anual_["firesync"].corr(anual_["inpe"]),
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


def graficos(s, anual_fs, saida, biomas):
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
        a_fs = anual_fs[anual_fs["bioma"] == bioma].set_index("ano")
        inpe_ano = g.groupby("ano")["inpe"].sum()
        fig, ax = plt.subplots(1, 3, figsize=(16, 4.5))
        a = ax[0]
        a.plot(a_fs.index, a_fs["firesync"], color="#00204d", label="firesync (VIIRS scale)")
        est = a_fs[a_fs["origem"] != "observado_viirs"]
        a.fill_between(est.index, est["band_low"], est["band_high"], color="#00204d", alpha=0.15,
                       label=f"uncertainty band (P{FAIXA[0]}-P{FAIXA[1]}, summed per scenario)")
        a2 = a.twinx()
        a2.plot(inpe_ano.index, inpe_ano.values, color="#c9a900", label="INPE (Aqua reference)")
        a.axvline(2012, color="gray", ls="--", lw=1)
        a.set_title(f"{bioma}: annual fire detections")
        # legenda única abaixo do gráfico: dentro dele, ela cobria o topo da faixa nos primeiros anos
        h1, l1 = a.get_legend_handles_labels()
        h2, l2 = a2.get_legend_handles_labels()
        a.legend(h1 + h2, l1 + l2, loc="upper center", bbox_to_anchor=(0.5, -0.1), fontsize=8, frameon=False)
        b = ax[1]
        r = a_fs["firesync"].reindex(inpe_ano.index) / inpe_ano
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
        fig.savefig(nome, dpi=130, bbox_inches="tight")
        plt.close(fig)
        feitos.append(nome.name)
    return "Gráficos: " + ", ".join(feitos)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--contagens", help="CSV no formato de agregados (bioma, ano, mes, satelite, periodo, focos)")
    ap.add_argument("--fatores", help="CSV dos fatores (bioma, mes, periodo, ano_calibracao, fator)")
    ap.add_argument("--inpe", default=str(Path(__file__).resolve().parent.parent / "referencia" / "inpe_mensal_biomas.csv"))
    ap.add_argument("--ate", type=int, default=2025)
    ap.add_argument("--saida", required=True)
    a = ap.parse_args()
    if bool(a.contagens) != bool(a.fatores):
        sys.exit("--contagens e --fatores vão juntos")

    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    cont, fat = (pd.read_csv(a.contagens), pd.read_csv(a.fatores)) if a.contagens else dados_do_banco(a.ate)
    cen = por_cenario(cont, fat, a.ate)
    mensal = resumir(cen, ["bioma", "ano", "mes"])
    anual_fs = resumir(cen, ["bioma", "ano"])
    anual_fs.to_csv(saida / "serie_anual_firesync.csv", index=False)
    s = mensal.merge(ler_inpe(a.inpe, a.ate), on=["bioma", "ano", "mes"], how="inner")
    s.to_csv(saida / "serie_firesync_vs_inpe.csv", index=False)

    m = comparar(s)
    m.to_csv(saida / "metricas_b6.csv", index=False)
    sem_fator = int(mensal["firesync"].isna().sum())
    zerados = int((mensal["firesync"] == 0).sum())
    rel = [f"B6: firesync x INPE (AQUA_M-T, meses completos), {ANO_INICIO} a {a.ate}",
           "Forma da série: correlações perto de 1 e picos coincidentes = mesma forma. Degrau em 2012 perto de 0 = "
           "a troca de satélite não criou salto artificial.",
           f"Meses com zero detecções no firesync (entram na comparação): {zerados}. "
           f"Meses sem estimativa por falta de fator (ficam fora): {sem_fator}.", "",
           m.round(3).to_string(index=False), "", graficos(s, anual_fs, saida, ["Amazônia", "Pantanal"])]
    texto = "\n".join(rel)
    (saida / "relatorio_b6.txt").write_text(texto, encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()

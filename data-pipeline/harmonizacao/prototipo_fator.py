"""B1. Protótipo do fator Aqua -> S-NPP (escala VIIRS), por bioma x mês x dia/noite.

Regras: docs/decisoes-harmonizacao.md e docs/importacao-regioes.md (seção "Fórmula do calendário").
Roda direto nos CSVs do FIRMS (Archive Download), sem banco. Serve para conferir a conta com dados reais:
com um ano só sai UM cenário, então aqui não há faixa de incerteza.

Uso:
    python -I prototipo_fator.py <modis.csv> <viirs_snpp.csv> <Biomas_250mil.zip> <pasta_saida>

Saídas na pasta:
    fatores_<ano>.csv     um fator por bioma x mês x período, com as contagens que o sustentam
    funil_<ano>.csv       quantas linhas cada regra tirou, por satélite
"""
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

# Nomes pelo código do IBGE (o arquivo traz os nomes com acentuação quebrada).
BIOMAS = {1: "Amazônia", 2: "Caatinga", 3: "Cerrado", 4: "Mata Atlântica", 5: "Pampa", 6: "Pantanal"}
COLUNAS = ["latitude", "longitude", "acq_date", "acq_time", "satellite", "confidence", "frp", "daynight", "type"]

# Limites de contagem do Aqua usados só para mostrar quantas condições ficariam frágeis.
# O mínimo oficial ainda não foi decidido (pendência em decisoes-harmonizacao.md).
LIMITES_INFORMATIVOS = [10, 30, 100]


def limpar(df, sensor, funil):
    """Aplica as regras de limpeza do main e registra quantas linhas cada uma tirou."""
    def passo(nome, mascara):
        nonlocal df
        funil.append({"sensor": sensor, "regra": nome, "removidas": int((~mascara).sum())})
        df = df[mascara]

    funil.append({"sensor": sensor, "regra": "linhas lidas", "removidas": 0, "restantes": len(df)})
    if sensor == "MODIS":
        passo("satélite diferente de Aqua (Terra fora)", df["satellite"] == "Aqua")
    passo("type diferente de 0", df["type"] == 0)
    frp = pd.to_numeric(df["frp"], errors="coerce")
    passo("FRP vazio, zero ou negativo", frp > 0)
    if sensor == "MODIS":
        conf = pd.to_numeric(df["confidence"], errors="coerce")
        passo("confiança baixa (MODIS abaixo de 30)", conf >= 30)
    else:
        passo("confiança baixa (VIIRS l, de dia ou de noite)", df["confidence"].isin(["n", "h"]))
    antes = len(df)
    df = df.drop_duplicates(subset=["latitude", "longitude", "acq_date", "acq_time", "satellite"])
    funil.append({"sensor": sensor, "regra": "duplicatas idênticas", "removidas": antes - len(df)})
    funil.append({"sensor": sensor, "regra": "restantes", "removidas": 0, "restantes": len(df)})
    return df


def com_bioma(df, biomas, sensor, funil):
    """Atribui o bioma pelo ponto. Pontos fora dos 6 biomas (mar, fronteira) saem e são contados."""
    pts = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["longitude"], df["latitude"]), crs="EPSG:4326")
    j = gpd.sjoin(pts, biomas, how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]  # ponto exatamente na divisa: fica no primeiro bioma
    fora = j["CD_Bioma"].isna()
    funil.append({"sensor": sensor, "regra": "fora dos 6 biomas", "removidas": int(fora.sum())})
    j = j[~fora]
    j["bioma"] = j["CD_Bioma"].astype(int).map(BIOMAS)
    j["mes"] = pd.to_datetime(j["acq_date"]).dt.month
    j["ano"] = pd.to_datetime(j["acq_date"]).dt.year
    return pd.DataFrame(j[["bioma", "ano", "mes", "daynight", "acq_date"]])


def main(modis_csv, viirs_csv, biomas_zip, saida):
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    funil = []

    biomas = gpd.read_file("zip://" + str(Path(biomas_zip)).replace("\\", "/"))[["CD_Bioma", "geometry"]]
    # SIRGAS 2000 (EPSG:4674) e WGS84 diferem menos de 1 m: só declaramos o CRS dos pontos igual.
    biomas = biomas.set_crs("EPSG:4326", allow_override=True)

    aqua = limpar(pd.read_csv(modis_csv, usecols=COLUNAS), "MODIS", funil)
    snpp = limpar(pd.read_csv(viirs_csv, usecols=COLUNAS), "VIIRS", funil)
    aqua = com_bioma(aqua, biomas, "MODIS", funil)
    snpp = com_bioma(snpp, biomas, "VIIRS", funil)

    chave = ["bioma", "ano", "mes", "daynight"]
    a = aqua.groupby(chave).size().rename("focos_aqua")
    s = snpp.groupby(chave).size().rename("focos_snpp")
    t = pd.concat([a, s], axis=1).fillna(0).astype(int).reset_index()
    t = t.rename(columns={"daynight": "periodo"})
    # Fator = razão das somas (S-NPP / Aqua). Sem Aqua, não há fator (fica vazio, não infinito).
    t["fator"] = (t["focos_snpp"] / t["focos_aqua"].where(t["focos_aqua"] > 0)).round(3)
    for lim in LIMITES_INFORMATIVOS:
        t[f"aqua_abaixo_de_{lim}"] = t["focos_aqua"] < lim

    ano = int(t["ano"].mode()[0])
    t.sort_values(["bioma", "mes", "periodo"]).to_csv(saida / f"fatores_{ano}.csv", index=False)
    # Contagens diárias no formato que o calibrar.py lê com --csv (regiao, data, periodo, satelite, focos)
    diario = pd.concat([aqua.assign(satelite="Aqua"), snpp.assign(satelite="SNPP")])
    diario = (diario.groupby(["bioma", "acq_date", "daynight", "satelite"]).size().rename("focos").reset_index()
              .rename(columns={"bioma": "regiao", "acq_date": "data", "daynight": "periodo"}))
    diario.to_csv(saida / f"contagens_diarias_{ano}.csv", index=False)
    pd.DataFrame(funil).to_csv(saida / f"funil_{ano}.csv", index=False)

    # Resumo na tela
    pd.set_option("display.width", 200)
    print("\n== Funil de limpeza")
    print(pd.DataFrame(funil).astype(object).fillna("").to_string(index=False))
    print("\n== Razão anual S-NPP / Aqua por bioma (todas as condições somadas)")
    anual = t.groupby("bioma")[["focos_aqua", "focos_snpp"]].sum()
    anual["razao"] = (anual["focos_snpp"] / anual["focos_aqua"]).round(2)
    print(anual.to_string())
    print("\n== Amazônia: fator por mês e período")
    amz = t[t["bioma"] == "Amazônia"].pivot(index="mes", columns="periodo", values=["focos_aqua", "focos_snpp", "fator"])
    print(amz.to_string())
    print("\n== Condições (bioma x mês x período) com poucos focos do Aqua, de", len(t))
    for lim in LIMITES_INFORMATIVOS:
        print(f"  Aqua abaixo de {lim}: {int(t[f'aqua_abaixo_de_{lim}'].sum())}")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])

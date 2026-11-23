"""Nome do lugar de cada célula H3 de resolução 4 (cerca de 1.770 km², a unidade do risco e do alerta).

Quem está no campo pensa em município, unidade de conservação ou terra indígena, e não em célula H3. Este job cruza
cada célula da cobertura com três camadas oficiais (lugares.json) e grava a tabela `lugares_celula`; a API só lê.

- Município (e UF): o que contém o centro da célula. Na costa e na fronteira, onde o centro cai no mar ou no país
  vizinho, o município que mais cobre a célula.
- Unidades de conservação (MMA, CNUC) e terras indígenas (Funai): as que cobrem pelo menos 1% da célula, da maior para
  a menor parte, até 3 nomes de cada.

Uso (dentro de data-pipeline/, com DATABASE_URL): python lugares.py
Baixa as camadas que faltam em data/raw/ (fora do git) e troca a tabela inteira numa transação.

Divisas dos estados no mapa do site (sem banco): python lugares.py --estados ../frontend/public/brazil-states.geojson
Junta os municípios da mesma malha do IBGE por UF, simplifica em ~1 km e grava um GeoJSON pequeno, versionado no front.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import h3
import shapely
from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.ops import polylabel

import logs
from pipeline import RAW, ROOT, SIMPLIFY_DEG, curl, db, ms_desde

log = logs.logger("lugares")
ALERT_RESOLUTION = 4
AREA_IGUAL = "ESRI:102033"  # South America Albers Equal Area: a parte da célula é medida em área, não em graus
MIN_PARTE = 0.01            # parte mínima da célula coberta para a área protegida entrar na lista (≈ 18 km²)
MAX_NOMES = 3
SIMPLIFICA_ESTADOS = 0.01   # ~1 km: a divisa só precisa ser vista no mapa, e o arquivo fica pequeno
CASAS_ESTADOS = 3            # ~110 m de precisão nas coordenadas do GeoJSON
MIN_ILHA = 0.001             # graus² (≈ 12 km²): ilhas menores somem do desenho da divisa
PALAVRAS_CURTAS = {"a", "à", "ao", "as", "da", "das", "de", "do", "dos", "e", "em", "na", "nas", "no", "nos", "o", "os"}


def carregar_fontes(caminho=ROOT / "lugares.json"):
    return json.loads(caminho.read_text(encoding="utf-8"))


def titulo(nome):
    """O CNUC grava os nomes em maiúsculas. Vira título, com as palavras curtas em minúsculas; o resto fica como veio."""
    palavras = nome.split()
    if nome != nome.upper():
        return " ".join(palavras)
    return " ".join(p.lower() if i and p.lower() in PALAVRAS_CURTAS else "-".join(s.capitalize() for s in p.split("-"))
                    for i, p in enumerate(palavras))


def ler_camada(fonte):
    """Camada oficial -> GeoDataFrame com `nome` (e `uf`, nos municípios). Baixa o arquivo se ainda não estiver em RAW."""
    arquivo = RAW / fonte["arquivo"]
    if not arquivo.exists():
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        log.info("place_layer_download", file=fonte["arquivo"])
        curl(fonte["url"], arquivo)
    colunas = {fonte["nome"]: "nome", **({fonte["uf"]: "uf"} if "uf" in fonte else {})}
    # só as colunas usadas: outras colunas dos arquivos têm texto cortado no meio de um caractere
    g = gpd.read_file(f"zip://{arquivo}", layer=fonte.get("camada"), columns=list(colunas)).rename(columns=colunas)
    g = g[g["nome"].notna()].copy()
    # os polígonos oficiais têm muitos vértices; simplificar em ~110 m não muda a parte de uma célula de ~1.770 km²
    g["geometry"] = g.geometry.simplify(SIMPLIFY_DEG).make_valid()
    return g


def partes_por_celula(hexes, camada, chaves):
    """Área de cada polígono da camada dentro de cada célula, somada por nome, da maior para a menor."""
    partes = gpd.overlay(hexes[["h3", "geometry"]], camada.to_crs(AREA_IGUAL)[[*chaves, "geometry"]],
                         how="intersection", keep_geom_type=True)
    partes["area"] = partes.area
    soma = partes.groupby(["h3", *chaves], as_index=False)["area"].sum()
    # Conta em float explícito: no pandas 3, sem nenhuma interseção o `map` de uma coluna de texto vazia sai como texto,
    # e a divisão quebrava (PR #172).
    area_da_celula = dict(zip(hexes["h3"], hexes.area.astype(float)))
    soma["parte"] = soma["area"].astype(float) / soma["h3"].map(area_da_celula).astype(float)
    return soma.sort_values(["h3", "area", *chaves], ascending=[True, False, *[True] * len(chaves)])


def nomes(hexes, camada):
    soma = partes_por_celula(hexes, camada.assign(nome=camada["nome"].map(titulo)), ["nome"])
    soma = soma[soma["parte"] >= MIN_PARTE]
    return {celula: list(g["nome"])[:MAX_NOMES] for celula, g in soma.groupby("h3")}


def lugares_das_celulas(celulas, municipios, unidades, terras):
    """[célula res 4] -> [{h3, municipio, uf, unidades_conservacao, terras_indigenas}], na mesma ordem."""
    contornos = [Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(c)]) for c in celulas]
    hexes = gpd.GeoDataFrame({"h3": celulas}, geometry=contornos, crs=4326).to_crs(AREA_IGUAL)
    centros = gpd.GeoDataFrame({"h3": celulas}, crs=4326, geometry=gpd.points_from_xy(
        [h3.cell_to_latlng(c)[1] for c in celulas], [h3.cell_to_latlng(c)[0] for c in celulas])).to_crs(AREA_IGUAL)
    mun = municipios.to_crs(AREA_IGUAL)
    no_centro = gpd.sjoin(centros, mun[["nome", "uf", "geometry"]], predicate="within").drop_duplicates("h3")
    municipio = {r.h3: (r.nome, r.uf) for r in no_centro.itertuples()}
    sem_centro = hexes[~hexes["h3"].isin(municipio)]
    if len(sem_centro):
        maior = partes_por_celula(sem_centro, mun, ["nome", "uf"]).drop_duplicates("h3")
        municipio.update({r.h3: (r.nome, r.uf) for r in maior.itertuples()})
    ucs, tis = nomes(hexes, unidades), nomes(hexes, terras)
    return [{"h3": c, "municipio": municipio.get(c, (None, None))[0], "uf": municipio.get(c, (None, None))[1],
             "unidades_conservacao": ucs.get(c, []), "terras_indigenas": tis.get(c, [])} for c in celulas]


def arredondar(coords):
    if isinstance(coords[0], (int, float)):
        return [round(v, CASAS_ESTADOS) for v in coords]
    return [arredondar(c) for c in coords]


def estados_geojson(municipios):
    """Municípios (com `uf`) -> FeatureCollection com um polígono por estado e o ponto da sigla (`label`, [lon, lat])
    no centro visual da maior parte do estado, sempre dentro dele."""
    features = []
    for uf, grupo in sorted(municipios.groupby("uf")):
        uniao = grupo.union_all()
        # Só o contorno externo: os municípios simplificados não encostam perfeitamente, e a união sai cheia de buracos
        # falsos (1.070 só no Pará), que eram quase todo o peso do arquivo. O mapa desenha só a linha, sem
        # preenchimento, então um buraco verdadeiro (o DF dentro de Goiás) continua visível pela linha do outro estado.
        partes = [Polygon(p.exterior) for p in getattr(uniao, "geoms", [uniao])]
        partes = [p for p in partes if p.area >= MIN_ILHA] or [max(partes, key=lambda p: p.area)]
        estado = shapely.set_precision(MultiPolygon(partes).simplify(SIMPLIFICA_ESTADOS), 10 ** -CASAS_ESTADOS)
        maior = max(getattr(estado, "geoms", [estado]), key=lambda g: g.area)
        ponto = polylabel(maior, tolerance=SIMPLIFICA_ESTADOS)
        geometria = mapping(estado)
        features.append({"type": "Feature", "properties": {"state": uf, "label": arredondar([ponto.x, ponto.y])},
                         "geometry": {"type": geometria["type"], "coordinates": arredondar(geometria["coordinates"])}})
    return {"type": "FeatureCollection", "features": features}


def celulas_da_cobertura(conn):
    """Células de resolução 4 que contêm alguma célula da cobertura (`celula_regiao`)."""
    filhas = conn.execute("SELECT h3 FROM celula_regiao").fetchall()
    return sorted({h3.cell_to_parent(h3.int_to_str(c), ALERT_RESOLUTION) for (c,) in filhas})


def gravar(conn, linhas):
    """A tabela vira exatamente as linhas calculadas, numa transação: a API nunca lê metade."""
    agora = datetime.now(timezone.utc)
    with conn.transaction():
        conn.execute("DELETE FROM lugares_celula")
        conn.cursor().executemany(
            """INSERT INTO lugares_celula (h3, municipio, uf, unidades_conservacao, terras_indigenas, calculado_em)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [(h3.str_to_int(r["h3"]), r["municipio"], r["uf"], r["unidades_conservacao"], r["terras_indigenas"], agora)
             for r in linhas])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--estados", type=Path, help="grava só o GeoJSON das divisas dos estados neste arquivo (sem banco)")
    a = ap.parse_args()
    inicio = time.monotonic()
    fontes = carregar_fontes()
    if a.estados:
        fc = estados_geojson(ler_camada(fontes["municipios"]))
        a.estados.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        log.info("states_saved", states=len(fc["features"]), file=str(a.estados), bytes=a.estados.stat().st_size,
                 duration_ms=ms_desde(inicio))
        return
    conn = db()
    camadas = {nome: ler_camada(f) for nome, f in fontes.items()}
    celulas = celulas_da_cobertura(conn)
    linhas = lugares_das_celulas(celulas, camadas["municipios"], camadas["unidades_conservacao"],
                                 camadas["terras_indigenas"])
    gravar(conn, linhas)
    log.info("places_saved", cells=len(linhas), without_municipality=sum(r["municipio"] is None for r in linhas),
             with_protected_area=sum(bool(r["unidades_conservacao"] or r["terras_indigenas"]) for r in linhas),
             duration_ms=ms_desde(inicio))


if __name__ == "__main__":
    sys.exit(main())

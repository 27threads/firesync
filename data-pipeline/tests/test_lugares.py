"""Nome do lugar de cada célula de resolução 4: município, unidades de conservação e terras indígenas. DADOS INVENTADOS.

Os polígonos são retângulos em volta de uma célula conhecida, para saber de antemão o que cada célula deve receber.
"""
import os

import geopandas as gpd
import h3
import pytest
from shapely.geometry import box

import lugares

CELULA = h3.latlng_to_cell(-10.0, -55.0, 4)
LAT, LON = h3.cell_to_latlng(CELULA)
VIZINHA = sorted(h3.grid_ring(CELULA, 1))[0]
VLAT, VLON = h3.cell_to_boundary(CELULA)[0]         # um vértice da célula


def camada(linhas):
    """[(geometria, {coluna: valor})] -> GeoDataFrame em graus (EPSG:4674, como os arquivos oficiais)."""
    return gpd.GeoDataFrame([dict(c) for _, c in linhas], geometry=[g for g, _ in linhas], crs=4674)


MUNICIPIOS = camada([
    (box(LON - 2, LAT - 2, LON + 0.01, LAT + 2), {"nome": "Oeste", "uf": "MT"}),     # contém o centro
    (box(LON + 0.01, LAT - 2, LON + 2, LAT + 2), {"nome": "Leste", "uf": "PA"}),
])


def vazio():
    return camada([(box(0, 0, 0.1, 0.1), {"nome": "Longe"})])


def test_municipio_e_o_do_centro_da_celula_com_a_uf():
    r = lugares.lugares_das_celulas([CELULA], MUNICIPIOS, vazio(), vazio())
    assert r == [{"h3": CELULA, "municipio": "Oeste", "uf": "MT", "unidades_conservacao": [], "terras_indigenas": []}]


def test_centro_fora_de_todo_municipio_usa_o_que_mais_cobre_a_celula():
    """Costa e fronteira: o centro cai no mar ou no país vizinho, mas a célula ainda encosta num município."""
    borda = camada([(box(LON + 0.05, LAT - 2, LON + 2, LAT + 2), {"nome": "Leste", "uf": "PA"}),
                    (box(LON - 2, LAT - 2, LON - 0.3, LAT + 2), {"nome": "Oeste", "uf": "MT"})])
    r = lugares.lugares_das_celulas([CELULA], borda, vazio(), vazio())
    assert (r[0]["municipio"], r[0]["uf"]) == ("Leste", "PA")


def test_celula_sem_nenhum_municipio_fica_sem_nome():
    r = lugares.lugares_das_celulas([CELULA], vazio().assign(uf="XX"), vazio(), vazio())
    assert r[0]["municipio"] is None and r[0]["uf"] is None


def test_areas_protegidas_vem_da_maior_para_a_menor_e_sem_as_lascas_da_borda():
    ucs = camada([
        (box(LON - 0.05, LAT - 0.05, LON + 0.05, LAT + 0.05), {"nome": "PEQUENA"}),
        (box(LON - 1, LAT - 1, LON + 1, LAT + 1), {"nome": "GRANDE"}),
        (box(VLON - 0.02, VLAT - 0.02, VLON + 0.02, VLAT + 0.02), {"nome": "LASCA"}),   # só um canto entra na célula
    ])
    tis = camada([(box(LON - 1, LAT - 1, LON + 1, LAT + 1), {"nome": "Terra A"})])
    r = lugares.lugares_das_celulas([CELULA], MUNICIPIOS, ucs, tis)[0]
    assert r["unidades_conservacao"][:2] == ["Grande", "Pequena"]
    assert "Lasca" not in r["unidades_conservacao"]         # abaixo do mínimo de área dentro da célula
    assert r["terras_indigenas"] == ["Terra A"]


def test_lista_de_areas_protegidas_tem_no_maximo_tres_nomes():
    ucs = camada([(box(LON - 1 + i * 0.01, LAT - 1, LON + 1, LAT + 1), {"nome": f"UC {i}"}) for i in range(5)])
    r = lugares.lugares_das_celulas([CELULA], MUNICIPIOS, ucs, vazio())[0]
    assert len(r["unidades_conservacao"]) == lugares.MAX_NOMES == 3


def test_um_nome_repetido_em_dois_poligonos_aparece_uma_vez():
    tis = camada([(box(LON - 1, LAT - 1, LON, LAT + 1), {"nome": "Terra A"}),
                  (box(LON, LAT - 1, LON + 1, LAT + 1), {"nome": "Terra A"})])
    assert lugares.lugares_das_celulas([CELULA], MUNICIPIOS, vazio(), tis)[0]["terras_indigenas"] == ["Terra A"]


@pytest.mark.parametrize("bruto,limpo", [
    ("ÁREA DE PROTEÇÃO AMBIENTAL DA BACIA DO RIO SÃO BARTOLOMEU", "Área de Proteção Ambiental da Bacia do Rio São Bartolomeu"),
    ("PARQUE NACIONAL DO XINGU E DAS ÁGUAS", "Parque Nacional do Xingu e das Águas"),
    ("Kayapó", "Kayapó"),
    ("  Terra   do Meio ", "Terra do Meio"),
])
def test_nome_em_maiusculas_vira_titulo_com_as_palavras_curtas_em_minusculas(bruto, limpo):
    assert lugares.titulo(bruto) == limpo


def test_fontes_tem_url_arquivo_e_coluna_de_nome_de_cada_camada():
    fontes = lugares.carregar_fontes()
    assert set(fontes) == {"municipios", "unidades_conservacao", "terras_indigenas"}
    for f in fontes.values():
        assert f["url"].startswith("https://") and f["arquivo"] and f["nome"] and f["fonte"]
    assert fontes["municipios"]["uf"]


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="precisa de TEST_DATABASE_URL (Postgres descartável)")
def test_gravar_troca_a_tabela_inteira_e_le_as_celulas_da_cobertura():
    import psycopg

    with psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True) as conn:
        for f in sorted(lugares.ROOT.joinpath("migrations").glob("*.sql")):
            conn.execute(f.read_text(encoding="utf-8"))
        conn.execute("DELETE FROM celula_regiao")
        conn.execute("DELETE FROM regioes WHERE nome = 'Teste lugares'")
        rid = conn.execute("""INSERT INTO regioes (nome, geom, fonte_poligono)
            VALUES ('Teste lugares', ST_Multi(ST_MakeEnvelope(-56, -11, -54, -9, 4326)), 't') RETURNING id""").fetchone()[0]
        filhas = [h3.str_to_int(c) for c in sorted(h3.cell_to_children(CELULA, 6))[:2]]
        for c in filhas:
            conn.execute("INSERT INTO celula_regiao VALUES (%s, %s)", (c, rid))
        assert lugares.celulas_da_cobertura(conn) == [CELULA]
        conn.execute("INSERT INTO lugares_celula (h3, municipio, uf, calculado_em) VALUES (%s, 'Velho', 'XX', now())",
                     (h3.str_to_int(VIZINHA),))
        lugares.gravar(conn, lugares.lugares_das_celulas([CELULA], MUNICIPIOS, vazio(), vazio()))
        linhas = conn.execute("SELECT h3, municipio, uf, unidades_conservacao, terras_indigenas FROM lugares_celula").fetchall()
        conn.execute("DELETE FROM celula_regiao")
        conn.execute("DELETE FROM regioes WHERE id = %s", (rid,))
    assert linhas == [(h3.str_to_int(CELULA), "Oeste", "MT", [], [])]


def test_estados_junta_os_municipios_por_uf_com_o_ponto_da_sigla_dentro_do_estado():
    """Divisas dos estados no mapa: saem da mesma malha municipal do IBGE, juntando os municípios de cada UF."""
    from shapely.geometry import Point, shape

    mun = camada([(box(0, 0, 1, 1), {"nome": "A", "uf": "PA"}), (box(1, 0, 2, 1), {"nome": "B", "uf": "PA"}),
                  (box(0, 1, 2, 2), {"nome": "C", "uf": "AM"})])
    fc = lugares.estados_geojson(mun)
    assert fc["type"] == "FeatureCollection"
    por_uf = {f["properties"]["state"]: f for f in fc["features"]}
    assert set(por_uf) == {"AM", "PA"}
    pa = shape(por_uf["PA"]["geometry"])
    assert pa.area == pytest.approx(2, rel=0.02)                       # os dois municípios viraram um polígono só
    lon, lat = por_uf["PA"]["properties"]["label"]
    assert pa.contains(Point(lon, lat))


def test_estados_geojson_arredonda_as_coordenadas_para_o_arquivo_ficar_pequeno():
    mun = camada([(box(0.123456, 0.123456, 1.987654, 1.987654), {"nome": "A", "uf": "PA"})])
    feature = lugares.estados_geojson(mun)["features"][0]
    coords = [c for ring in feature["geometry"]["coordinates"] for c in ring] if feature["geometry"]["type"] == "Polygon" \
        else [c for poly in feature["geometry"]["coordinates"] for ring in poly for c in ring]
    assert all(round(v, lugares.CASAS_ESTADOS) == v for c in coords for v in c)


def test_estados_sem_as_frestas_entre_municipios_nem_as_ilhotas():
    """Os municípios simplificados não encostam perfeitamente: a união sai cheia de buracos falsos, que eram quase todo
    o peso do arquivo. O mapa só desenha a linha da divisa, então o estado fica só com o contorno externo."""
    from shapely.geometry import shape

    mun = camada([(box(0, 0, 1, 1), {"nome": "A", "uf": "PA"}), (box(1.0001, 0, 2, 1), {"nome": "B", "uf": "PA"}),
                  (box(5, 5, 5.01, 5.01), {"nome": "Ilhota", "uf": "PA"})])
    pa = shape(lugares.estados_geojson(mun)["features"][0]["geometry"])
    partes = list(getattr(pa, "geoms", [pa]))
    assert all(len(p.interiors) == 0 for p in partes)
    assert not any(p.bounds[0] >= 5 for p in partes)

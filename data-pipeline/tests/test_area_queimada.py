"""Validação com área queimada (issue #107), sem banco e sem HDF. DADOS INVENTADOS."""
from datetime import date

import h3
import numpy as np
import pandas as pd
import pytest

from validacao import area_queimada as aq
from validacao import backtest_alerta as bt


def test_centro_do_pixel_na_grade_senoidal_do_modis():
    """Pixel (0, 0) do bloco h12v09: o canto do bloco fica no equador, em 60° O."""
    lat, lon = aq.centros_latlon(12, 9, np.array([0]), np.array([0]))
    assert lat[0] == pytest.approx(-0.002083, abs=1e-5)
    assert lon[0] == pytest.approx(-59.997917, abs=1e-5)


def test_ida_e_volta_da_projecao_senoidal():
    linhas, colunas = np.array([10, 1200, 2399]), np.array([5, 700, 2399])
    lat, lon = aq.centros_latlon(11, 10, linhas, colunas)
    x = np.radians(lon) * aq.RAIO * np.cos(np.radians(lat))
    y = np.radians(lat) * aq.RAIO
    assert np.allclose(x, aq.X0 + 11 * aq.BLOCO + (colunas + 0.5) * aq.PIXEL)
    assert np.allclose(y, aq.Y0 - 10 * aq.BLOCO - (linhas + 0.5) * aq.PIXEL)


def test_celula_res4_e_a_mesma_do_banco():
    """O banco agrupa pela mãe da célula res 6 (a auditoria achou ~6% de diferença para latlng_to_cell(..., 4))."""
    lat, lon = np.array([-3.1, -10.73, -8.4]), np.array([-60.1, -55.21, -48.0])
    esperado = [h3.str_to_int(h3.cell_to_parent(h3.latlng_to_cell(a, b, 6), 4)) for a, b in zip(lat, lon)]
    assert aq.celula_res4(lat, lon).tolist() == esperado


def test_pixels_queimados_ignoram_nao_queimado_sem_dado_e_agua():
    burn = np.array([[0, -1, -2], [15, 0, 366]], dtype=np.int16)
    linhas, colunas, dias = aq.pixels_queimados(burn)
    assert linhas.tolist() == [1, 1] and colunas.tolist() == [0, 2] and dias.tolist() == [15, 366]


def test_area_por_celula_e_dia_soma_os_pixels():
    unidades = np.array([7, 7, 7, 9])
    datas = np.array([date(2021, 8, 1), date(2021, 8, 1), date(2021, 8, 2), date(2021, 8, 1)])
    df = aq.area_por_celula_dia(unidades, datas)
    linha = df[(df.unidade == 7) & (df.data == date(2021, 8, 1))].iloc[0]
    assert linha.km2 == pytest.approx(2 * aq.PIXEL_KM2)
    assert len(df) == 3


def test_area_dos_14_dias_seguintes_nao_inclui_o_domingo():
    """Mesma janela do alvo do modelo: t+1..t+14. Queima só no próprio domingo não conta."""
    t = date(2021, 8, 1)
    df = pd.DataFrame({"unidade": [5, 5, 5], "data": [t, date(2021, 8, 2), date(2021, 8, 15)], "km2": [10.0, 1.0, 2.0]})
    m = aq.matriz_area(df, np.array([5, 6]))
    a14 = aq.area_14_dias_seguintes(m, [t])
    assert a14[0].tolist() == [3.0, 0.0]      # 2/8 e 15/8 entram (t+1 e t+14); 1/8 (t) não
    assert m.shape[1] == (bt.FIM - bt.INICIO).days + 1


def test_media_por_faixa_e_ordem():
    prob = np.array([0.9, 0.7, 0.5, 0.45, 0.3, 0.1, 0.05])
    area = np.array([20.0, 10.0, 6.0, 4.0, 2.0, 0.0, 1.0])
    medias = aq.media_por_faixa(prob, area, aq.FAIXAS)
    assert medias == {"very_high": 15.0, "high": 5.0, "medium": 2.0, "lower": 0.5}
    assert aq.ordem_mantida(medias)
    assert not aq.ordem_mantida({"very_high": 1.0, "high": 2.0, "medium": 0.5, "lower": 0.1})

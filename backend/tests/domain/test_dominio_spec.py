"""Especificação TDD do núcleo da API (domínio, arquitetura hexagonal).

Os testes implementados executam as interfaces reais do domínio. Apenas intensidade,
alerta e janelas recentes permanecem em xfail(strict=True), pois pertencem à próxima entrega.

Quando você implementar uma parte e o teste passar, o `strict=True` faz a esteira quebrar com XPASS.
É o aviso para tirar o marcador daquele teste: a partir daí, ele vale de verdade.

Os valores esperados foram calculados à mão e seguem o docs/api.md. Mudar um valor aqui é mudar o contrato.
"""
import json
from datetime import date

import pytest

TDD = pytest.mark.xfail(strict=True, reason="TDD: domínio ainda não implementado")


# ---------------------------------------------------------------- faixa de incerteza (P5–P95)
def test_faixa_p5_p95_por_interpolacao_linear():
    from backend.domain.calculations.statistics import summarize
    b = summarize(dict(enumerate([10, 20, 30, 40, 50])), estimated=True)
    assert (b["detections"], b["band_low"], b["band_high"]) == pytest.approx((30, 12, 48))  # índices 0,2 e 3,8


def test_faixa_com_13_cenarios():
    from backend.domain.calculations.statistics import summarize
    b = summarize(dict(enumerate(range(1, 14))), estimated=True)
    assert (b["detections"], b["band_low"], b["band_high"]) == pytest.approx((7, 1.6, 12.4))


def test_faixa_e_calculada_depois_de_somar():
    """A soma dos percentis das células não é o percentil da soma."""
    from backend.domain.calculations.statistics import summarize
    a, b = [1, 10, 1], [10, 1, 1]           # duas células, três cenários
    soma = [x + y for x, y in zip(a, b)]     # [11, 11, 2]
    assert summarize(dict(enumerate(soma)), True)["band_high"] != pytest.approx(
        summarize(dict(enumerate(a)), True)["band_high"] + summarize(dict(enumerate(b)), True)["band_high"])


# ---------------------------------------------------------------- origem e satélite do mês
@pytest.mark.parametrize("ano, mes, origem, satelite", [
    (2003, 1, "estimated_modis", "Aqua"),
    (2012, 1, "estimated_modis", "Aqua"),     # o S-NPP só começa em 20/01/2012
    (2012, 2, "observed_viirs", "SNPP"),
    (2026, 10, "observed_viirs", "SNPP"),
    (2026, 11, "observed_viirs", "N20"),      # o S-NPP parou em 02/11/2026; NOAA-20 com fator 1
])
def test_origem_e_satelite_dependem_so_da_data(ano, mes, origem, satelite):
    from backend.domain.models.month import Month
    month = Month(ano, mes)
    assert month.source == origem
    assert month.satellite == satelite


# ---------------------------------------------------------------- classe de intensidade
@TDD
@pytest.mark.parametrize("frp, sensor, confianca, classe", [
    (4.9, "VIIRS", "nominal", "low"),
    (5.0, "VIIRS", "nominal", "medium"),
    (24.9, "VIIRS", "nominal", "medium"),
    (25.0, "VIIRS", "nominal", "high"),
    (10.0, "VIIRS", "alta", "high"),          # pixel saturado: o FRP sai menor que o real
    (10.0, "MODIS", "alta", "medium"),        # no MODIS, confiança alta não é saturação
])
def test_classe_de_intensidade(frp, sensor, confianca, classe, alert_rules):
    from backend.domain.intensity import intensity_class
    assert intensity_class(frp, sensor, confianca, alert_rules["intensity"]) == classe


# ---------------------------------------------------------------- nível de alerta
@TDD
@pytest.mark.parametrize("agora, mediana, p75, ultimos, anteriores, nivel", [
    (100, 40, 50, [20, 25, 30], [5, 10, 15], "critical"),   # 2,5× a mediana e subindo
    (80, 40, 50, [20, 25, 30], [5, 10, 15], "critical"),    # exatamente 2× conta
    (100, 40, 50, [10, 10, 10], [20, 20, 20], "attention"),  # acima do P75, mas caindo
    (51, 40, 50, [5, 5, 5], [5, 5, 5], "attention"),
    (45, 40, 50, [5, 5, 5], [5, 5, 5], "normal"),
])
def test_nivel_de_alerta(agora, mediana, p75, ultimos, anteriores, nivel, alert_rules):
    from backend.domain.alert import alert_level
    assert alert_level(agora, mediana, p75, ultimos, anteriores, alert_rules) == nivel


# ---------------------------------------------------------------- janelas do normal (±15 dias)
@TDD
def test_janelas_de_referencia():
    from backend.domain.windows import reference_windows
    w = reference_windows(date(2026, 11, 14), window_days=7, neighbor_days=15, years=range(2012, 2026))
    assert len(w) == 14 * 31                       # 31 posições (−15 a +15 dias) em cada um dos 14 anos
    assert w[0] == (date(2012, 10, 24), date(2012, 10, 30))
    assert all((fim - ini).days == 6 for ini, fim in w)


@TDD
def test_janela_de_29_de_fevereiro_em_ano_comum():
    from backend.domain.windows import reference_windows
    w = reference_windows(date(2024, 2, 29), window_days=7, neighbor_days=0, years=[2023])
    assert w == [(date(2023, 2, 22), date(2023, 2, 28))]


# ---------------------------------------------------------------- IDs H3
def test_id_h3_sai_como_texto_e_volta_igual():
    from h3 import int_to_str as cell_to_text
    cell = int("86a8100c7ffffff", 16)
    texto = cell_to_text(cell)
    assert texto == "86a8100c7ffffff"
    assert int(json.loads(json.dumps({"h3": texto}))["h3"], 16) == cell
    assert float(cell) != cell  # como número, o JSON perderia precisão (o motivo da regra)

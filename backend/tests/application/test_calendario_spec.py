"""Especificação TDD do caso de uso do calendário (camada de aplicação, arquitetura hexagonal).

O caso de uso fala com o banco só por uma **porta** (`AggregatesPort`). Aqui ela é um adaptador falso,
em memória: o teste roda sem Postgres. O adaptador de verdade (Postgres) tem o próprio teste de integração.

Fase vermelha do TDD: falha até `firesync_api.application.calendar` existir (ver test_dominio_spec.py).
"""
import pytest

TDD = pytest.mark.xfail(strict=True, reason="TDD: caso de uso ainda não implementado")


class AggregatesFake:
    """Adaptador falso da porta de agregados. Contagens brutas por (bioma, ano, mês, período)."""

    def __init__(self, counts, factors):
        self.counts, self.factors = counts, factors

    def raw_counts(self, cells, start, end):
        return [dict(region_id=1, year=y, month=m, daynight=p, raw_count=n)
                for (y, m, p), n in self.counts.items() if start <= f"{y}-{m:02d}" <= end]

    def scenario_factors(self, region_id, month, daynight):
        return self.factors[(month, daynight)]


@TDD
def test_calendario_preenche_zeros_e_aplica_os_cenarios():
    from firesync_api.application.calendar import CalendarService

    repo = AggregatesFake(
        counts={(2011, 12, "D"): 10, (2012, 2, "D"): 70},          # jan/2012 sem focos, mar/2012 também
        factors={(12, "D"): [4.0, 5.0, 6.0], (1, "D"): [4.0, 5.0, 6.0]},
    )
    meses = CalendarService(repo).months(cells=[1], start="2011-12", end="2012-03")

    assert [m.month for m in meses] == ["2011-12", "2012-01", "2012-02", "2012-03"]
    dez, jan, fev, mar = meses
    assert dez.source == "estimated_modis" and dez.detections == pytest.approx(50)   # 10 × mediana(4, 5, 6)
    assert dez.band_low < dez.detections < dez.band_high
    assert jan.source == "estimated_modis" and jan.detections == 0                     # zero, não "sem dados"
    assert fev.source == "observed_viirs" and fev.detections == 70 and fev.band_low is None
    assert mar.detections == 0

"""Calendário pela porta de histórico; mesmos valores da especificação da main."""
from datetime import date

import pytest

from backend.domain.models.area import Area
from backend.domain.models.snapshot import HistorySnapshot
from backend.application.calendar import CalendarService
from tests.fakes.history import FakeHistoryRepository


def test_calendario_preenche_zeros_e_aplica_os_cenarios():
    snapshot = HistorySnapshot(
        meta={"last_month": "2012-03"},
        area={"biomes": [{"region_id": 1}]},
        coverage={"status": "full"},
        counts=({"region_id": 1, "year": 2011, "month": 12, "daynight": "D", "raw_count": 10, "satellite": "Aqua"},
                {"region_id": 1, "year": 2012, "month": 2, "daynight": "D", "raw_count": 70, "satellite": "SNPP"}),
        factors=tuple({"region_id": 1, "month": month, "daynight": "D", "calibration_year": year, "factor": factor}
                      for month in (1, 12) for year, factor in zip((2013, 2014, 2015), (4.0, 5.0, 6.0))),
        periods=({"region_id": 1, "satellite": "Aqua", "start": date(2011, 12, 1), "end": date(2012, 1, 31)},
                 {"region_id": 1, "satellite": "SNPP", "start": date(2012, 2, 1), "end": date(2012, 3, 31)}),
        missing=frozenset(), provisional=frozenset(),
    )
    service = CalendarService(FakeHistoryRepository(snapshot), clock=lambda: date(2026, 11, 14))
    months = service.calculate(Area("region", region_id=1), "2011-12", "2012-03")["months"]

    assert [month["month"] for month in months] == ["2011-12", "2012-01", "2012-02", "2012-03"]
    december, january, february, march = months
    assert december["source"] == "estimated_modis" and december["detections"] == pytest.approx(50)
    assert december["band_low"] < december["detections"] < december["band_high"]
    assert january["source"] == "estimated_modis" and january["detections"] == 0
    assert february["source"] == "observed_viirs" and february["detections"] == 70 and february["band_low"] is None
    assert march["detections"] == 0

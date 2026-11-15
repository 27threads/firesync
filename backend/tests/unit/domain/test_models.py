import json
import pytest
from backend.domain.models.area import Area
from backend.domain.models.month import Month
from backend.domain.models.error import CalendarError
from backend.domain.calculations.statistics import percentile


@pytest.mark.parametrize("value", ["2020-00", "2020-13", "20-01", "2020-1", "2020-01-01", None])
def test_invalid_month(value):
    with pytest.raises(CalendarError):
        Month.parse(value)


@pytest.mark.parametrize("value,satellite", [("2012-01", "Aqua"), ("2012-02", "SNPP"), ("2026-10", "SNPP"), ("2026-11", "N20")])
def test_sensor_boundaries(value, satellite):
    assert Month.parse(value).satellite == satellite


def test_year_boundary():
    assert str(Month(2020, 12).next()) == "2021-01"


@pytest.mark.parametrize("kwargs", [{"type":"region", "region_id":True}, {"type":"point", "lat":float('nan'),"lon":0,"radius_km":1}, {"type":"point","lat":0,"lon":0,"radius_km":201}, {"type":"bad"}])
def test_invalid_area(kwargs):
    with pytest.raises(CalendarError):
        Area(**kwargs)


def test_percentile_is_linear_and_scenarios_not_fixed():
    assert percentile([0, 10, 30], 5) == 1
    assert percentile([0, 10, 30], 95) == pytest.approx(28)
    assert percentile([7], 95) == 7
    assert percentile([0, 100], 50) == 50


def test_h3_json_does_not_lose_precision():
    cell = "86a8100c7ffffff"
    assert json.loads(json.dumps({"h3": cell}))["h3"] == cell

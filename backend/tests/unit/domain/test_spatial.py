import h3
import pytest
from firesync_backend.domain.models.area import Area
from firesync_backend.domain.models.error import CalendarError
from firesync_backend.domain.calculations.spatial import cells_for_area


def test_small_area_uses_one_cell():
    cells = cells_for_area(Area('point', lat=-3, lon=-60, radius_km=1))
    assert len(cells) >= 1
    assert all(h3.get_resolution(c) == 6 for c in cells)


@pytest.mark.parametrize('ring', [ [[0,0],[1,0],[1,1],[0,1]], [[0,0],[1,1],[1,0],[0,1],[0,0]], [[0,0],[181,0],[181,1],[0,0]] ])
def test_invalid_ring_rejected(ring):
    with pytest.raises(CalendarError, match='Invalid'):
        cells_for_area(Area('geojson', geometry={'type':'Polygon','coordinates':[ring]}))


def test_large_area_rejected_before_fine_grid():
    with pytest.raises(CalendarError) as error:
        cells_for_area(Area('geojson', geometry={'type':'Polygon','coordinates':[[[-80,-50],[-30,-50],[-30,10],[-80,10],[-80,-50]]]}))
    assert error.value.code == 'area_too_large'

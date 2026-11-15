from contextlib import contextmanager
from dataclasses import replace
from datetime import date, datetime, timedelta, UTC

import h3

from backend.domain.models.error import CalendarError
from backend.domain.calculations.spatial import cells_for_area
from tests.unit.services.test_calendar import fixture, count, factors

NOW = datetime(2026, 11, 14, 15, tzinfo=UTC)
CELL = '86a8100c7ffffff'


class FakeApiRepository:
    def __init__(self):
        self.snapshot = fixture([dict(count(2003, 1, 5), frp_sum=10),
                                 dict(count(2026, 11, 7), frp_sum=20)],
                                factors(1, {2013: 2, 2014: 4}),
                                meta={'last_month': '2026-11', 'updated_at': '2026-11-14T15:00:00Z',
                                      'data_version': '2026-11-14T14:00:00Z', 'h3_resolution': 6, 'scale': 'VIIRS'})
        self.detection_count = 1
        self.map_count = 1
        self.risk = None  # notas de risco por celula res 4 (risco_celulas); None = sem notas frescas
        self.cell_daily = {}  # contagens diárias por célula res 4, para o nível de urgência do mapa
        self.failure = None

    @contextmanager
    def read(self):
        if self.failure:
            raise self.failure
        yield self

    def meta(self):
        return self.snapshot.meta

    def regions(self):
        return [{'region_id': 1, 'name': 'Test', 'source': 'Test fixture', 'bbox': [-61, -4, -59, -2]}]

    def history(self, area):
        if area.type == 'region' and area.region_id != 1:
            raise CalendarError('region_not_found', 'Region not found.')
        if area.type != 'region':
            cells_for_area(area)
        if area.type == 'point' and area.lat > 0:
            return replace(self.snapshot, coverage={'status': 'none', 'covered_fraction': 0, 'message': 'No data.'})
        return self.snapshot

    def recent(self, snapshot):
        return {'data_through': date(2026, 11, 14), 'daily': {date(2026, 11, 14): 7},
                'high': {date(2026, 11, 14): 1},
                'coverage': [(date(2012, 2, 1), date(2026, 11, 14))], 'missing': set()}

    def detections(self, snapshot, first, final):
        return self.detection_count, ([{'satellite': 'N20', 'latitude': -3, 'longitude': -60,
            'acquired_utc': '2026-11-14T12:00:00Z', 'confidence': 'high', 'frp': 3,
            'daynight': 'D', 'quality': 'NRT', 'source_file': 'fixture.csv'}]
            if self.detection_count <= 500_000 else [])

    def map_rows(self, query, now):
        return {'total': self.map_count, 'expires_at': now + timedelta(hours=query.hours),
                'hexagons': [{'h3': h3.str_to_int(CELL), 'detections': self.map_count,
                              'n_low': 0, 'n_medium': 0, 'n_high': self.map_count}],
                'points': [{'satellite': 'N20', 'longitude': -60, 'latitude': -3,
                            'acquired_utc': '2026-11-14T12:00:00Z', 'confidence': 'high',
                            'intensity': 'high', 'daynight': 'D'}] if self.map_count <= 50_000 else None,
                'data_through': date(2026, 11, 14), 'coverage_start': date(2012, 2, 1),
                'cell_daily': self.cell_daily, 'risk': self.risk}

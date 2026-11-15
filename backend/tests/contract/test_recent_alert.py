from datetime import date, timedelta

import pytest

import h3

from tests.contract.test_api_contract import REQUEST, client, repository  # noqa: F401 -- shared HTTP fixtures
from tests.fakes.api import CELL


@pytest.mark.parametrize('count,expected', [(2, 'attention'), (9, 'attention'), (10, 'critical')])
def test_calendar_exposes_continuous_floor(client, repository, monkeypatch, count, expected, alert_rules):  # noqa: F811 -- pytest injects shared fixtures
    today = date(2026, 11, 14)
    # Every historical seven-day window has exactly one detection.
    daily = {date(2025, 10, 1) + timedelta(days=7 * i): 1 for i in range(10)}
    daily[today] = count
    monkeypatch.setattr(repository, 'recent', lambda snapshot: {
        'data_through': today, 'daily': daily, 'high': {},
        'coverage': [(date(2025, 10, 1), date(2025, 12, 1)), (today - timedelta(days=6), today)],
        'missing': set(),
    })
    response = client.post('/api/v1/calendar', json=REQUEST)
    assert response.status_code == 200
    recent = response.json()['recent']
    assert recent['last_7_days']['typical_median'] == 1
    assert recent['alert_level'] == expected
    assert recent['alert_rules_version'] == alert_rules['version']


@pytest.mark.parametrize('zoom', [4, 5, 7, 9])
def test_map_marks_urgent_cells_and_lists_them_first(client, repository, zoom, alert_rules):  # noqa: F811 -- pytest injects shared fixtures
    """RFC 0003: no mapa de focos recentes, cada hexágono carrega o nível da sua célula res 4."""
    today = date(2026, 11, 14)
    parent = h3.cell_to_parent(CELL, 4)
    daily = {date(year, 11, 14) + timedelta(days=offset): 1 for year in range(2012, 2026) for offset in range(-30, 30)}
    for i, value in enumerate([0, 0, 0, 2, 4, 10, 30]):
        daily[today - timedelta(days=6 - i)] = value
    repository.cell_daily = {parent: daily}
    body = client.get(f'/api/v1/detections/recent?bbox=-61,-4,-59,-2&zoom={zoom}&hours=24').json()
    alerts = body['alerts']
    assert alerts['alert_rules_version'] == alert_rules['version'] and alerts['data_through'] == '2026-11-14'
    assert alerts['horizon_days'] == 14 and alerts['overall_share'] == pytest.approx(0.042)
    assert [p['h3'] for p in alerts['priority']] == [parent]
    assert alerts['priority'][0]['alert_level'] == 'critical'
    assert alerts['priority'][0]['share_followed_by_high'] == pytest.approx(0.266)
    if body['mode'] == 'hexagons':
        properties = body['features'][0]['properties']
        assert properties['alert_cell'] == parent and properties['alert_level'] == 'critical'


def test_map_without_cell_history_has_an_empty_priority_list(client):  # noqa: F811 -- pytest injects shared fixtures
    body = client.get('/api/v1/detections/recent?bbox=-61,-4,-59,-2&zoom=4&hours=24').json()
    assert body['alerts']['priority'] == []
    assert body['features'][0]['properties']['alert_level'] is None

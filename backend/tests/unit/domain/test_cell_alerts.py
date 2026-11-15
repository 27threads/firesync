"""Nível de urgência por célula H3 res 4 no mapa de focos recentes (RFC 0003, opção D2). DADOS INVENTADOS."""
from datetime import date, timedelta

import h3
import pytest

TODAY = date(2026, 11, 14)
VIIRS_START = date(2012, 2, 1)
CELL4 = h3.latlng_to_cell(-10.0, -55.0, 4)
OTHER4 = h3.latlng_to_cell(-12.0, -50.0, 4)


def history(per_day, years=range(2012, 2026), around=TODAY, span=40):
    """Contagens constantes por dia, em torno da mesma data, nos anos dados (padrão: todos os anos de referência)."""
    daily = {}
    for year in years:
        for offset in range(-span, span):
            daily[around.replace(year=year) + timedelta(days=offset)] = per_day
    return daily


@pytest.mark.parametrize('level,share', [('normal', 0.026), ('attention', 0.107), ('critical', 0.266)])
def test_historical_outcome_by_level(level, share, alert_rules):
    from backend.domain.alert import historical_outcome
    outcome = historical_outcome(level, alert_rules)
    assert outcome['share_followed_by_high'] == share
    assert outcome['overall_share'] == pytest.approx(0.042)
    assert outcome['horizon_days'] == 14


def test_no_level_means_no_outcome(alert_rules):
    from backend.domain.alert import historical_outcome
    assert historical_outcome(None, alert_rules) is None


@pytest.mark.parametrize('week', [
    [0, 0, 0, 0, 0, 0, 0],      # quiet week
    [0, 0, 0, 3, 3, 3, 3],      # above P75, not double
    [0, 0, 0, 2, 4, 10, 30],    # critical, rising
    [30, 10, 4, 2, 0, 0, 0],    # high but falling
    [5, 5, 5, 5, 5, 5, 5],      # high, flat trend
])
def test_cell_level_is_the_same_rule_as_recent(week, alert_rules):
    """Paridade: na mesma série, a célula do mapa e o `recent` da área dão o mesmo nível."""
    from backend.domain.calculations.cell_alerts import cell_alerts
    from backend.domain.calculations.recent import recent_result
    daily = history(1)
    for i, value in enumerate(week):
        daily[TODAY - timedelta(days=6 - i)] = value
    expected = recent_result(TODAY, daily, {}, [(VIIRS_START, TODAY)], set(), alert_rules)
    result = cell_alerts(TODAY, {CELL4: daily}, alert_rules, VIIRS_START)[CELL4]
    assert result['alert_level'] == expected['alert_level']
    assert result['detections_7d'] == expected['last_7_days']['detections']
    assert result['typical_median'] == expected['last_7_days']['typical_median']


def test_cell_uses_only_previous_years_and_windows_after_viirs_start(alert_rules):
    from backend.domain.calculations.cell_alerts import cell_alerts
    daily = history(1)
    daily.update(history(100, years=(2027,)))          # um ano futuro nunca entra no normal
    daily[TODAY] = 30
    for i in range(1, 7):
        daily[TODAY - timedelta(days=i)] = 0
    result = cell_alerts(TODAY, {CELL4: daily}, alert_rules, VIIRS_START)[CELL4]
    assert result['typical_median'] == 7
    jan = date(2026, 1, 10)                            # janelas de jan/2012 começam antes do VIIRS
    early = cell_alerts(jan, {CELL4: {jan: 12}}, alert_rules, VIIRS_START)[CELL4]
    plain = cell_alerts(jan, {CELL4: {jan: 12}}, alert_rules, date(2003, 1, 1))[CELL4]
    assert early['n_windows'] < plain['n_windows']


def test_cell_without_history_has_no_level(alert_rules):
    from backend.domain.calculations.cell_alerts import cell_alerts
    result = cell_alerts(date(2012, 3, 1), {CELL4: {date(2012, 3, 1): 5}}, alert_rules, VIIRS_START)[CELL4]
    assert result['alert_level'] is None and result['share_followed_by_high'] is None


def test_critical_cell_carries_the_historical_share(alert_rules):
    from backend.domain.calculations.cell_alerts import cell_alerts
    daily = history(1)
    for i, value in enumerate([0, 0, 0, 2, 4, 10, 30]):
        daily[TODAY - timedelta(days=6 - i)] = value
    result = cell_alerts(TODAY, {CELL4: daily}, alert_rules, VIIRS_START)[CELL4]
    assert result['alert_level'] == 'critical'
    assert result['share_followed_by_high'] == 0.266


def test_history_ranges_cover_every_reference_window_and_the_current_week(alert_rules):
    from backend.domain.calculations.cell_alerts import history_ranges
    from backend.domain.windows import reference_windows
    ranges = history_ranges(TODAY, alert_rules)
    covered = lambda day: any(first <= day <= last for first, last in ranges)  # noqa: E731
    base = alert_rules['baseline']
    for first, last in reference_windows(TODAY, base['window_days'], base['neighbor_days'],
                                         range(base['reference_years_from'], TODAY.year)):
        assert covered(first) and covered(last)
    assert all(covered(TODAY - timedelta(days=i)) for i in range(7))
    assert not covered(TODAY + timedelta(days=1))


def test_map_result_marks_hexagons_with_their_cell_level_and_lists_priorities(alert_rules):
    from backend.domain.calculations.map_features import map_result
    from backend.domain.models.map_query import MapQuery
    critical, attention = history(1), history(1)
    for i, value in enumerate([0, 0, 0, 2, 4, 10, 30]):
        critical[TODAY - timedelta(days=6 - i)] = value
    for i, value in enumerate([0, 0, 0, 3, 3, 3, 3]):
        attention[TODAY - timedelta(days=6 - i)] = value
    child = h3.cell_to_children(CELL4, 6)[0]
    rows = {'total': 3, 'points': None, 'expires_at': None,
            'hexagons': [{'h3': h3.str_to_int(child), 'detections': 2, 'n_low': 2, 'n_medium': 0, 'n_high': 0},
                         {'h3': h3.str_to_int(h3.cell_to_children(OTHER4, 6)[0]), 'detections': 1,
                          'n_low': 1, 'n_medium': 0, 'n_high': 0}],
            'data_through': TODAY, 'coverage_start': VIIRS_START,
            'cell_daily': {CELL4: critical, OTHER4: attention}}
    body = map_result(MapQuery.parse('-60,-15,-45,-5', '24', '5'), rows, 'x', alert_rules)
    levels = {f['properties']['alert_cell']: f['properties']['alert_level'] for f in body['features']}
    assert levels == {CELL4: 'critical', OTHER4: 'attention'}
    alerts = body['alerts']
    assert alerts['data_through'] == '2026-11-14' and alerts['alert_rules_version'] == alert_rules['version']
    assert [p['h3'] for p in alerts['priority']] == [CELL4, OTHER4]      # Crítico antes de Atenção
    top = alerts['priority'][0]
    assert top['share_followed_by_high'] == 0.266
    lat, lon = h3.cell_to_latlng(CELL4)
    assert top['center'] == [pytest.approx(lon), pytest.approx(lat)]


@pytest.mark.parametrize('rules_given,cell_daily', [(False, {}), (True, None)])
def test_map_without_alert_data_keeps_the_old_shape(rules_given, cell_daily, alert_rules):
    """Sem regras, ou com células demais para calcular (cell_daily None), o mapa sai como antes, sem `alerts`."""
    from backend.domain.calculations.map_features import map_result
    from backend.domain.models.map_query import MapQuery
    child = h3.cell_to_children(CELL4, 6)[0]
    rows = {'total': 1, 'points': None, 'expires_at': None,
            'hexagons': [{'h3': h3.str_to_int(child), 'detections': 1, 'n_low': 1, 'n_medium': 0, 'n_high': 0}],
            'data_through': TODAY, 'coverage_start': VIIRS_START, 'cell_daily': cell_daily}
    body = map_result(MapQuery.parse('-60,-15,-45,-5', '24', '4'), rows, 'x', alert_rules if rules_given else None)
    assert 'alerts' not in body
    assert set(body['features'][0]['properties']) == {'h3', 'detections', 'n_low', 'n_medium', 'n_high'}


def test_normal_cells_are_not_in_the_priority_list(alert_rules):
    from backend.domain.calculations.map_features import map_result
    from backend.domain.models.map_query import MapQuery
    child = h3.cell_to_children(CELL4, 6)[0]
    rows = {'total': 1, 'points': None, 'expires_at': None,
            'hexagons': [{'h3': h3.str_to_int(child), 'detections': 1, 'n_low': 1, 'n_medium': 0, 'n_high': 0}],
            'data_through': TODAY, 'coverage_start': VIIRS_START, 'cell_daily': {CELL4: history(1)}}
    body = map_result(MapQuery.parse('-60,-15,-45,-5', '24', '4'), rows, 'x', alert_rules)
    assert body['features'][0]['properties']['alert_level'] == 'normal'
    assert body['alerts']['priority'] == []

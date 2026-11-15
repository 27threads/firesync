from copy import deepcopy

import pytest


@pytest.mark.parametrize('count,median,p75,last,previous,expected', [
    (2, 1, 1, [0, 0, 2], [0, 0, 0], 'attention'),
    (9, 1, 2, [0, 0, 9], [0, 0, 0], 'attention'),
    (10, 1, 2, [0, 0, 10], [0, 0, 0], 'critical'),
    (9, 0, 0, [0, 0, 9], [0, 0, 0], 'attention'),
    (10, 0, 0, [0, 0, 10], [0, 0, 0], 'critical'),
    (0, 0, 0, [0, 0, 0], [0, 0, 0], 'normal'),
    (19, 10, 15, [0, 0, 19], [0, 0, 0], 'attention'),
    (20, 10, 15, [0, 0, 20], [0, 0, 0], 'critical'),
    (10, 1, 2, [0, 0, 5], [0, 0, 5], 'attention'),
    (10, 1, 2, [0, 0, 4], [0, 0, 6], 'attention'),
    (10, 1, 2, [4, 2, 0], [0, 0, 4], 'critical'),
    (5, 3, 5, [0, 0, 5], [0, 0, 0], 'normal'),
    (10, None, None, [0, 0, 10], [0, 0, 0], None),
])
def test_continuous_floor_and_strict_trend(count, median, p75, last, previous, expected, alert_rules):
    from backend.domain.alert import alert_level
    assert alert_level(count, median, p75, last, previous, alert_rules) == expected


def test_thresholds_are_read_from_configuration(alert_rules):
    from backend.domain.alert import alert_level
    rules = deepcopy(alert_rules)
    rules['levels']['critical'].update(min_detections=20, requires_rising_trend=False)
    assert alert_level(10, 1, 2, [0, 0, 5], [0, 0, 5], rules) == 'attention'
    assert alert_level(20, 1, 2, [0, 0, 10], [0, 0, 10], rules) == 'critical'

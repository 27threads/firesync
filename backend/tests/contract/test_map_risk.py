from datetime import date, datetime, UTC

import h3
import pytest

from tests.contract.test_api_contract import client, repository  # noqa: F401 -- shared HTTP fixtures
from tests.fakes.api import CELL

PARENT = h3.cell_to_parent(CELL, 4)
URL = '/api/v1/detections/recent?bbox=-61,-4,-59,-2&zoom=4&hours=24'


def scored(prob):
    return {'data_ref': date(2026, 11, 14), 'scored_at': datetime(2026, 11, 14, 15, 5, tzinfo=UTC),
            'model_version': 'gb-2026-11-14-s42', 'by_cell': {PARENT: prob}}


@pytest.mark.parametrize('prob,tier', [(0.72, 'very_high'), (0.6, 'very_high'), (0.59, 'high'), (0.4, 'high'),
                                       (0.39, 'medium'), (0.2, 'medium'), (0.19, 'lower')])
def test_hexagon_carries_the_risk_of_its_resolution_4_cell(client, repository, prob, tier):  # noqa: F811 -- pytest injects shared fixtures
    repository.risk = scored(prob)
    properties = client.get(URL).json()['features'][0]['properties']
    assert properties['risk_prob'] == pytest.approx(prob) and properties['risk_tier'] == tier


def test_alerts_risk_block_has_the_legend_and_when_it_was_scored(client, repository, risk_rules):  # noqa: F811
    repository.risk = scored(0.72)
    risk = client.get(URL).json()['alerts']['risk']
    assert risk['scored_at'] == '2026-11-14T15:05:00Z' and risk['data_ref'] == '2026-11-14'
    assert risk['model_version'] == 'gb-2026-11-14-s42' and risk['horizon_days'] == 14
    assert risk['rules_version'] == risk_rules['version']
    assert risk['tiers'][0] == {'tier': 'very_high', 'min_prob': 0.6, 'historical_share': 0.82}


def test_high_risk_cell_enters_the_priority_list_with_its_risk(client, repository):  # noqa: F811
    repository.risk = scored(0.72)
    priority = client.get(URL).json()['alerts']['priority']
    assert [(p['h3'], p['risk_tier']) for p in priority] == [(PARENT, 'very_high')]
    assert priority[0]['risk_prob'] == pytest.approx(0.72)


def test_cell_without_a_score_has_null_risk_while_the_block_exists(client, repository):  # noqa: F811
    repository.risk = {**scored(0.72), 'by_cell': {}}
    body = client.get(URL).json()
    assert body['alerts']['risk']['horizon_days'] == 14
    assert body['features'][0]['properties']['risk_tier'] is None and body['features'][0]['properties']['risk_prob'] is None


def test_without_fresh_scores_the_map_is_as_before(client, repository):  # noqa: F811
    repository.risk = None
    body = client.get(URL).json()
    assert 'risk' not in body['alerts']
    assert 'risk_prob' not in body['features'][0]['properties'] and 'risk_tier' not in body['features'][0]['properties']

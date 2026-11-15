"""RFC 0003: faixas de risco por célula, vindas do modelo treinado e lidas da tabela `risco_celulas`."""
from datetime import date, datetime, UTC

import pytest

from backend.domain.calculations.map_features import alerts_block
from backend.domain.calculations.risk import RISK_ORDER, risk_block, risk_tier


@pytest.mark.parametrize('prob,tier', [(1.0, 'very_high'), (0.6, 'very_high'), (0.59, 'high'), (0.4, 'high'),
                                       (0.39, 'medium'), (0.2, 'medium'), (0.19, 'lower'), (0.0, 'lower')])
def test_tier_follows_the_cutoffs_of_the_config(prob, tier, risk_rules):
    assert risk_tier(prob, risk_rules) == tier


def test_risk_block_carries_the_legend_and_provenance(risk_rules):
    risk = {'data_ref': date(2026, 11, 14), 'scored_at': datetime(2026, 11, 14, 15, 5, tzinfo=UTC),
            'model_version': 'gb-2026-11-14-s42', 'by_cell': {}}
    block = risk_block(risk, risk_rules)
    assert block['data_ref'] == '2026-11-14' and block['scored_at'] == '2026-11-14T15:05:00Z'
    assert block['model_version'] == 'gb-2026-11-14-s42' and block['horizon_days'] == 14
    assert block['rules_version'] == risk_rules['version']
    assert [t['tier'] for t in block['tiers']] == ['very_high', 'high', 'medium', 'lower']
    assert block['tiers'][0] == {'tier': 'very_high', 'min_prob': 0.6, 'historical_share': 0.82}


def test_no_risk_block_without_scores(risk_rules):
    assert risk_block(None, risk_rules) is None


def levels(*cells):
    return {cell: {'alert_level': level, 'detections_7d': n, 'typical_median': 5.0, 'share_followed_by_high': 0.1}
            for cell, level, n in cells}


def rows(cells, by_cell):
    return {'cell_levels': levels(*cells), 'cell_daily': None, 'data_through': date(2026, 11, 14),
            'coverage_start': date(2012, 2, 1),
            'risk': {'data_ref': date(2026, 11, 14), 'scored_at': datetime(2026, 11, 14, 15, tzinfo=UTC),
                     'model_version': 'v', 'by_cell': by_cell}}


A, B, C = '84a8101ffffffff', '84a8103ffffffff', '84a8105ffffffff'


def test_priority_is_ordered_by_risk_tier_and_the_alert_stays_as_a_seal(alert_rules, risk_rules):
    block, _ = alerts_block(rows([(A, 'critical', 30), (B, 'attention', 12), (C, 'normal', 3)],
                                 {A: 0.30, B: 0.72, C: 0.65}), alert_rules, risk_rules)
    assert [p['h3'] for p in block['priority']] == [B, C, A]       # very high first, even with a milder alert
    assert [p['risk_tier'] for p in block['priority']] == ['very_high', 'very_high', 'medium']
    assert block['priority'][0]['alert_level'] == 'attention' and block['priority'][0]['risk_prob'] == pytest.approx(0.72)


def test_cell_with_high_risk_is_listed_even_when_its_alert_is_normal(alert_rules, risk_rules):
    block, _ = alerts_block(rows([(A, 'normal', 3)], {A: 0.45}), alert_rules, risk_rules)
    assert [(p['h3'], p['risk_tier'], p['alert_level']) for p in block['priority']] == [(A, 'high', 'normal')]


def test_cell_with_low_risk_and_normal_alert_stays_out(alert_rules, risk_rules):
    block, _ = alerts_block(rows([(A, 'normal', 3)], {A: 0.05}), alert_rules, risk_rules)
    assert block['priority'] == []


def test_without_scores_the_priority_is_the_old_one(alert_rules, risk_rules):
    body = rows([(A, 'critical', 30), (B, 'attention', 12)], {})
    body['risk'] = None
    block, _ = alerts_block(body, alert_rules, risk_rules)
    assert [p['h3'] for p in block['priority']] == [A, B] and 'risk' not in block
    assert all('risk_tier' not in p for p in block['priority'])


def test_risk_order_ranks_tiers_from_the_highest():
    assert sorted(RISK_ORDER, key=RISK_ORDER.get) == ['very_high', 'high', 'medium', 'lower']

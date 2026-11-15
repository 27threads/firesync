"""API/backtest parity from one synthetic area's daily observations (issue #64)."""
from copy import deepcopy
from datetime import date, timedelta
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from backend.domain.calculations.recent import recent_result


@pytest.fixture
def backtest():
    path = Path(__file__).resolve().parents[4] / 'data-pipeline/validacao/backtest_alerta.py'
    spec = importlib.util.spec_from_file_location('alert_parity_backtest', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compare_daily(backtest, monkeypatch, today, daily, rules):
    # Evaluate one date without changing the study's reference years or coverage.
    # This also exercises leap day, which is not a Sunday in the study's last year.
    monkeypatch.setattr(backtest, 'PRIMEIRO_DOMINGO', today)
    monkeypatch.setattr(backtest, 'ULTIMO_DOMINGO', today)
    matrix = np.zeros((1, (backtest.FIM - backtest.INICIO).days + 1), dtype=np.float32)
    for day, value in daily.items():
        matrix[0, (day - backtest.INICIO).days] = value
    weeks, stats = backtest.avaliar(matrix, rules)
    index = weeks.index(today)
    result = recent_result(today, daily, {}, [(backtest.INICIO, today)], set(), rules)
    week = result['last_7_days']
    for public, internal in [('detections', 's7'), ('typical_median', 'med7'), ('typical_p75', 'p75')]:
        assert week[public] == pytest.approx(float(stats[internal][index, 0]))
    trend_days = rules['levels']['critical']['trend_days']
    last = sum(daily.get(today - timedelta(days=i), 0) for i in range(trend_days))
    previous = sum(daily.get(today - timedelta(days=i), 0) for i in range(trend_days, 2 * trend_days))
    assert bool(stats['sobe'][index, 0]) == (last > previous)
    expected = ('normal', 'attention', 'critical')[backtest.nivel_da_regra(stats, rules)[index, 0]]
    assert result['alert_level'] == expected
    assert result['alert_rules_version'] == rules['version']
    return result


@pytest.mark.parametrize('baseline,current,expected', [
    (0, [0, 0, 0, 0, 0, 0, 9], 'attention'),
    (0, [0, 0, 0, 0, 0, 0, 10], 'critical'),
    (1, [0, 0, 0, 0, 0, 0, 2], 'attention'),
    (7, [0, 0, 0, 0, 0, 0, 14], 'critical'),
    (7, [0, 0, 0, 0, 0, 0, 7], 'normal'),
    (1, [0, 0, 0, 5, 0, 0, 5], 'attention'),
])
def test_daily_series_thresholds(backtest, monkeypatch, alert_rules, baseline, current, expected):
    today = date(2024, 8, 4)
    daily = {backtest.INICIO + timedelta(days=i): baseline
             for i in range(0, (backtest.FIM - backtest.INICIO).days + 1, 7)}
    # Poison the current year's earlier data: neither baseline may include it.
    for i in range(31):
        daily[today - timedelta(days=7 + i)] = 10000
    daily.update({today - timedelta(days=6 - i): value for i, value in enumerate(current)})
    result = compare_daily(backtest, monkeypatch, today, daily, alert_rules)
    assert result['last_7_days']['typical_median'] == baseline
    assert result['last_7_days']['typical_p75'] == baseline
    assert result['alert_level'] == expected


@pytest.mark.parametrize('today', [date(2024, 1, 7), date(2024, 2, 4), date(2024, 12, 15)])
def test_daily_series_calendar_edges(backtest, monkeypatch, alert_rules, today):
    rng = np.random.default_rng(64)
    values = rng.poisson(2, (backtest.FIM - backtest.INICIO).days + 1)
    daily = {backtest.INICIO + timedelta(days=i): int(value) for i, value in enumerate(values)}
    compare_daily(backtest, monkeypatch, today, daily, alert_rules)


def test_leap_day_keeps_february_29_in_leap_reference_years(backtest, monkeypatch, alert_rules):
    rules = deepcopy(alert_rules)
    rules['baseline']['neighbor_days'] = 0
    daily = {date(year, 2, 29): 100 for year in (2012, 2016, 2020, 2024)}
    result = compare_daily(backtest, monkeypatch, date(2024, 2, 29), daily, rules)
    assert result['last_7_days']['n_windows'] == 12
    assert result['last_7_days']['typical_p75'] == 25


def test_daily_parity_reads_custom_configuration(backtest, monkeypatch, alert_rules):
    rules = deepcopy(alert_rules)
    rules['levels']['critical'].update(min_detections=20, min_ratio_to_median=3,
                                       trend_days=2, requires_rising_trend=False)
    rules['levels']['attention']['above_percentile'] = 90
    rules['baseline']['neighbor_days'] = 3
    today = date(2024, 8, 4)
    result = compare_daily(backtest, monkeypatch, today, {today - timedelta(days=3): 15}, rules)
    assert result['alert_level'] == 'attention'
    result = compare_daily(backtest, monkeypatch, today, {today - timedelta(days=3): 20}, rules)
    assert result['alert_level'] == 'critical'

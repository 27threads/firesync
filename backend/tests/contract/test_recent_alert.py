from datetime import date, timedelta

import pytest

from tests.contract.test_api_contract import REQUEST, client, repository  # noqa: F401 -- shared HTTP fixtures


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

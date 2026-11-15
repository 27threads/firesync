from datetime import date, timedelta

import pytest


def test_recent_uses_all_shifted_windows_and_covered_zero_days():
    from backend.domain.calculations.recent import recent_result
    # Constant 2/day in 2024 and 4/day in 2025: 62 windows, median 21.
    daily = {}
    for year, amount in [(2024, 2), (2025, 4)]:
        for offset in range(-40, 20):
            daily[date(year, 11, 14) + timedelta(days=offset)] = amount
    daily[date(2026, 11, 14)] = 42
    result = recent_result(date(2026, 11, 14), daily, {date(2026, 11, 14): 3},
                           [(date(2024, 1, 1), date(2026, 11, 14))], set())
    week = result['last_7_days']
    assert week == {'start': '2026-11-08', 'end': '2026-11-14', 'detections': 42,
                    'typical_median': 21, 'typical_p25': 14, 'typical_p75': 28,
                    'difference': 21, 'difference_pct': 1, 'n_years': 2,
                    'n_windows': 62, 'n_high': 3, 'high_share': 3 / 42}
    assert result['month_to_date']['typical_median'] == 42
    assert result['month_to_date']['difference_pct'] == 0


def test_recent_empty_baseline_is_not_zero_and_zero_denominators_are_null():
    from backend.domain.calculations.recent import recent_result
    today = date(2026, 11, 14)
    no_history = recent_result(today, {}, {}, [(date(2026, 1, 1), today)], set())
    assert no_history['last_7_days']['typical_median'] is None
    assert no_history['last_7_days']['difference'] is None
    assert no_history['last_7_days']['n_windows'] == 0
    zeros = recent_result(today, {}, {}, [(date(2012, 2, 1), today)], set())
    assert zeros['last_7_days']['typical_median'] == 0
    assert zeros['last_7_days']['difference_pct'] is None
    assert zeros['last_7_days']['high_share'] is None
    assert zeros['last_7_days']['n_windows'] == 434


def test_missing_days_and_cross_year_unavailable_days_exclude_reference_windows():
    from backend.domain.calculations.recent import recent_result
    result = recent_result(date(2026, 1, 5), {}, {},
                           [(date(2024, 1, 1), date(2026, 1, 5))], {date(2024, 1, 10)})
    # 2024: Jan 7..20 are valid endpoints, except Jan 10..16 (7 windows).
    # 2025: all 31 windows; the crossing into 2023 has no coverage.
    assert result['last_7_days']['n_windows'] == 38
    assert result['last_7_days']['n_years'] == 2


@pytest.mark.parametrize('frp,confidence,expected', [(4.99, 'nominal', 'low'),
    (5, 'nominal', 'medium'), (25, 'nominal', 'high'), (1, 'high', 'high')])
def test_intensity_public_values(frp, confidence, expected, alert_rules):
    from backend.domain.intensity import intensity_class
    assert intensity_class(frp, 'VIIRS', confidence, alert_rules['intensity']) == expected

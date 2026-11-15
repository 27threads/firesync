"""Alert level of each H3 resolution 4 cell for the recent-fire map (RFC 0003).

Same rule as `recent` (`alert_level`), applied to each cell's own daily VIIRS counts. Resolution 4 is the unit in
which rule v1 was backtested, so the historical outcome of each level applies to these cells. Days without a row
count as zero, as in the backtest; windows that start before VIIRS coverage are skipped.
"""
from datetime import timedelta

from backend.domain.alert import alert_level, historical_outcome
from backend.domain.calculations.statistics import percentile
from backend.domain.windows import reference_windows


def _reference_windows(data_through, rules, coverage_start):
    base = rules['baseline']
    windows = reference_windows(data_through, base['window_days'], base['neighbor_days'],
                                range(base['reference_years_from'], data_through.year))
    return [(first, last) for first, last in windows if first >= coverage_start]


def history_ranges(data_through, rules):
    """Date ranges the map needs from `agregados_diarios`: each reference year, then the current window."""
    base = rules['baseline']
    span = max(base['window_days'], 2 * rules['levels']['critical']['trend_days'])
    ranges = []
    for year in range(base['reference_years_from'], data_through.year):
        windows = reference_windows(data_through, base['window_days'], base['neighbor_days'], [year])
        ranges.append((windows[0][0], windows[-1][1]))
    ranges.append((data_through - timedelta(days=span - 1), data_through))
    return ranges


def cell_alerts(data_through, daily_by_cell, rules, coverage_start):
    """{cell: level, last-7-day detections, typical median and historical share} for each cell."""
    length = rules['baseline']['window_days']
    trend = rules['levels']['critical']['trend_days']
    windows = [[(first + timedelta(days=i)).toordinal() for i in range(length)]
               for first, _ in _reference_windows(data_through, rules, coverage_start)]
    through = data_through.toordinal()
    result = {}
    for cell, daily in daily_by_cell.items():
        counts = {day.toordinal(): value for day, value in daily.items()}
        samples = [sum(counts.get(day, 0) for day in window) for window in windows]
        week = sum(counts.get(through - i, 0) for i in range(length))
        last = [counts.get(through - i, 0) for i in range(trend)]
        previous = [counts.get(through - i, 0) for i in range(trend, 2 * trend)]
        median = percentile(samples, 50) if samples else None
        threshold = percentile(samples, rules['levels']['attention']['above_percentile']) if samples else None
        level = alert_level(week, median, threshold, last, previous, rules)
        outcome = historical_outcome(level, rules)
        result[cell] = {'alert_level': level, 'detections_7d': week, 'typical_median': median,
                        'n_windows': len(samples),
                        'share_followed_by_high': outcome['share_followed_by_high'] if outcome else None}
    return result

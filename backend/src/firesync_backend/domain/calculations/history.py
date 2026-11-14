"""Scenario-preserving historical calculations, with no HTTP or SQL dependencies."""
from collections import defaultdict
from math import fsum, isfinite

from firesync_backend.domain.models.error import CalendarError
from firesync_backend.domain.models.month import Month
from .statistics import percentile, summarize


def months_between(start, end):
    while start <= end:
        yield start
        start = start.next()


def aligned(vectors):
    """Align by calibration year; None denotes an observed/zero constant.

    Only scenarios present in every nonconstant vector can be combined.
    No missing factor is imputed, and disjoint scenarios are rejected.
    """
    sets = [set(vector) for vector in vectors if None not in vector]
    years = set.intersection(*sets) if sets else {None}
    if not years:
        raise CalendarError('invalid_data', 'No common calibration scenarios.')
    return {year: [vector[None] if None in vector else vector[year] for vector in vectors]
            for year in years}


def total(vectors):
    return {year: fsum(values) for year, values in aligned(vectors).items()}


def month_scenarios(month, rows, factors):
    selected = [row for row in rows if row['satellite'] == month.satellite]
    if any(row['raw_count'] < 0 for row in selected):
        raise CalendarError('invalid_data', 'Negative detection count.')
    raw = sum(row['raw_count'] for row in selected)
    if month.source == 'observed_viirs' or raw == 0:
        return {None: raw}, raw
    vectors = []
    for row in selected:
        if not row['raw_count']:
            continue
        condition = (row['region_id'], month.month, row['daynight'])
        available = factors.get(condition, {})
        if not available:
            raise CalendarError('invalid_data', 'Missing calibration factors.')
        vectors.append({year: row['raw_count'] * factor for year, factor in available.items()})
    return total(vectors), raw


def factor_index(rows):
    result = defaultdict(dict)
    for row in rows:
        value = row['factor']
        if not isfinite(value) or value < 0:
            raise CalendarError('invalid_data', 'Invalid calibration factor.')
        condition = (row['region_id'], row['month'], row['daynight'])
        year = row['calibration_year']
        if year in result[condition]:
            raise CalendarError('invalid_data', 'Duplicate calibration factor.')
        result[condition][year] = value
    return result


def annual_results(selected, vectors, today):
    grouped = defaultdict(list)
    for month in selected:
        grouped[month.year].append(month)
    results = []
    for year, months in grouped.items():
        sources = {month.source for month in months}
        result = summarize(total([vectors[m] for m in months]), 'estimated_modis' in sources)
        result.update(year=year, source=next(iter(sources)) if len(sources) == 1 else 'mixed',
                      complete=len(months) == 12 and year < today.year, rank=None)
        results.append(result)
    results.sort(key=lambda row: (-row['detections'], row['year']))
    rank = 0
    for result in results:
        if result['complete']:
            rank += 1
            result['rank'] = rank
    return results


def seasonality_results(years, vectors):
    result = []
    for month in range(1, 13):
        row = {'month_of_year': month, 'n_years': len(years)}
        if years:
            scenarios = aligned([vectors[Month(year, month)] for year in years])
            functions = {'median': lambda v: percentile(v, 50), 'mean': lambda v: fsum(v) / len(v),
                         'min': min, 'max': max}
            row.update({name: percentile([function(v) for v in scenarios.values()], 50)
                        for name, function in functions.items()})
        else:
            row.update(median=None, mean=None, min=None, max=None)
        result.append(row)
    return result


def anomaly(vector, references):
    if not references:
        return None, None
    absolute, relative = [], []
    for values in aligned([vector, *references]).values():
        baseline = percentile(values[1:], 50)
        absolute.append(values[0] - baseline)
        relative.append(values[0] / baseline - 1 if baseline else None)
    return percentile(absolute, 50), (None if None in relative else percentile(relative, 50))

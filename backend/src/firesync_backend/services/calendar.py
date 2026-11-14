from collections import defaultdict
from datetime import datetime, UTC
from math import fsum

from firesync_backend.domain.calculations.history import (
    aligned, annual_results, anomaly, factor_index, month_scenarios,
    months_between, seasonality_results, total,
)
from firesync_backend.domain.calculations.statistics import percentile, summarize
from firesync_backend.domain.models.error import CalendarError
from firesync_backend.domain.models.month import Month
from firesync_backend.repositories.interfaces.history import HistoryRepository


class CalendarService:
    """Historical portion of /calendar; recent monitoring is a separate delivery."""

    def __init__(self, repository: HistoryRepository, clock=None):
        self.repository = repository
        self.clock = clock or (lambda: datetime.now(UTC).date())

    def calculate(self, area, start=None, end=None):
        snapshot = self.repository.load(area)
        last = Month.parse(snapshot.meta['last_month'])
        first = Month.parse(start) if start is not None else Month(2003, 1)
        final = Month.parse(end) if end is not None else last
        if not Month(2003, 1) <= first <= final <= last:
            raise CalendarError('invalid_period', 'Period is outside the available calendar.')
        result = {'meta': dict(snapshot.meta), 'area': dict(snapshot.area), 'coverage': dict(snapshot.coverage)}
        if snapshot.coverage['status'] == 'none':
            return result
        today = self.clock()
        selected = list(months_between(first, final))
        rows = defaultdict(list)
        for row in snapshot.counts:
            rows[Month(row['year'], row['month'])].append(row)
        factors = factor_index(snapshot.factors)
        regions = {biome['region_id'] for biome in snapshot.area['biomes']}
        periods = {(row['region_id'], row['satellite']): row for row in snapshot.periods}
        vectors, raw_counts = {}, {}
        # Read the full baseline independently of the user's display filter.
        for month in months_between(Month(2003, 1), last):
            covered = all((region, month.satellite) in periods and
                          periods[(region, month.satellite)]['start'] < month.next().start and
                          periods[(region, month.satellite)]['end'] >= month.start for region in regions)
            if not covered:
                continue
            vectors[month], raw_counts[month] = month_scenarios(month, rows[month], factors)
        if any(month not in vectors for month in selected):
            raise CalendarError('invalid_data', 'The requested period has missing temporal coverage.')
        full_years = [year for year in range(2003, min(today.year, last.year + 1))
                      if all(Month(year, month) in vectors for month in range(1, 13))]
        missing = defaultdict(int)
        for day, satellite in snapshot.missing:
            month = Month(day.year, day.month)
            if satellite == month.satellite:
                missing[month] += 1
        months = []
        for month in selected:
            current = month == Month(today.year, today.month)
            references = [vectors[Month(year, month.month)] for year in full_years if year != month.year]
            absolute, relative = (None, None) if current else anomaly(vectors[month], references)
            row = summarize(vectors[month], month.source == 'estimated_modis')
            row.update(month=str(month), source=month.source, raw_count=raw_counts[month],
                       missing_days=missing[month], incomplete=missing[month] >= 3 or current,
                       provisional=(month.year, month.month, month.satellite) in snapshot.provisional,
                       anomaly=absolute, anomaly_pct=relative)
            months.append(row)
        years = annual_results(selected, vectors, today)
        complete_selected = sorted(row['year'] for row in years if row['complete'])
        seasonality = seasonality_results(complete_selected, vectors)
        latest = None
        if complete_selected:
            year = max(complete_selected)
            own = total([vectors[Month(year, m)] for m in range(1, 13)])
            references = [total([vectors[Month(y, m)] for m in range(1, 13)]) for y in full_years if y != year]
            reference_mean = percentage = None
            if references:
                aligned_values = list(aligned([own, *references]).values())
                means = [fsum(values[1:]) / len(values[1:]) for values in aligned_values]
                reference_mean = percentile(means, 50)
                if all(means):
                    percentage = percentile([values[0] / mean - 1 for values, mean in zip(aligned_values, means)], 50)
            latest = {'year': year, 'detections': percentile(list(own.values()), 50),
                      'reference_mean': reference_mean, 'anomaly_pct': percentage}
        result.update(months=months, years=years, seasonality=seasonality,
                      indicators={'total_detections': fsum(row['detections'] for row in months),
                                  'latest_complete_year': latest})
        return result

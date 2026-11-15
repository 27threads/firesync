"""Observed VIIRS windows; absent covered rows are zero, unavailable days are not."""
from datetime import timedelta

from backend.domain.calculations.statistics import percentile
from backend.domain.windows import reference_windows


def days_between(start, end):
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def recent_result(data_through, daily, high, coverage, missing):
    def window(length):
        start = data_through - timedelta(days=length - 1)
        current_days = days_between(start, data_through)
        count = sum(daily.get(day, 0) for day in current_days)
        n_high = sum(high.get(day, 0) for day in current_days)
        samples, years = [], set()
        for year in range(2012, data_through.year):
            for first, last in reference_windows(data_through, length, 15, [year]):
                days = days_between(first, last)
                if any(day in missing or not any(a <= day <= b for a, b in coverage) for day in days):
                    continue
                years.add(year)
                samples.append(sum(daily.get(day, 0) for day in days))
        median = percentile(samples, 50) if samples else None
        return {'start': start.isoformat(), 'end': data_through.isoformat(), 'detections': count,
                'typical_median': median, 'typical_p25': percentile(samples, 25) if samples else None,
                'typical_p75': percentile(samples, 75) if samples else None,
                'difference': count - median if median is not None else None,
                'difference_pct': count / median - 1 if median else None,
                'n_years': len(years), 'n_windows': len(samples), 'n_high': n_high,
                'high_share': n_high / count if count else None}
    return {'data_through': data_through.isoformat(), 'last_7_days': window(7),
            'month_to_date': window(data_through.day)}

from math import isfinite

from backend.domain.models.error import CalendarError


def percentile(values, percent):
    """Linear interpolation, equivalent to numpy.percentile(method='linear')."""
    ordered = sorted(values)
    if not ordered or not 0 <= percent <= 100 or not all(isfinite(x) for x in ordered):
        raise CalendarError("invalid_data", "Cannot calculate a percentile from these values.")
    position = (len(ordered) - 1) * percent / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize(scenarios, estimated):
    values = list(scenarios.values())
    return {"detections": percentile(values, 50),
            "band_low": percentile(values, 5) if estimated else None,
            "band_high": percentile(values, 95) if estimated else None}


def difference(value, baseline):
    return value - baseline, value / baseline - 1 if baseline else None

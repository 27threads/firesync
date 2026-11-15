from calendar import monthrange
from datetime import date, timedelta


def reference_windows(end, window_days, neighbor_days, years):
    """Shift same-length windows around the calendar date, clamping leap day."""
    windows = []
    for year in years:
        anchor = date(year, end.month, min(end.day, monthrange(year, end.month)[1]))
        for offset in range(-neighbor_days, neighbor_days + 1):
            final = anchor + timedelta(days=offset)
            windows.append((final - timedelta(days=window_days - 1), final))
    return windows

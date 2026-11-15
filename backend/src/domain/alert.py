"""Versioned alert decision shared by recent monitoring and domain tests."""


def alert_level(count, median, attention_threshold, last, previous, rules):
    if median is None or attention_threshold is None:
        return None
    critical = rules['levels']['critical']
    threshold = max(critical['min_ratio_to_median'] * median, critical['min_detections'])
    rising = sum(last) > sum(previous)
    if count >= threshold and (not critical['requires_rising_trend'] or rising):
        return 'critical'
    return 'attention' if count > attention_threshold else 'normal'

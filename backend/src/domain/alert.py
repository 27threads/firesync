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


def historical_outcome(level, rules):
    """How often this level was followed by unusually high detections (backtest of rule v1, RFC 0003)."""
    history = rules.get('historical_outcome')
    if level is None or not history:
        return None
    return {'share_followed_by_high': history['share_followed_by_high'][level],
            'overall_share': history['overall_share'], 'horizon_days': history['horizon_days']}

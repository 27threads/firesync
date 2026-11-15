def intensity_class(frp, sensor, confidence, rules):
    saturation = rules['saturated_is_high']
    if (saturation['enabled'] and sensor in saturation['sensors']
            and confidence in ('high', 'alta')):
        return 'high'
    if frp >= rules['high_min_mw']:
        return 'high'
    return 'medium' if frp >= rules['medium_min_mw'] else 'low'

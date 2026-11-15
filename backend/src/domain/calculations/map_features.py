from collections import defaultdict

import h3

from backend.domain.calculations.cell_alerts import cell_alerts

ALERT_RESOLUTION = 4  # rule v1 was backtested on H3 resolution 4 cells (RFC 0003)
PRIORITY_ORDER = {'critical': 0, 'attention': 1}


def alerts_block(rows, rules):
    """Level of each resolution 4 cell with recent fire, and the cells to look at first (Critical, then Attention)."""
    if rules is None:
        return None, {}
    levels = rows.get('cell_levels')      # already computed (and cached per data version) by the repository
    if levels is None and rows.get('cell_daily') is not None:
        levels = cell_alerts(rows['data_through'], rows['cell_daily'], rules, rows['coverage_start'])
    if levels is None:
        return None, {}
    priority = []
    for cell, info in levels.items():
        if info['alert_level'] in PRIORITY_ORDER:
            lat, lon = h3.cell_to_latlng(cell)
            priority.append({'h3': cell, 'alert_level': info['alert_level'], 'detections_7d': info['detections_7d'],
                             'typical_median': info['typical_median'],
                             'share_followed_by_high': info['share_followed_by_high'], 'center': [lon, lat]})
    priority.sort(key=lambda p: (PRIORITY_ORDER[p['alert_level']],
                                 -p['detections_7d'] / max(p['typical_median'] or 0, 1), p['h3']))
    history = rules.get('historical_outcome') or {}
    block = {'data_through': rows['data_through'].isoformat(), 'alert_rules_version': rules['version'],
             'unit': history.get('unit'), 'horizon_days': history.get('horizon_days'),
             'overall_share': history.get('overall_share'), 'priority': priority}
    return block, levels


def map_result(query, rows, updated_at, rules=None):
    result = {'type': 'FeatureCollection', 'hours': query.hours,
              'updated_at': updated_at, 'total_detections': rows['total']}
    alerts, levels = alerts_block(rows, rules)
    if alerts is not None:
        result['alerts'] = alerts
    if query.points and rows['points'] is not None:
        result.update(mode='points', features=[{
            'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [row['longitude'], row['latitude']]},
            'properties': {key: row[key] for key in ('satellite', 'acquired_utc', 'confidence', 'intensity', 'daynight')}
        } for row in rows['points']])
        return result
    resolution = 6 if query.points else query.resolution
    grouped = defaultdict(lambda: dict.fromkeys(('detections', 'n_low', 'n_medium', 'n_high'), 0))
    for row in rows['hexagons']:
        cell = h3.cell_to_parent(h3.int_to_str(row['h3']), resolution)
        for field in grouped[cell]:
            grouped[cell][field] += row[field]
    features = []
    for cell, counts in sorted(grouped.items()):
        ring = [[lon, lat] for lat, lon in h3.cell_to_boundary(cell)]
        ring.append(ring[0])
        properties = {'h3': cell, **counts}
        if alerts is not None:
            parent = h3.cell_to_parent(cell, ALERT_RESOLUTION)
            properties.update(alert_cell=parent, alert_level=levels.get(parent, {}).get('alert_level'))
        features.append({'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [ring]},
                         'properties': properties})
    result.update(mode='hexagons', h3_resolution=resolution, features=features)
    return result

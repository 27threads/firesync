from collections import defaultdict

import h3


def map_result(query, rows, updated_at):
    result = {'type': 'FeatureCollection', 'hours': query.hours,
              'updated_at': updated_at, 'total_detections': rows['total']}
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
        features.append({'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [ring]},
                         'properties': {'h3': cell, **counts}})
    result.update(mode='hexagons', h3_resolution=resolution, features=features)
    return result

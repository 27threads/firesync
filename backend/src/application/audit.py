"""Build an English audit document; ZIP/CSV serialization belongs to the adapter."""
from backend.domain.models.month import Month

DETECTION_LIMIT = 500_000
RESULT_FIELDS = ('month', 'detections', 'band_low', 'band_high', 'source', 'raw_count',
                 'missing_days', 'incomplete', 'provisional', 'anomaly', 'anomaly_pct')
COUNT_FIELDS = ('region_id', 'biome', 'year', 'month', 'satellite', 'daynight', 'raw_count', 'frp_sum')
FACTOR_FIELDS = ('region_id', 'source_satellite', 'target_satellite', 'month', 'daynight', 'calibration_year', 'factor')
DETECTION_FIELDS = ('satellite', 'latitude', 'longitude', 'acquired_utc', 'confidence', 'frp', 'daynight', 'quality', 'source_file')


def audit_document(reader, snapshot, result, request, now, rules):
    first = Month.parse(request.get('start', '2003-01'))
    final = Month.parse(request.get('end', snapshot.meta['last_month']))
    biomes = {b['region_id']: b['name'] for b in snapshot.area['biomes']}
    counts = [dict(row, biome=biomes[row['region_id']]) for row in snapshot.counts
              if first <= Month(row['year'], row['month']) <= final
              and row['satellite'] == Month(row['year'], row['month']).satellite]
    conditions = {(r['region_id'], r['month'], r['daynight']) for r in counts
                  if r['satellite'] == 'Aqua' and r['raw_count'] > 0}
    factors = [dict(row, source_satellite='Aqua', target_satellite='SNPP') for row in snapshot.factors
               if (row['region_id'], row['month'], row['daynight']) in conditions]
    count, detections = reader.detections(snapshot, first.start, final.next().start)
    omitted = count > DETECTION_LIMIT
    metadata = {'request': request, 'meta': dict(snapshot.meta), 'area': dict(snapshot.area),
                'coverage': dict(snapshot.coverage), 'exported_at': now.isoformat().replace('+00:00', 'Z'),
                'formula': 'For each calibration year k: E_k = sum(raw_count[biome,daynight] * factor[biome,month,daynight,k]). Use the median and P5-P95 of E_k. Observed VIIRS uses raw_count without a factor. Combine only common calibration years; zero counts do not require factors.',
                'band_percentiles': [5, 95], 'percentile_method': 'linear',
                'calibration_years': sorted({f['calibration_year'] for f in factors}),
                'filters': {'type': '0 (NRT may omit type)', 'confidence': ['nominal', 'high'],
                            'duplicates': ['satellite', 'latitude', 'longitude', 'acquired_utc'],
                            'satellite': 'Aqua before 2012-02; SNPP through 2026-10; N20 from 2026-11',
                            'frp': 'positive'},
                'sources': ['NASA FIRMS MODIS C6.1', 'NASA FIRMS VIIRS C2', 'https://firms.modaps.eosdis.nasa.gov/'],
                'alert_rules_version': rules['version'], 'intensity': rules['intensity'],
                'detections_count': count, 'detections_omitted': omitted,
                'message': 'Select a smaller area or period to include detections.csv.' if omitted else None}
    files = {'result.csv': (RESULT_FIELDS, result.get('months', [])),
             'counts.csv': (COUNT_FIELDS, counts), 'factors.csv': (FACTOR_FIELDS, factors)}
    if not omitted:
        files['detections.csv'] = (DETECTION_FIELDS, detections)
    return files, metadata

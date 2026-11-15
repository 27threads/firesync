"""HTTP contract runs in-process by default; API_URL enables the same public checks on a live API."""
import csv
import io
import json
import os
import zipfile

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.fakes.api import CELL, NOW, FakeApiRepository

REQUEST = {'area': {'type': 'region', 'region_id': 1}, 'start': '2003-01', 'end': '2026-11'}


@pytest.fixture
def repository():
    return FakeApiRepository()


@pytest.fixture
def client(repository):
    from backend.adapters.inbound.http.app import create_app
    with TestClient(create_app(repository=repository, clock=lambda: NOW,
                               limits={'general': 1000, 'calendar': 1000, 'export': 1000})) as client:
        yield client


def test_five_endpoints_and_full_calendar_contract(client, api_example):
    health = client.get('/api/v1/health')
    assert health.status_code == 200
    assert set(health.json()) == {'status', 'data_version', 'last_month', 'updated_at', 'h3_resolution'}
    assert health.json()['status'] == 'ok'
    assert client.get('/api/v1/regions').json()[0]['bbox'] == [-61, -4, -59, -2]
    response = client.post('/api/v1/calendar', json=REQUEST)
    assert response.status_code == 200
    data = response.json()
    assert set(data) == set(api_example) - {'_example'}
    for field in ['meta', 'area', 'coverage', 'indicators', 'recent']:
        assert set(data[field]) == set(api_example[field])
    for field in ['months', 'years', 'seasonality']:
        assert set(data[field][0]) == set(api_example[field][0])
    for field in ['last_7_days', 'month_to_date']:
        assert set(data['recent'][field]) == set(api_example['recent'][field])
    assert data['months'][0]['detections'] == 15
    assert data['recent']['last_7_days']['detections'] == 7
    assert data['indicators']['last_7_days_vs_typical_pct'] == data['recent']['last_7_days']['difference_pct']
    assert 'frp' not in response.text
    assert response.headers['etag']
    assert client.post('/api/v1/calendar', json={'area': REQUEST['area']}).json() == data
    small = client.post('/api/v1/calendar', json={**REQUEST, 'end': '2003-01'}).json()
    assert small['recent'] == data['recent']
    assert client.get('/api/v1/detections/recent?bbox=-61,-4,-59,-2&zoom=7').status_code == 200
    assert client.post('/api/v1/export', json=REQUEST).status_code == 200


@pytest.mark.parametrize('payload,code,status', [
    ({}, 'invalid_geometry', 400),
    ({'area': {'type': 'point', 'lat': 0, 'lon': 0, 'radius_km': 201}}, 'invalid_geometry', 400),
    ({'area': {'type': 'region', 'region_id': 999}}, 'region_not_found', 404),
    ({'area': {'type': 'geojson', 'geometry': {'type': 'Point', 'coordinates': [0, 0]}}}, 'invalid_geometry', 400),
    ({'area': {'type': 'geojson', 'geometry': {'type': 'Polygon', 'coordinates': [[[-100,-50],[100,-50],[100,50],[-100,50],[-100,-50]]]}}}, 'area_too_large', 413),
    ({**REQUEST, 'start': '2002-12'}, 'invalid_period', 400),
    ({**REQUEST, 'end': '2027-01'}, 'invalid_period', 400),
    ({**REQUEST, 'start': '2026-11', 'end': '2020-01'}, 'invalid_period', 400),
    ({**REQUEST, 'start': 'bad'}, 'invalid_period', 400),
    ({**REQUEST, 'start': 202001}, 'invalid_period', 400),
])
@pytest.mark.parametrize('endpoint', ['calendar', 'export'])
def test_request_errors(client, payload, code, status, endpoint):
    response = client.post('/api/v1/' + endpoint, json=payload)
    assert response.status_code == status
    assert response.json()['error']['code'] == code
    assert response.json()['error']['message']


@pytest.mark.parametrize('params,code', [('bbox=bad', 'invalid_bbox'),
    ('bbox=0,0,0,10', 'invalid_bbox'), ('bbox=nan,0,10,10', 'invalid_bbox'),
    ('bbox=-181,0,10,10', 'invalid_bbox'), ('bbox=0,0,10,91', 'invalid_bbox'),
    ('bbox=0,0,10,10&hours=48', 'invalid_hours'), ('bbox=0,0,10,10&hours=x', 'invalid_hours'),
    ('bbox=0,0,10,10&mode=bad', 'invalid_mode'), ('bbox=0,0,10,10&zoom=x', 'invalid_mode')])
def test_map_errors(client, params, code):
    response = client.get('/api/v1/detections/recent?' + params)
    assert response.status_code == 400
    assert response.json()['error']['code'] == code


def test_outside_coverage_and_internal_errors(client, repository):
    payload = {'area': {'type': 'point', 'lat': 50, 'lon': 20, 'radius_km': 1}}
    response = client.post('/api/v1/calendar', json=payload)
    assert response.status_code == 200
    assert set(response.json()) == {'meta', 'area', 'coverage'}
    assert response.json()['coverage']['status'] == 'none'
    repository.failure = RuntimeError('secret database password')
    response = client.get('/api/v1/health')
    assert response.status_code == 500
    assert response.json()['error']['code'] == 'internal_error'
    assert 'secret' not in response.text


@pytest.mark.parametrize('zoom,mode,resolution', [(4, 'hexagons', 4), (5, 'hexagons', 5),
    (6, 'hexagons', 5), (7, 'hexagons', 6), (8, 'points', None)])
def test_map_mode_and_h3_roundtrip(client, zoom, mode, resolution):
    response = client.get(f'/api/v1/detections/recent?bbox=-61,-4,-59,-2&zoom={zoom}&hours=168')
    assert response.status_code == 200
    body = response.json()
    assert body['mode'] == mode
    assert body['total_detections'] == 1
    feature = body['features'][0]
    assert 'frp' not in response.text
    if resolution:
        assert body['h3_resolution'] == resolution
        properties = feature['properties']
        assert isinstance(properties['h3'], str)
        assert properties['n_low'] + properties['n_medium'] + properties['n_high'] == properties['detections']
        assert feature['geometry']['coordinates'][0][0] == feature['geometry']['coordinates'][0][-1]
        if resolution == 6:
            assert properties['h3'] == CELL
    else:
        assert feature['properties']['intensity'] == 'high'
        assert 'h3_resolution' not in body


def test_points_over_limit_become_hexagons_without_truncation(client, repository):
    repository.map_count = 50_001
    data = client.get('/api/v1/detections/recent?bbox=-61,-4,-59,-2&zoom=9&mode=points').json()
    assert data['mode'] == 'hexagons'
    assert data['h3_resolution'] == 6
    assert sum(f['properties']['detections'] for f in data['features']) == 50_001


def test_zip_reconstructs_result_and_contains_english_audit_rows(client):
    response = client.post('/api/v1/export', json=REQUEST)
    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/zip'
    assert 'firesync-2026-11-14.zip' in response.headers['content-disposition']
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {'result.csv', 'counts.csv', 'factors.csv', 'metadata.json', 'detections.csv'}
        def rows(name):
            return list(csv.DictReader(io.StringIO(archive.read(name).decode('utf-8-sig'))))
        result, counts, factors = rows('result.csv'), rows('counts.csv'), rows('factors.csv')
        assert float(result[0]['detections']) == sum(float(f['factor']) * int(counts[0]['raw_count']) for f in factors) / 2
        assert 'biome' in counts[0] and 'frp_sum' in counts[0]
        assert factors[0]['source_satellite'] == 'Aqua'
        assert rows('detections.csv')[0]['confidence'] == 'high'
        metadata = json.loads(archive.read('metadata.json'))
        assert metadata['request'] == REQUEST
        assert metadata['band_percentiles'] == [5, 95]
        assert metadata['percentile_method'] == 'linear'
        assert metadata['calibration_years'] == [2013, 2014]
        assert metadata['detections_omitted'] is False
        assert metadata['alert_rules_version'] == '0.2'


def test_zip_omits_raw_rows_above_limit(client, repository):
    repository.detection_count = 500_001
    with zipfile.ZipFile(io.BytesIO(client.post('/api/v1/export', json=REQUEST).content)) as archive:
        assert 'detections.csv' not in archive.namelist()
        metadata = json.loads(archive.read('metadata.json'))
        assert metadata['detections_omitted'] is True
        assert metadata['detections_count'] == 500_001
        assert 'smaller' in metadata['message']


def test_zip_includes_raw_rows_at_exact_limit(client, repository):
    repository.detection_count = 500_000
    with zipfile.ZipFile(io.BytesIO(client.post('/api/v1/export', json=REQUEST).content)) as archive:
        assert 'detections.csv' in archive.namelist()
        assert json.loads(archive.read('metadata.json'))['detections_omitted'] is False


def test_rate_limit_retry_and_ip_isolation(repository):
    from backend.adapters.inbound.http.app import create_app
    tick = [0.0]
    app = create_app(repository=repository, clock=lambda: NOW, monotonic=lambda: tick[0],
                     limits={'general': 3, 'calendar': 1, 'export': 1}, rate_window=60)
    with TestClient(app) as client:
        assert client.post('/api/v1/calendar', json=REQUEST).status_code == 200
        response = client.post('/api/v1/calendar', json=REQUEST, headers={'X-Forwarded-For': 'spoof'})
        assert response.status_code == 429
        assert response.json()['error']['code'] == 'rate_limited'
        assert response.headers['retry-after'] == '60'
        tick[0] = 60
        assert client.post('/api/v1/calendar', json=REQUEST).status_code == 200
        assert client.post('/api/v1/export', json=REQUEST).status_code == 200
        assert client.post('/api/v1/export', json=REQUEST).status_code == 429
        assert client.get('/api/v1/health').status_code == 200
        assert client.get('/api/v1/health').status_code == 429
    with TestClient(app, client=('another-client', 123)) as other:
        assert other.get('/api/v1/health').status_code == 200


def test_cache_refresh_etag_and_cors(client, repository):
    first = client.post('/api/v1/calendar', json=REQUEST)
    cached = client.post('/api/v1/calendar', json=REQUEST)
    assert first.json() == cached.json()
    repository.snapshot.meta['updated_at'] = '2026-11-14T18:00:00Z'
    refreshed = client.post('/api/v1/calendar', json=REQUEST)
    assert refreshed.headers['etag'] != first.headers['etag']
    allowed = client.get('/api/v1/health', headers={'Origin': 'http://localhost:5173'})
    assert allowed.headers['access-control-allow-origin'] == 'http://localhost:5173'
    denied = client.get('/api/v1/health', headers={'Origin': 'https://untrusted.example'})
    assert 'access-control-allow-origin' not in denied.headers


@pytest.mark.skipif(not os.environ.get('API_URL'), reason='Set API_URL for the live API smoke test.')
def test_live_api_smoke():
    with httpx.Client(base_url=os.environ['API_URL'].rstrip('/'), timeout=120) as client:
        health = client.get('/api/v1/health')
        assert health.status_code == 200
        regions = client.get('/api/v1/regions').json()
        assert regions
        payload = {'area': {'type': 'region', 'region_id': regions[0]['region_id']},
                   'start': '2024-01', 'end': '2024-12'}
        response = client.post('/api/v1/calendar', json=payload)
        assert response.status_code == 200, response.text
        assert len(response.json()['months']) == 12
        bbox = ','.join(map(str, regions[0]['bbox']))
        assert client.get('/api/v1/detections/recent', params={'bbox': bbox, 'zoom': 4}).status_code == 200
        exported = client.post('/api/v1/export', json=payload)
        assert exported.status_code == 200
        assert zipfile.is_zipfile(io.BytesIO(exported.content))

from dataclasses import replace
import json

import pytest
from fastapi.testclient import TestClient

from backend.adapters.inbound.http.app import create_app
from backend.adapters.inbound.http.cache import ResponseCache
from backend.adapters.inbound.http.limits import RateLimiter
from tests.fakes.api import NOW, FakeApiRepository


@pytest.mark.parametrize('body', ['{', 'null', '[]', '{"area":{"type":"region","region_id":1,"extra":1}}',
    '{"area":{"type":"point","lat":NaN,"lon":0,"radius_km":1}}',
    '{"area":{"type":"geojson","geometry":{"type":"Polygon","coordinates":[[[NaN,0],[1,0],[1,1],[NaN,0]]]}}}'])
def test_malformed_json_and_nonfinite_geometry_are_contract_errors(body):
    with TestClient(create_app(repository=FakeApiRepository(), clock=lambda: NOW)) as client:
        response = client.post('/api/v1/calendar', content=body, headers={'Content-Type': 'application/json'})
        assert response.status_code == 400
        assert response.json()['error']['code'] == 'invalid_geometry'


def test_unavailable_dataset_is_generic_500_and_cors_preflight():
    repo = FakeApiRepository()
    repo.snapshot = replace(repo.snapshot, periods=())
    with TestClient(create_app(repository=repo, clock=lambda: NOW)) as client:
        response = client.post('/api/v1/calendar', json={'area': {'type': 'region', 'region_id': 1}})
        assert response.status_code == 500
        assert response.json()['error']['code'] == 'internal_error'
        preflight = client.options('/api/v1/calendar', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST'})
        assert preflight.status_code == 200
        assert preflight.headers['access-control-allow-origin'] == 'http://localhost:5173'


def test_get_conditional_requests_map_cache_and_forced_modes():
    with TestClient(create_app(repository=FakeApiRepository(), clock=lambda: NOW)) as client:
        url = '/api/v1/detections/recent?bbox=-61,-4,-59,-2&zoom=4&mode=points'
        first = client.get(url)
        assert first.json()['mode'] == 'points'
        second = client.get(url, headers={'If-None-Match': first.headers['etag']})
        assert second.status_code == 304 and second.content == b''
        assert client.get('/api/v1/detections/recent?bbox=-61,-4,-59,-2&zoom=9&mode=hexagons').json()['mode'] == 'hexagons'


def test_lru_eviction_keeps_recently_used_response():
    cache = ResponseCache(2)
    cache.put('a', 1)
    cache.put('b', 2)
    assert cache.get('a') == 1
    cache.put('c', 3)
    assert cache.get('b') is None
    assert cache.get('a') == 1


def test_limiter_rolls_individual_windows_while_other_routes_remain_active():
    tick = [0]
    limits = {'general': 3, 'calendar': 1, 'export': 1}
    with pytest.raises(ValueError):
        RateLimiter(limits, 0, lambda: 0)
    limiter = RateLimiter(limits, 60, lambda: tick[0])
    assert limiter.retry_after('ip', 'calendar') == 0
    tick[0] = 30
    assert limiter.retry_after('ip', 'health') == 0
    assert limiter.retry_after('ip', 'calendar') == 30
    tick[0] = 60
    assert limiter.retry_after('ip', 'calendar') == 0


def test_intensity_configuration_is_loaded_from_environment(tmp_path, monkeypatch, alert_rules):
    path = tmp_path / 'rules.json'
    path.write_text(json.dumps(alert_rules), encoding='utf-8')
    monkeypatch.setenv('ALERT_RULES_PATH', str(path))
    monkeypatch.setenv('RATE_LIMIT_GENERAL', '1')
    with TestClient(create_app(repository=FakeApiRepository())) as client:
        assert client.get('/api/v1/health').status_code == 200
        assert client.get('/api/v1/health').status_code == 429


def test_request_metrics_use_uvicorn_logging(caplog):
    caplog.set_level('INFO', logger='uvicorn.error.firesync')
    with TestClient(create_app(repository=FakeApiRepository(), clock=lambda: NOW)) as client:
        client.post('/api/v1/calendar', json={'area': {'type': 'region', 'region_id': 1}})
    assert 'endpoint=/api/v1/calendar status=200 duration_ms=' in caplog.text
    assert 'n_cells=1' in caplog.text

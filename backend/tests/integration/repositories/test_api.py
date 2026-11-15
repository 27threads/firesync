from datetime import date
import io
import json
from zipfile import ZipFile

import h3
import pytest
from fastapi.testclient import TestClient

from tests.integration.repositories.test_history import database  # noqa: F401 - shared isolated PostGIS fixture
from tests.fakes.api import NOW


@pytest.fixture
def api_database(database):  # noqa: F811 - pytest injects the imported fixture
    pool, region, cell = database
    with pool.connection() as conn:
        conn.execute("INSERT INTO cobertura(regiao_id,satelite,data_inicio,data_fim) VALUES (%s,'Aqua','2003-01-01','2012-01-31')", (region,))
        conn.execute("INSERT INTO agregados VALUES (%s,2003,1,%s,'Aqua','D',5,10)", (cell, region))
        conn.execute("INSERT INTO fatores_harmonizacao(regiao_id,satelite_origem,satelite_destino,mes,periodo,ano_calibracao,fator) VALUES (%s,'Aqua','SNPP',1,'D',2013,2),(%s,'Aqua','SNPP',1,'D',2014,4)", (region, region))
        conn.execute("INSERT INTO agregados_diarios VALUES (%s,'2026-11-14',%s,'N20','D',3),(%s,'2025-11-14',%s,'SNPP','D',2)", (cell, region, cell, region))
        for index, (satellite, confidence, frp, kind, quality) in enumerate([
            ('N20', 'nominal', 4, 0, 'NRT'), ('N20', 'nominal', 5, None, 'NRT'),
            ('N20', 'alta', 3, None, 'NRT'), ('N21', 'alta', 1, None, 'NRT'),
            ('SNPP', 'alta', 1, None, 'NRT'), ('N20', 'baixa', 1, None, 'NRT'),
            ('N20', 'nominal', 1, 2, 'NRT'), ('N20', 'nominal', 0, 0, 'NRT'),
            ('N20', 'nominal', 25, 0, 'SP'),
        ]):
            conn.execute("""INSERT INTO focos(sensor,satelite,lat,lon,datahora_utc,confianca,frp,periodo,tipo,qualidade,arquivo_origem,h3)
                VALUES ('VIIRS',%s,-3,%s,'2026-11-14T12:00Z',%s,%s,'D',%s,%s,'fixture.csv',%s)""",
                         (satellite, -60 + index * .00001, confidence, frp, kind, quality, cell))
    return pool, region, cell


@pytest.fixture
def api(api_database):
    from backend.adapters.outbound.postgres.api import PostgresApiRepository
    from backend.adapters.outbound.config_file.rules import load_rules
    from backend.adapters.inbound.http.app import create_app
    pool, region, cell = api_database
    repository = PostgresApiRepository(pool, load_rules())
    with TestClient(create_app(repository=repository, clock=lambda: NOW,
                               limits={'general': 1000, 'calendar': 1000, 'export': 1000})) as client:
        yield client, repository, region, cell


def test_postgres_all_routes_and_filtered_map(api):
    client, repository, region, cell = api
    assert client.get('/api/v1/health').json()['status'] == 'ok'
    assert client.get('/api/v1/regions').json() == [{'region_id': region, 'name': 'Test', 'source': 'test', 'bbox': [-61, -4, -59, -2]}]
    payload = {'area': {'type': 'region', 'region_id': region}, 'start': '2003-01', 'end': '2003-01'}
    result = client.post('/api/v1/calendar', json=payload)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body['months'][0]['detections'] == 15
    assert body['recent']['data_through'] == '2026-11-14'
    assert body['recent']['last_7_days']['detections'] == 3
    # High includes SP as well as NRT, just as daily totals do.
    assert body['recent']['last_7_days']['n_high'] == 2
    map_body = client.get('/api/v1/detections/recent?bbox=-61,-4,-59,-2&zoom=7&hours=24').json()
    assert map_body['total_detections'] == 3
    parent = h3.cell_to_parent(h3.int_to_str(cell), 4)
    # A semana de 2026 (3) passa do P75 do normal (0) mas não chega ao piso de 10: Atenção (RFC 0003).
    assert map_body['features'][0]['properties'] == {'h3': h3.int_to_str(cell), 'detections': 3, 'n_low': 1, 'n_medium': 1,
                                                     'n_high': 1, 'alert_cell': parent, 'alert_level': 'attention'}
    assert map_body['alerts']['data_through'] == '2026-11-14'
    assert [(p['h3'], p['alert_level'], p['detections_7d']) for p in map_body['alerts']['priority']] == [(parent, 'attention', 3)]
    points = client.get('/api/v1/detections/recent?bbox=-61,-4,-59,-2&zoom=9').json()
    assert {f['properties']['intensity'] for f in points['features']} == {'low', 'medium', 'high'}
    assert all(f['properties']['satellite'] == 'N20' for f in points['features'])
    payload.update(start='2026-11', end='2026-11')
    archive = ZipFile(io.BytesIO(client.post('/api/v1/export', json=payload).content))
    metadata = json.loads(archive.read('metadata.json'))
    assert metadata['detections_count'] == 4
    assert 'alta' not in archive.read('detections.csv').decode('utf-8-sig')
    with repository.read() as reader:
        assert reader.meta()['h3_resolution'] == 6


def test_no_coverage_export_has_only_headers(api):
    client, _, _, _ = api
    response = client.post('/api/v1/export', json={'area': {'type': 'point', 'lat': 50, 'lon': 20, 'radius_km': 1}})
    assert response.status_code == 200, response.text
    archive = ZipFile(io.BytesIO(response.content))
    assert json.loads(archive.read('metadata.json'))['coverage']['status'] == 'none'
    assert len(archive.read('result.csv').decode('utf-8-sig').splitlines()) == 1


def test_recent_covers_zero_days_and_excludes_missing_windows(api, api_database):
    from backend.domain.models.area import Area
    _, repo, region, _ = api
    pool, _, _ = api_database
    with pool.connection() as conn:
        conn.execute("INSERT INTO dias_sem_dados VALUES ('2025-11-14','SNPP')")
    with repo.read() as reader:
        recent = reader.recent(reader.history(Area('region', region_id=region)))
    assert recent['data_through'] == date(2026, 11, 14)
    assert date(2025, 11, 14) in recent['missing']
    assert recent['coverage'] == [(date(2012, 2, 1), date(2026, 11, 14))]


def test_api_snapshot_survives_pipeline_commit(api, api_database):
    from backend.domain.models.area import Area
    _, repo, region, _ = api
    pool, _, _ = api_database
    with repo.read() as reader:
        before = reader.meta()
        with pool.connection() as conn:
            conn.execute("UPDATE agregados SET focos_brutos=9 WHERE ano=2003")
            conn.execute("UPDATE config SET valor='2026-11-14T20:00:00Z' WHERE chave='atualizado_em'")
        snapshot = reader.history(Area('region', region_id=region))
        assert next(r['raw_count'] for r in snapshot.counts if r['year'] == 2003) == 5
        assert snapshot.meta['updated_at'] == before['updated_at']


def test_factor_cache_reloads_on_intraday_version(api, api_database):
    client, _, region, _ = api
    pool, _, _ = api_database
    payload = {'area': {'type': 'region', 'region_id': region}, 'start': '2003-01', 'end': '2003-01'}
    assert client.post('/api/v1/calendar', json=payload).json()['months'][0]['detections'] == 15
    with pool.connection() as conn:
        conn.execute('UPDATE fatores_harmonizacao SET fator=10')
        conn.execute("UPDATE config SET valor='2026-11-14T21:00:00Z' WHERE chave IN ('data_version','atualizado_em')")
    assert client.post('/api/v1/calendar', json=payload).json()['months'][0]['detections'] == 50


def test_startup_rejects_wrong_h3_resolution(api_database):
    from backend.adapters.outbound.postgres.api import PostgresApiRepository
    from backend.adapters.outbound.config_file.rules import load_rules
    from backend.adapters.inbound.http.app import create_app
    from backend.domain.models.error import CalendarError
    pool, _, _ = api_database
    with pool.connection() as conn:
        conn.execute("UPDATE config SET valor='5' WHERE chave='h3_resolucao'")
    with pytest.raises(CalendarError):
        with TestClient(create_app(repository=PostgresApiRepository(pool, load_rules()))):
            pass


def test_large_queries_aggregate_points_and_omit_export_without_truncating(api, api_database):
    client, _, region, cell = api
    pool, _, _ = api_database
    with pool.connection() as conn:
        conn.execute("""INSERT INTO focos(sensor,satelite,lat,lon,datahora_utc,confianca,frp,periodo,tipo,qualidade,arquivo_origem,h3)
            SELECT 'VIIRS','N20',-3,-60,'2026-11-14T13:00Z'::timestamptz+i*interval '1 microsecond',
            'nominal',2,'D',NULL,'NRT','large-fixture.csv',%s FROM generate_series(1,499997) AS i""", (cell,))
    response = client.get('/api/v1/detections/recent?bbox=-61,-4,-59,-2&zoom=9&mode=points')
    assert response.status_code == 200
    result = response.json()
    assert result['mode'] == 'hexagons' and result['h3_resolution'] == 6
    assert result['total_detections'] == 500_000  # Three pre-existing NRT detections.
    assert sum(f['properties']['detections'] for f in result['features']) == 500_000
    response = client.post('/api/v1/export', json={'area': {'type': 'region', 'region_id': region},
                                                 'start': '2026-11', 'end': '2026-11'})
    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        assert 'detections.csv' not in archive.namelist()
        metadata = json.loads(archive.read('metadata.json'))
        assert metadata['detections_count'] == 500_001  # SP also belongs in the export.
        assert metadata['detections_omitted'] is True


def test_custom_intensity_thresholds_agree_for_points_and_hexagons(api_database, alert_rules):
    from copy import deepcopy
    from backend.adapters.outbound.postgres.api import PostgresApiRepository
    from backend.domain.models.map_query import MapQuery
    pool, _, _ = api_database
    rules = deepcopy(alert_rules)
    rules['intensity'].update(medium_min_mw=2, high_min_mw=4)
    rules['intensity']['saturated_is_high']['enabled'] = False
    with PostgresApiRepository(pool, rules).read() as reader:
        rows = reader.map_rows(MapQuery.parse('-61,-4,-59,-2', '24', '9'), NOW)
    assert sorted(p['intensity'] for p in rows['points']) == ['high', 'high', 'medium']
    assert rows['hexagons'][0]['n_high'] == 2


def test_map_skips_alert_levels_when_too_many_cells_are_in_view(api_database, alert_rules, monkeypatch):
    """RFC 0003: acima do limite de células res 4, o mapa não calcula o nível, em vez de ficar lento."""
    from backend.adapters.outbound.postgres import api as postgres_api
    from backend.domain.models.map_query import MapQuery
    pool, _, cell = api_database
    with postgres_api.PostgresApiRepository(pool, alert_rules).read() as reader:
        rows = reader.map_rows(MapQuery.parse('-61,-4,-59,-2', '24', '4'), NOW)
        assert set(rows['cell_daily']) == {h3.cell_to_parent(h3.int_to_str(cell), 4)}
        monkeypatch.setattr(postgres_api, 'MAX_ALERT_CELLS', 0)
        rows = reader.map_rows(MapQuery.parse('-61,-4,-59,-2', '24', '4'), NOW)
    assert rows['cell_daily'] is None and rows['data_through'] == date(2026, 11, 14)


def test_map_cache_expires_detections_when_time_moves_without_a_pipeline_update(api_database, alert_rules):
    from datetime import timedelta
    from backend.adapters.inbound.http.app import create_app
    from backend.adapters.outbound.postgres.api import PostgresApiRepository
    pool, _, _ = api_database
    tick = [NOW]
    with TestClient(create_app(repository=PostgresApiRepository(pool, alert_rules), clock=lambda: tick[0])) as client:
        url = '/api/v1/detections/recent?bbox=-61,-4,-59,-2&zoom=9&hours=24'
        first = client.get(url)
        assert first.json()['total_detections'] == 3
        tick[0] += timedelta(days=1)
        expired = client.get(url, headers={'If-None-Match': first.headers['etag']})
        assert expired.status_code == 200
        assert expired.json()['total_detections'] == 0
        assert expired.json()['features'] == []
        assert expired.headers['etag'] != first.headers['etag']

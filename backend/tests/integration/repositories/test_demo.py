import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.integration.repositories.test_history import database  # noqa: F401 - isolated PostGIS fixture
from tests.fakes.api import NOW


def test_generated_fixture_runs_the_application_factory(database, monkeypatch):  # noqa: F811 - pytest fixture injection
    script = Path(__file__).resolve().parents[3] / 'scripts' / 'demo_data.py'
    spec = importlib.util.spec_from_file_location('demo_data', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pool, _, _ = database
    with pool.connection() as conn:
        conn.execute(module.demo_sql(NOW))
        region = conn.execute("SELECT id FROM regioes WHERE nome='Synthetic demo'").fetchone()[0]
        # The app factory owns its own pool and inherits the isolated schema.
        monkeypatch.setenv('DATABASE_URL', conn.info.dsn)
    from backend.adapters.inbound.http.app import create_app
    with TestClient(create_app(clock=lambda: NOW)) as client:
        payload = {'area': {'type': 'region', 'region_id': region}}
        response = client.post('/api/v1/calendar', json=payload)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['months'][0]['detections'] == 15
        assert result['recent']['last_7_days']['detections'] == 7
        assert result['recent']['last_7_days']['n_high'] == 1
        assert result['coverage']['status'] == 'full'


def test_factory_requires_explicit_database(monkeypatch):
    from backend.adapters.inbound.http.app import create_app
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.raises(KeyError, match='DATABASE_URL'):
        with TestClient(create_app()):
            pass

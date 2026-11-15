import os
from pathlib import Path
from uuid import uuid4

import h3
import psycopg
from psycopg import sql
from psycopg_pool import ConnectionPool
import pytest

from backend.domain.models.area import Area
from backend.domain.models.error import CalendarError
from backend.adapters.outbound.postgres.history import PostgresHistoryRepository

pytestmark = pytest.mark.integration


@pytest.fixture
def database():
    url = os.environ.get('TEST_DATABASE_URL')
    if not url:
        pytest.skip('Set TEST_DATABASE_URL to run PostGIS integration tests.')
    schema = 'backend_test_' + uuid4().hex
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute('CREATE EXTENSION IF NOT EXISTS postgis')
        admin.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        try:
            with ConnectionPool(url, min_size=1, max_size=3,
                                kwargs={'options': f'-c search_path={schema},public'}) as pool:
                with pool.connection() as conn:
                    migrations = Path(__file__).resolve().parents[4] / 'data-pipeline' / 'migrations'
                    for migration in sorted(migrations.glob('*.sql')):
                        conn.execute(migration.read_text())
                    # Keep all data isolated in a unique schema. Never truncate shared tables.
                    assert conn.execute("SELECT to_regclass('config')::text").fetchone()[0] == 'config'
                    conn.execute("INSERT INTO config VALUES ('data_version','2026-11-14T14:00:00Z'), ('atualizado_em','2026-11-14T15:00:00Z')")
                    region = conn.execute("INSERT INTO regioes(nome,geom,fonte_poligono) VALUES ('Test',ST_Multi(ST_MakeEnvelope(-61,-4,-59,-2,4326)),'test') RETURNING id").fetchone()[0]
                    cell = h3.str_to_int(h3.latlng_to_cell(-3,-60,6))
                    conn.execute('INSERT INTO celula_regiao VALUES (%s,%s)', (cell,region))
                    conn.execute("INSERT INTO cobertura(regiao_id,satelite,data_inicio,data_fim) VALUES (%s,'SNPP','2012-02-01','2026-10-31'),(%s,'N20','2026-11-01','2026-11-14')", (region,region))
                    conn.execute("INSERT INTO agregados VALUES (%s,2020,9,%s,'SNPP','D',7,20)", (cell,region))
                yield pool, region, cell
        finally:
            admin.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def test_reads_translates_and_releases_connection(database):
    pool, region, _ = database
    result = PostgresHistoryRepository(pool).load(Area('region',region_id=region))
    assert result.counts[0]['raw_count'] == 7
    assert result.counts[0]['satellite'] == 'SNPP'
    assert result.meta['last_month'] == '2026-11'
    assert result.meta['data_version'] == '2026-11-14T14:00:00Z'
    assert result.meta['updated_at'] == '2026-11-14T15:00:00Z'
    assert result.coverage['status'] == 'full'
    assert result.area['biomes'][0]['fraction'] == pytest.approx(1)
    with pool.connection() as conn:
        assert conn.execute('SHOW transaction_read_only').fetchone()[0] == 'off'


def test_unknown_region_and_outside_coverage(database):
    pool, _, _ = database
    repository = PostgresHistoryRepository(pool)
    with pytest.raises(CalendarError) as error:
        repository.load(Area('region',region_id=9999))
    assert error.value.code == 'region_not_found'
    assert repository.load(Area('point',lat=50,lon=20,radius_km=1)).coverage['status'] == 'none'


def test_missing_version_is_not_silently_fabricated(database):
    pool, region, _ = database
    with pool.connection() as conn:
        conn.execute("DELETE FROM config WHERE chave='atualizado_em'")
    with pytest.raises(CalendarError, match='metadata'):
        PostgresHistoryRepository(pool).load(Area('region',region_id=region))


def test_snapshot_stays_consistent_during_concurrent_write(database):
    pool, region, _ = database
    # Intercept between SELECT config and SELECT counts; another connection commits.
    # Production adapter must still see the original version AND original count.
    from unittest.mock import patch
    from psycopg import Cursor
    execute = Cursor.execute
    changed = False
    def concurrent(cursor, query, params=None, **kwargs):
        nonlocal changed
        if isinstance(query,str) and 'SELECT regiao_id AS region_id, ano' in query and not changed:
            changed = True
            with pool.connection() as other:
                other.execute('UPDATE agregados SET focos_brutos=99')
                other.execute("UPDATE config SET valor='2026-11-15T00:00:00Z' WHERE chave='atualizado_em'")
        return execute(cursor,query,params,**kwargs)
    with patch.object(Cursor,'execute',concurrent):
        result = PostgresHistoryRepository(pool).load(Area('region',region_id=region))
    assert changed
    assert result.counts[0]['raw_count'] == 7
    assert result.meta['updated_at'] == '2026-11-14T15:00:00Z'
    assert PostgresHistoryRepository(pool).load(Area('region',region_id=region)).counts[0]['raw_count'] == 99


def test_partial_coverage_and_read_only_transaction(database):
    pool, _, _ = database
    from unittest.mock import patch
    from psycopg import Cursor
    execute = Cursor.execute
    checked = []
    def inspect(cursor, query, params=None, **kwargs):
        if query == 'SELECT chave, valor FROM config':
            execute(cursor, 'SHOW transaction_read_only')
            assert cursor.fetchone()['transaction_read_only'] == 'on'
            execute(cursor, 'SHOW transaction_isolation')
            assert cursor.fetchone()['transaction_isolation'] == 'repeatable read'
            checked.append(True)
        return execute(cursor,query,params,**kwargs)
    with patch.object(Cursor,'execute',inspect):
        result = PostgresHistoryRepository(pool).load(Area('point',lat=-3,lon=-60,radius_km=10))
    assert checked
    assert result.coverage['status'] == 'partial'
    assert 0 < result.coverage['covered_fraction'] < 1


def test_wrong_configured_resolution_rejected(database):
    pool, region, _ = database
    with pool.connection() as conn:
        conn.execute("UPDATE config SET valor='5' WHERE chave='h3_resolucao'")
    with pytest.raises(CalendarError):
        PostgresHistoryRepository(pool).load(Area('region',region_id=region))


def test_calendar_service_with_real_postgres_and_factors(database):
    from datetime import date
    from backend.application.calendar import CalendarService
    pool, region, cell = database
    with pool.connection() as conn:
        conn.execute("INSERT INTO cobertura(regiao_id,satelite,data_inicio,data_fim) VALUES (%s,'Aqua','2003-01-01','2012-01-31')",(region,))
        # Distinct cells are summed by region, month and day/night in SQL.
        second = h3.str_to_int(next(c for c in h3.grid_disk(h3.int_to_str(cell),1) if h3.str_to_int(c) != cell))
        conn.execute('INSERT INTO celula_regiao VALUES (%s,%s)',(second,region))
        conn.execute("INSERT INTO agregados VALUES (%s,2003,1,%s,'Aqua','D',2,4),(%s,2003,1,%s,'Aqua','D',3,6)", (cell,region,second,region))
        conn.execute("INSERT INTO fatores_harmonizacao(regiao_id,satelite_origem,satelite_destino,mes,periodo,ano_calibracao,fator) VALUES (%s,'Aqua','SNPP',1,'D',2013,2),(%s,'Aqua','SNPP',1,'D',2014,4)",(region,region))
    service=CalendarService(PostgresHistoryRepository(pool),clock=lambda:date(2026,11,14))
    result=service.calculate(Area('region',region_id=region),'2003-01','2003-01')
    assert result['area']['n_cells'] == 2
    assert result['months'][0]['raw_count'] == 5
    assert result['months'][0]['detections'] == 15
    assert result['months'][0]['band_low'] == pytest.approx(10.5)
    assert result['months'][0]['band_high'] == pytest.approx(19.5)


def test_rollback_releases_pool_after_query_failure(database):
    pool, region, _ = database
    with pool.connection() as conn:
        conn.execute('ALTER TABLE fatores_harmonizacao RENAME TO saved_factors')
    with pytest.raises(psycopg.errors.UndefinedTable):
        PostgresHistoryRepository(pool).load(Area('region',region_id=region))
    with pool.connection() as conn:
        conn.execute('ALTER TABLE saved_factors RENAME TO fatores_harmonizacao')
    assert PostgresHistoryRepository(pool).load(Area('region',region_id=region)).counts[0]['raw_count'] == 7


@pytest.mark.parametrize('version', ['2026-11-14', '2026-11-14T17:30:00Z'])
def test_preserves_legacy_and_intraday_data_versions(database, version):
    pool, region, _ = database
    with pool.connection() as conn:
        conn.execute("UPDATE config SET valor=%s WHERE chave='data_version'", (version,))
    assert PostgresHistoryRepository(pool).load(Area('region', region_id=region)).meta['data_version'] == version


def test_rejects_version_timestamp_without_timezone(database):
    pool, region, _ = database
    with pool.connection() as conn:
        conn.execute("UPDATE config SET valor='2026-11-14T17:30:00' WHERE chave='data_version'")
    with pytest.raises(CalendarError, match='metadata'):
        PostgresHistoryRepository(pool).load(Area('region', region_id=region))

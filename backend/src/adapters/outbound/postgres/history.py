"""Read-only, bounded-query adapter for the pipeline's Portuguese schema."""
from datetime import date, datetime
from math import fsum

import h3
from psycopg.rows import dict_row

from backend.domain.calculations.spatial import MAX_CELLS, cells_for_area
from backend.domain.models.error import CalendarError
from backend.domain.models.snapshot import HistorySnapshot


class PostgresHistoryRepository:
    def __init__(self, pool):
        """Receive a psycopg_pool.ConnectionPool owned by the application."""
        self.pool = pool

    def load(self, area):
        # The snapshot starts before metadata, so a concurrent pipeline commit
        # cannot mix versions, counts and factors in one result.
        with self.pool.connection() as connection:
            with connection.transaction():
                connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                connection.execute("SET LOCAL TIME ZONE 'UTC'")
                with connection.cursor(row_factory=dict_row) as cursor:
                    return self._load(cursor, area)

    def _load(self, cursor, area):
        cursor.execute("SELECT chave, valor FROM config")
        config = {r['chave']: r['valor'] for r in cursor.fetchall()}
        try:
            resolution = int(config['h3_resolucao'])
            version = config['data_version']
            if len(version) == 10:  # Historical snapshots used date-only versions.
                date.fromisoformat(version)
            elif datetime.fromisoformat(version.replace('Z', '+00:00')).utcoffset() is None:
                raise ValueError
            timestamp = datetime.fromisoformat(config['atualizado_em'].replace('Z', '+00:00'))
            if timestamp.utcoffset() is None or resolution != 6:
                raise ValueError
        except (KeyError, ValueError):
            raise CalendarError('invalid_data', 'Dataset metadata is missing or invalid.') from None
        cursor.execute("SELECT h3 FROM agregados LIMIT 100")
        if any(not h3.is_valid_cell(h3.int_to_str(r['h3'])) or h3.get_resolution(h3.int_to_str(r['h3'])) != resolution
               for r in cursor.fetchall()):
            raise CalendarError('invalid_data', 'Aggregate H3 resolution does not match configuration.')
        cursor.execute("SELECT max(data_fim) AS last_day FROM cobertura WHERE satelite IN ('Aqua','SNPP','N20')")
        last_day = cursor.fetchone()['last_day']
        if last_day is None:
            raise CalendarError('invalid_data', 'No dataset coverage is available.')
        meta = {'data_version': config['data_version'], 'updated_at': config['atualizado_em'],
                'h3_resolution': resolution, 'last_month': last_day.strftime('%Y-%m'), 'scale': 'VIIRS'}
        if area.type == 'region':
            cursor.execute('SELECT id FROM regioes WHERE id = %s', (area.region_id,))
            if cursor.fetchone() is None:
                raise CalendarError('region_not_found', 'Region not found.')
            cursor.execute('SELECT h3 FROM celula_regiao WHERE regiao_id = %s LIMIT %s',
                           (area.region_id, MAX_CELLS + 1))
            cells = tuple(h3.int_to_str(r['h3']) for r in cursor.fetchall())
        else:
            cells = cells_for_area(area, resolution)
        if len(cells) > MAX_CELLS:
            raise CalendarError('area_too_large', 'The selected area is too large.')
        if not cells:
            raise CalendarError('invalid_data', 'The region has no registered cells.')
        ids = [h3.str_to_int(cell) for cell in cells]
        areas = {h3.str_to_int(cell): h3.cell_area(cell, unit='km^2') for cell in cells}
        total_area = fsum(areas.values())
        cursor.execute('''SELECT cr.h3, cr.regiao_id AS region_id, r.nome AS name
            FROM celula_regiao cr JOIN regioes r ON r.id = cr.regiao_id
            WHERE cr.h3 = ANY(%s::bigint[]) AND EXISTS
            (SELECT 1 FROM cobertura c WHERE c.regiao_id = cr.regiao_id
             AND c.satelite IN ('Aqua','SNPP','N20'))''', (ids,))
        assigned = cursor.fetchall()
        covered_ids = [r['h3'] for r in assigned]
        regions = sorted({r['region_id'] for r in assigned})
        covered_area = fsum(areas[r['h3']] for r in assigned)
        fraction = covered_area / total_area
        status = 'none' if not assigned else 'full' if len(assigned) == len(cells) else 'partial'
        selection = {'type': area.type, 'n_cells': len(cells), 'area_km2': total_area,
                     'biomes': [{'region_id': region, 'name': next(r['name'] for r in assigned if r['region_id'] == region),
                                 'fraction': fsum(areas[r['h3']] for r in assigned if r['region_id'] == region) / total_area}
                                for region in regions]}
        coverage = {'status': status, 'covered_fraction': fraction,
                    'message': None if status == 'full' else 'Some or all of this area has no data. Current coverage: ' + config.get('cobertura_pais', 'unknown') + '.'}
        cursor.execute('''SELECT regiao_id AS region_id, ano AS year, mes AS month,
            satelite AS satellite, periodo AS daynight, sum(focos_brutos)::bigint AS raw_count,
            sum(frp_soma) AS frp_sum FROM agregados WHERE h3 = ANY(%s::bigint[])
            GROUP BY regiao_id, ano, mes, satelite, periodo''', (covered_ids,))
        counts = tuple(cursor.fetchall())
        cursor.execute('''SELECT regiao_id AS region_id, mes AS month, periodo AS daynight,
            ano_calibracao AS calibration_year, fator AS factor FROM fatores_harmonizacao
            WHERE regiao_id = ANY(%s::int[]) AND satelite_origem = 'Aqua' AND satelite_destino = 'SNPP' ''', (regions,))
        factors = tuple(cursor.fetchall())
        cursor.execute('''SELECT regiao_id AS region_id, satelite AS satellite,
            data_inicio AS start, data_fim AS end FROM cobertura WHERE regiao_id = ANY(%s::int[])''', (regions,))
        periods = tuple(cursor.fetchall())
        cursor.execute('SELECT data AS day, satelite AS satellite FROM dias_sem_dados')
        missing = frozenset((r['day'], r['satellite']) for r in cursor.fetchall())
        # NRT-only partial index prevents a full scan of historical SP detections.
        cursor.execute('''SELECT DISTINCT extract(year FROM datahora_utc)::int AS year,
            extract(month FROM datahora_utc)::int AS month, satelite AS satellite
            FROM focos WHERE qualidade = 'NRT' AND h3 = ANY(%s::bigint[])
            AND confianca IN ('nominal','alta') AND (tipo = 0 OR tipo IS NULL) AND frp > 0''', (covered_ids,))
        provisional = frozenset((r['year'], r['month'], r['satellite']) for r in cursor.fetchall())
        return HistorySnapshot(meta, selection, coverage, counts, factors, periods, missing, provisional)

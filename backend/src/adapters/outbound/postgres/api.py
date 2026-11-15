"""PostGIS read unit of work. Portuguese column/value translation lives here."""
import os
from collections import OrderedDict
from contextlib import contextmanager
from datetime import date, datetime, timedelta, UTC
from threading import Lock

import h3
from psycopg.rows import dict_row

from backend.adapters.outbound.postgres.cell_level_cache import CellLevelCache
from backend.adapters.outbound.postgres.history import PostgresHistoryRepository
from backend.application.audit import DETECTION_LIMIT
from backend.domain.models.error import CalendarError
from backend.domain.models.month import SATELLITE_SWITCHES, Month
from backend.domain.intensity import intensity_class
from backend.domain.calculations.cell_alerts import cell_alerts, history_ranges
from backend.domain.calculations.map_features import ALERT_RESOLUTION

POINT_LIMIT = 50_000
DATABASE_RESOLUTION = 6
# Above this many resolution 4 cells with recent fire in view, the map skips alert levels instead of slowing down.
# The worst 7-day week of 2012-2024 had 3,069 cells with fire in Brazil (P95 2,770, median 1,378).
MAX_ALERT_CELLS = 4_000
# Risk scores older than this many days are not shown (env `RISK_MAX_AGE_DAYS`): the job writes them every day.
DEFAULT_RISK_MAX_AGE_DAYS = 2
VALID_DETECTION = "confianca IN ('nominal','alta') AND (tipo = 0 OR tipo IS NULL) AND frp > 0"
VIIRS_START = SATELLITE_SWITCHES[0][0]


def satellite_sql(column, cast):
    """SQL filter for the satellite of each day, built from SATELLITE_SWITCHES (constants, never user input)."""
    previous = ['Aqua'] + [satellite for _, satellite in SATELLITE_SWITCHES]
    cases = ' '.join(f"WHEN {column} < '{start.isoformat()}'::{cast} THEN '{before}'"
                     for (start, _), before in zip(SATELLITE_SWITCHES, previous))
    return f"satelite = CASE {cases} ELSE '{SATELLITE_SWITCHES[-1][1]}' END"


SELECTED_SATELLITE = satellite_sql('datahora_utc', 'timestamptz')
# Observed VIIRS satellites and the days each one counts (the last one has no end).
VIIRS_DAYS = {satellite: (start, (SATELLITE_SWITCHES[i + 1][0] - timedelta(days=1))
                          if i + 1 < len(SATELLITE_SWITCHES) else date.max)
              for i, (start, satellite) in enumerate(SATELLITE_SWITCHES)}
DETECTION_COLUMNS = """satelite AS satellite, lat AS latitude, lon AS longitude,
    datahora_utc AS acquired_utc, CASE confianca WHEN 'alta' THEN 'high'
    WHEN 'baixa' THEN 'low' ELSE 'nominal' END AS confidence,
    frp, periodo AS daynight, qualidade AS quality, arquivo_origem AS source_file"""


def utc_text(value):
    return value.astimezone(UTC).isoformat().replace('+00:00', 'Z')


def coverage_intervals(snapshot):
    """Intersect the regions' observed VIIRS coverage, retaining gaps."""
    regions = {row['region_id'] for row in snapshot.area['biomes']}
    common = [(VIIRS_START, date.max)]
    for region in regions:
        available = []
        for row in snapshot.periods:
            if row['region_id'] != region or row['satellite'] not in VIIRS_DAYS:
                continue
            first = max(row['start'], VIIRS_DAYS[row['satellite']][0])
            last = min(row['end'], VIIRS_DAYS[row['satellite']][1])
            if first <= last:
                available.append((first, last))
        common = [(max(a, c), min(b, d)) for a, b in common for c, d in available if max(a, c) <= min(b, d)]
    merged = []
    for first, last in sorted(common):
        if merged and (first - merged[-1][1]).days <= 1:
            merged[-1] = (merged[-1][0], max(last, merged[-1][1]))
        else:
            merged.append((first, last))
    return merged


class PostgresApiRepository:
    def __init__(self, pool, rules):
        self.pool, self.rules = pool, rules
        self.factor_versions = OrderedDict()
        self.factor_lock = Lock()
        self.cell_levels = CellLevelCache()

    @contextmanager
    def read(self):
        with self.pool.connection() as connection, connection.transaction():
            connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            connection.execute("SET LOCAL TIME ZONE 'UTC'")
            with connection.cursor(row_factory=dict_row) as cursor:
                yield PostgresApiReader(cursor, self)


class PostgresApiReader(PostgresHistoryRepository):
    def __init__(self, cursor, repository):
        self.cursor, self.repository = cursor, repository

    def meta(self):
        return self._metadata(self.cursor)[0]

    def regions(self):
        self.cursor.execute('''SELECT id AS region_id, nome AS name, fonte_poligono AS source,
            ARRAY[ST_XMin(geom::box3d),ST_YMin(geom::box3d),ST_XMax(geom::box3d),ST_YMax(geom::box3d)] AS bbox
            FROM regioes ORDER BY nome,id''')
        return self.cursor.fetchall()

    def history(self, area):
        return self._load(self.cursor, area)

    def _factors(self, cursor, regions, version):
        with self.repository.factor_lock:
            cache = self.repository.factor_versions
            if version not in cache:
                cursor.execute("""SELECT regiao_id AS region_id, mes AS month, periodo AS daynight,
                    ano_calibracao AS calibration_year, fator AS factor FROM fatores_harmonizacao
                    WHERE satelite_origem='Aqua' AND satelite_destino='SNPP'""")
                cache[version] = tuple(cursor.fetchall())
                while len(cache) > 2:
                    cache.popitem(last=False)
            return tuple(row for row in cache[version] if row['region_id'] in regions)

    def _intensity_sql(self):
        rules = self.repository.rules['intensity']
        saturated = rules['saturated_is_high']
        enabled = saturated['enabled'] and 'VIIRS' in saturated['sensors']
        return ("CASE WHEN (%s AND sensor='VIIRS' AND confianca='alta') OR frp >= %s THEN 'high' "
                "WHEN frp >= %s THEN 'medium' ELSE 'low' END",
                (enabled, rules['high_min_mw'], rules['medium_min_mw']))

    def recent(self, snapshot):
        coverage = coverage_intervals(snapshot)
        if not coverage:
            raise CalendarError('invalid_data', 'No observed VIIRS coverage is available.')
        through = coverage[-1][1]
        ids = [h3.str_to_int(cell) for cell in snapshot.cells]
        self.cursor.execute(f"""SELECT data AS day, sum(focos_brutos)::bigint AS detections
            FROM agregados_diarios WHERE h3=ANY(%s::bigint[]) AND data >= %s AND data <= %s
            AND {satellite_sql('data', 'date')} GROUP BY data""", (ids, VIIRS_START, through))
        daily = {row['day']: row['detections'] for row in self.cursor.fetchall()}
        start = min(through.replace(day=1), through - timedelta(days=6))
        intensity, params = self._intensity_sql()
        self.cursor.execute(f"""SELECT datahora_utc::date AS day, count(*)::bigint AS n_high FROM focos
            WHERE h3=ANY(%s::bigint[]) AND datahora_utc >= %s AND datahora_utc < %s
            AND {VALID_DETECTION} AND {SELECTED_SATELLITE} AND ({intensity})='high' GROUP BY 1""",
            (ids, datetime.combine(start, datetime.min.time(), UTC),
             datetime.combine(through + timedelta(days=1), datetime.min.time(), UTC), *params))
        high = {row['day']: row['n_high'] for row in self.cursor.fetchall()}
        missing = {day for day, satellite in snapshot.missing if satellite == Month(day.year, day.month).satellite}
        return {'data_through': through, 'daily': daily, 'high': high, 'coverage': coverage, 'missing': missing}

    def detections(self, snapshot, first, final):
        ids = [h3.str_to_int(cell) for cell in snapshot.cells]
        params = (ids, datetime.combine(first, datetime.min.time(), UTC), datetime.combine(final, datetime.min.time(), UTC))
        where = f'h3=ANY(%s::bigint[]) AND datahora_utc >= %s AND datahora_utc < %s AND {VALID_DETECTION} AND {SELECTED_SATELLITE}'
        self.cursor.execute(f'SELECT count(*) AS total FROM focos WHERE {where}', params)
        total = self.cursor.fetchone()['total']
        if total > DETECTION_LIMIT:
            return total, []
        self.cursor.execute(f'SELECT {DETECTION_COLUMNS} FROM focos WHERE {where} ORDER BY datahora_utc,satelite,lat,lon', params)
        rows = self.cursor.fetchall()
        for row in rows:
            row['acquired_utc'] = utc_text(row['acquired_utc'])
        return total, rows

    def map_rows(self, query, now):
        west, south, east, north = query.bbox
        intensity, intensity_params = self._intensity_sql()
        # The NRT partial index bounds time before applying the viewport filter.
        where = f"""qualidade='NRT' AND datahora_utc >= %s AND datahora_utc <= %s
            AND lon BETWEEN %s AND %s AND lat BETWEEN %s AND %s AND {VALID_DETECTION}
            AND {SELECTED_SATELLITE} AND sensor='VIIRS'"""
        params = (now - timedelta(hours=query.hours), now, west, east, south, north)
        self.cursor.execute(f"""SELECT h3, count(*)::bigint AS detections, min(datahora_utc) AS first_acquired,
            count(*) FILTER (WHERE intensity='low')::bigint AS n_low,
            count(*) FILTER (WHERE intensity='medium')::bigint AS n_medium,
            count(*) FILTER (WHERE intensity='high')::bigint AS n_high
            FROM (SELECT h3, datahora_utc, {intensity} AS intensity FROM focos WHERE {where}) selected GROUP BY h3""",
            (*intensity_params, *params))
        grouped = self.cursor.fetchall()
        total = sum(row['detections'] for row in grouped)
        points = None
        if query.points and total <= POINT_LIMIT:
            self.cursor.execute(f"SELECT {DETECTION_COLUMNS} FROM focos WHERE {where} ORDER BY datahora_utc,satelite,lat,lon", params)
            points = self.cursor.fetchall()
            for row in points:
                row['acquired_utc'] = utc_text(row['acquired_utc'])
                row['intensity'] = intensity_class(row['frp'], 'VIIRS', row['confidence'], self.repository.rules['intensity'])
        # Even without another pipeline commit, the oldest detection leaves the
        # sliding window. Empty results are rechecked after one minute.
        expires_at = (min(row['first_acquired'] for row in grouped) + timedelta(hours=query.hours)
                      if grouped else now + timedelta(minutes=1))
        return {'total': total, 'hexagons': grouped, 'points': points, 'expires_at': expires_at,
                **self._cell_history(grouped, now), 'risk': self._risk_scores(grouped, now)}

    def _risk_scores(self, grouped, now):
        """Scores of the trained model (`risco_celulas`) for the resolution 4 cells in view, or None without a fresh day."""
        parents = {h3.cell_to_parent(h3.int_to_str(row['h3']), ALERT_RESOLUTION) for row in grouped}
        if not parents or len(parents) > MAX_ALERT_CELLS:
            return None
        self.cursor.execute("SELECT to_regclass('risco_celulas') IS NOT NULL AS present")
        if not self.cursor.fetchone()['present']:       # migration 005 not applied yet: the map works without risk
            return None
        newest = now.date() - timedelta(days=int(os.environ.get('RISK_MAX_AGE_DAYS', DEFAULT_RISK_MAX_AGE_DAYS)))
        self.cursor.execute("""SELECT data_ref, max(calculado_em) AS scored_at,
            (array_agg(modelo_versao ORDER BY calculado_em DESC))[1] AS model_version FROM risco_celulas
            WHERE data_ref = (SELECT max(data_ref) FROM risco_celulas WHERE data_ref <= %s AND data_ref >= %s)
            GROUP BY data_ref""", (now.date(), newest))
        head = self.cursor.fetchone()
        if head is None:
            return None
        self.cursor.execute("SELECT h3, prob FROM risco_celulas WHERE data_ref = %s AND h3 = ANY(%s::bigint[])",
                            (head['data_ref'], [h3.str_to_int(cell) for cell in parents]))
        return {**head, 'by_cell': {h3.int_to_str(row['h3']): float(row['prob']) for row in self.cursor.fetchall()}}

    def _cell_history(self, grouped, now):
        """Daily VIIRS counts of each resolution 4 cell with recent fire, for its alert level (RFC 0003)."""
        parents = {h3.cell_to_parent(h3.int_to_str(row['h3']), ALERT_RESOLUTION) for row in grouped}
        # The last covered day, not the last day with detections: `agregados_diarios` has no row for a day without fire.
        # A coverage row that is still running (it ends after today) counts up to today, so cap the end at the clock.
        self.cursor.execute("SELECT least(max(data_fim), %s::date) AS through FROM cobertura "
                            "WHERE satelite = ANY(%s) AND data_inicio <= %s",
                            (now.date(), list(VIIRS_DAYS), now.date()))
        through = self.cursor.fetchone()['through']
        if through is None:  # no coverage rows: fall back to the last day with detections
            self.cursor.execute(f"SELECT max(data) AS through FROM agregados_diarios WHERE data <= %s AND {satellite_sql('data', 'date')}",
                                (now.date(),))
            through = self.cursor.fetchone()['through']
        if not parents or through is None or len(parents) > MAX_ALERT_CELLS:
            return {'cell_levels': None, 'cell_daily': None, 'data_through': through, 'coverage_start': VIIRS_START}
        # The level of a cell depends on the data, not on the viewport: keep it per data version (PR #86 review),
        # so dragging or zooming the map only computes the cells not seen yet.
        meta = self.meta()
        levels = self.repository.cell_levels.levels((meta['updated_at'], meta['data_version'], through), sorted(parents),
                                                    lambda missing: self._compute_levels(missing, through))
        return {'cell_levels': levels, 'cell_daily': None, 'data_through': through, 'coverage_start': VIIRS_START}

    def _compute_levels(self, parents, through):
        child_to_parent = {h3.str_to_int(child): parent for parent in parents
                           for child in h3.cell_to_children(parent, DATABASE_RESOLUTION)}
        ranges = history_ranges(through, self.repository.rules)
        between = ' OR '.join('data BETWEEN %s AND %s' for _ in ranges)
        self.cursor.execute(f"""SELECT h3, data AS day, sum(focos_brutos)::bigint AS detections FROM agregados_diarios
            WHERE h3=ANY(%s::bigint[]) AND ({between}) AND {satellite_sql('data', 'date')} GROUP BY h3, data""",
                            (list(child_to_parent), *[day for pair in ranges for day in pair]))
        cell_daily = {parent: {} for parent in parents}
        for row in self.cursor.fetchall():
            daily = cell_daily[child_to_parent[row['h3']]]
            daily[row['day']] = daily.get(row['day'], 0) + row['detections']
        return cell_alerts(through, cell_daily, self.repository.rules, VIIRS_START)

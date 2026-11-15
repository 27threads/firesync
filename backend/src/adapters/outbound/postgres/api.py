"""PostGIS read unit of work. Portuguese column/value translation lives here."""
from collections import OrderedDict
from contextlib import contextmanager
from datetime import date, datetime, timedelta, UTC
from threading import Lock

import h3
from psycopg.rows import dict_row

from backend.adapters.outbound.postgres.history import PostgresHistoryRepository
from backend.application.audit import DETECTION_LIMIT
from backend.domain.models.error import CalendarError
from backend.domain.models.month import Month
from backend.domain.intensity import intensity_class

POINT_LIMIT = 50_000
VALID_DETECTION = "confianca IN ('nominal','alta') AND (tipo = 0 OR tipo IS NULL) AND frp > 0"
# Same monthly boundaries as Month.satellite; used for queries spanning a switch.
SELECTED_SATELLITE = """satelite = CASE WHEN datahora_utc < '2012-02-01'::timestamptz THEN 'Aqua'
    WHEN datahora_utc < '2026-11-01'::timestamptz THEN 'SNPP' ELSE 'N20' END"""
DETECTION_COLUMNS = """satelite AS satellite, lat AS latitude, lon AS longitude,
    datahora_utc AS acquired_utc, CASE confianca WHEN 'alta' THEN 'high'
    WHEN 'baixa' THEN 'low' ELSE 'nominal' END AS confidence,
    frp, periodo AS daynight, qualidade AS quality, arquivo_origem AS source_file"""


def utc_text(value):
    return value.astimezone(UTC).isoformat().replace('+00:00', 'Z')


def coverage_intervals(snapshot):
    """Intersect the regions' observed VIIRS coverage, retaining gaps."""
    regions = {row['region_id'] for row in snapshot.area['biomes']}
    common = [(date(2012, 2, 1), date.max)]
    for region in regions:
        available = []
        for row in snapshot.periods:
            if row['region_id'] != region or row['satellite'] not in ('SNPP', 'N20'):
                continue
            first = max(row['start'], date(2012, 2, 1) if row['satellite'] == 'SNPP' else date(2026, 11, 1))
            last = min(row['end'], date(2026, 10, 31) if row['satellite'] == 'SNPP' else date.max)
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
        self.cursor.execute("""SELECT data AS day, sum(focos_brutos)::bigint AS detections
            FROM agregados_diarios WHERE h3=ANY(%s::bigint[]) AND data >= '2012-02-01' AND data <= %s
            AND satelite = CASE WHEN data < '2026-11-01' THEN 'SNPP' ELSE 'N20' END GROUP BY data""", (ids, through))
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
        return {'total': total, 'hexagons': grouped, 'points': points, 'expires_at': expires_at}

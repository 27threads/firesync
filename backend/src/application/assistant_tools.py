"""Tools the assistant model may call (RFC 0004). Each one runs the same use case as an HTTP route."""
import json

import h3

from backend.application.api import calculate_calendar, calendar_cache_key, parse_request
from backend.domain.calculations.map_features import map_result
from backend.domain.models.error import CalendarError
from backend.domain.models.map_query import MapQuery

MAX_MONTHS_SENT = 36
TOP_MONTHS = 12
TOP_HEXAGONS = 10
MAP_WINDOWS = (24, 72, 168)  # the hours GET /detections/recent accepts
MAP_ZOOM = '4'  # resolution-4 hexagons: the whole coverage fits in one answer
MONTH_FIELDS = ('month', 'detections', 'source', 'missing_days', 'incomplete', 'provisional', 'anomaly_pct')
YEAR_FIELDS = ('year', 'detections', 'rank', 'complete', 'source')
ONE_YEAR_FIELDS = tuple(field for field in YEAR_FIELDS if field != 'rank')
RISK_NOTE = ('Risk tiers show how often each tier was followed by relevant fire in the next 14 days in past '
             'years. They are a historical frequency, not a forecast for this date.')

REGION_ID = {'type': 'integer', 'description': 'region_id from list_regions'}
MONTH = {'type': 'string', 'pattern': r'^\d{4}-\d{2}$', 'description': 'YYYY-MM, UTC'}
TOOL_SPECS = [
    {'type': 'function', 'function': {
        'name': 'list_regions', 'description': 'List the regions (Brazilian biomes) with their region_id.',
        'parameters': {'type': 'object', 'properties': {}}}},
    {'type': 'function', 'function': {
        'name': 'get_calendar',
        'description': 'Monthly harmonized hotspot counts for a region and period: months (or top months for long '
                       'periods), yearly ranking, seasonality and indicators. Period defaults to the whole series; '
                       'for one year, pass that year (2024-01 to 2024-12).',
        'parameters': {'type': 'object', 'required': ['region_id'],
                       'properties': {'region_id': REGION_ID, 'start': MONTH, 'end': MONTH}}}},
    {'type': 'function', 'function': {
        'name': 'get_recent',
        'description': 'Last 7 days and month to date of a region against the typical value for the season, '
                       'with the alert level.',
        'parameters': {'type': 'object', 'required': ['region_id'], 'properties': {'region_id': REGION_ID}}}},
    {'type': 'function', 'function': {
        'name': 'get_fire_map',
        'description': 'Where it is burning now in the whole coverage: busiest hexagons with their center, '
                       'cells to look at first and 14-day risk tiers.',
        'parameters': {'type': 'object', 'properties': {
            'hours': {'type': 'integer', 'enum': list(MAP_WINDOWS), 'description': 'Time window up to now'}}}}},
]


def pick(row, fields):
    return {field: row.get(field) for field in fields}


def readable(value):
    """What the model reads: whole counts, '*_pct' fractions as percents. Models misread raw floats in testing."""
    if isinstance(value, dict):
        return dict(readable_item(name, item) for name, item in value.items())
    if isinstance(value, list):
        return [readable(item) for item in value]
    if isinstance(value, float):
        return round(value) if abs(value) >= 100 else round(value, 2)
    return value


def readable_item(name, value):
    if name.endswith('_pct'):
        numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
        return name[:-4] + '_percent', round(value * 100, 1) if numeric else value
    return name, readable(value)


def highlights(months, years, indicators):
    """Peak, low and totals picked by code, so the model never has to search or add up a list."""
    counted = [month for month in months if month['detections'] is not None]
    found = {'period': f"{months[0]['month']} to {months[-1]['month']}" if months else None,
             'total_detections': indicators.get('total_detections')}
    if counted:
        peak = max(counted, key=lambda month: month['detections'])
        low = min(counted, key=lambda month: month['detections'])
        found.update(peak_month=pick(peak, ('month', 'detections', 'anomaly_pct')),
                     lowest_month=pick(low, ('month', 'detections', 'anomaly_pct')))
    complete = [year for year in years if year.get('complete')]
    if len(complete) > 1:
        found['busiest_year'] = pick(max(complete, key=lambda year: year['detections']), ('year', 'detections'))
    return found


def calendar_summary(body):
    months = body['months']
    summary = {'highlights': highlights(months, body['years'], body['indicators']),
               'area': body['area'], 'coverage': body['coverage'], 'indicators': body['indicators'],
               # A rank inside a one-year period is always 1 and reads as 'record year', so it goes only with more years.
               'years': [pick(year, YEAR_FIELDS if len(body['years']) > 1 else ONE_YEAR_FIELDS)
                         for year in body['years']],
               'seasonality': [pick(month, ('month_of_year', 'median')) for month in body['seasonality']]}
    if len(months) <= MAX_MONTHS_SENT:
        summary['months'] = [pick(month, MONTH_FIELDS) for month in months]
    else:
        busiest = sorted(months, key=lambda month: month['detections'] or 0, reverse=True)
        summary['top_months'] = [pick(month, MONTH_FIELDS) for month in busiest[:TOP_MONTHS]]
    return readable(summary)


def area_name(body):
    biomes = body['area'].get('biomes') or []
    return biomes[0]['name'] if len(biomes) == 1 else None


class Toolbox:
    """Runs each tool in its own short read transaction, so no database connection waits on the language model.

    Collects what the answer may show: actions, notes, sources and the tool results used to check its numbers.
    """

    def __init__(self, repository, meta, now, rules, risk_rules, cache=None):
        self.repository, self.meta, self.now = repository, meta, now
        self.rules, self.risk_rules, self.cache = rules, risk_rules, cache
        self.handlers = {'list_regions': self.list_regions, 'get_calendar': self.get_calendar,
                         'get_recent': self.get_recent, 'get_fire_map': self.get_fire_map}
        self.actions, self.notes, self.sources, self.results = [], [], [], []

    def run(self, name, arguments):
        handler = self.handlers.get(name)
        if handler is None:
            return failure('unknown_tool', f'No tool named {name}.')
        try:
            parsed = json.loads(arguments or '{}')
            if not isinstance(parsed, dict):
                raise TypeError
            result, actions, notes, source = handler(**parsed)
        except CalendarError as error:  # a ValueError too, so it must come first
            return failure(error.code, str(error))
        except (TypeError, ValueError):
            return failure('invalid_arguments', 'Arguments do not match the tool parameters.')
        for items, new in ((self.actions, actions), (self.notes, notes), (self.sources, [source])):
            items += [item for item in new if item not in items]
        self.results.append(result)
        return result

    def context(self):
        return (f'Today is {self.now.date().isoformat()} (UTC). Data covers 2003-01 to '
                f"{self.meta['last_month']}; resolve relative dates like 'last year' from today.")

    def source(self, endpoint, **details):
        return {'endpoint': endpoint, **{key: value for key, value in details.items() if value is not None},
                'data_version': self.meta['data_version'], 'updated_at': self.meta['updated_at']}

    def list_regions(self):
        with self.repository.read() as reader:
            regions = [pick(region, ('region_id', 'name')) for region in reader.regions()]
        return regions, [], [], self.source('GET /api/v1/regions')

    def calendar(self, region_id, start=None, end=None):
        request = {'area': {'type': 'region', 'region_id': region_id},
                   **{key: value for key, value in (('start', start), ('end', end)) if value is not None}}
        area, first, last = parse_request(request)
        key = calendar_cache_key(request, self.now.date(), self.meta)
        body = self.cache.get(key) if self.cache else None
        if body is None:
            with self.repository.read() as reader:
                _, body = calculate_calendar(reader, area, first, last, self.now.date(), self.rules)
            if self.cache:
                self.cache.put(key, body)
        months = body['months']
        source = self.source('POST /api/v1/calendar', area=request['area'], region=area_name(body),
                             start=months[0]['month'] if months else None, end=months[-1]['month'] if months else None)
        return request, body, source

    def get_calendar(self, region_id, start=None, end=None):
        request, body, source = self.calendar(region_id, start, end)
        return calendar_summary(body), [{'type': 'show_calendar', **request},
                                        {'type': 'download_export', **request}], [], source

    def get_recent(self, region_id):
        request, body, source = self.calendar(region_id)
        result = {'area': body['area'], 'coverage': body['coverage'], 'recent': body.get('recent')}
        return readable(result), [{'type': 'show_calendar', **request}], [], source

    def get_fire_map(self, hours=24):
        with self.repository.read() as reader:
            boxes = [region['bbox'] for region in reader.regions()]
            bbox = ','.join(str(value) for value in (min(b[0] for b in boxes), min(b[1] for b in boxes),
                                                     max(b[2] for b in boxes), max(b[3] for b in boxes)))
            query = MapQuery.parse(bbox, str(hours), MAP_ZOOM, 'hexagons')
            rows = reader.map_rows(query, self.now)
        body = map_result(query, rows, self.meta['updated_at'], self.rules, self.risk_rules)
        hexagons = sorted(body['features'], key=lambda feature: feature['properties']['detections'], reverse=True)
        alerts = body.get('alerts') or {}
        risk = alerts.get('risk')
        result = {'hours': body['hours'], 'windows_available_hours': list(MAP_WINDOWS),
                  'total_detections': body['total_detections'],
                  'top_hexagons': [hexagon_summary(feature['properties']) for feature in hexagons[:TOP_HEXAGONS]],
                  'look_first': [look_first_summary(cell) for cell in alerts.get('priority', [])[:TOP_HEXAGONS]],
                  'risk_tiers': risk['tiers'] if risk else None}
        return (readable(result), [], [RISK_NOTE] if risk else [],
                self.source('GET /api/v1/detections/recent', hours=query.hours))


def place(lat, lon):
    # Written out with hemispheres: given bare signed numbers, models swapped N/S and lat/lon in testing.
    return f"{abs(lat):.2f}°{'N' if lat >= 0 else 'S'}, {abs(lon):.2f}°{'E' if lon >= 0 else 'W'}"


def look_first_summary(cell):
    lon, lat = cell['center']  # the map contract sends [lon, lat]
    return {**{key: value for key, value in cell.items() if key != 'center'}, 'center': place(lat, lon)}


def hexagon_summary(properties):
    lat, lon = h3.cell_to_latlng(properties['h3'])
    return {'center': place(lat, lon), 'detections': properties['detections'],
            'alert_level': properties.get('alert_level'), 'risk_tier': properties.get('risk_tier')}


def failure(code, message):
    return {'error': {'code': code, 'message': message}}

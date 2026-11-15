"""Tools the assistant model may call (RFC 0004). Each one runs the same use case as an HTTP route."""
import json

import h3

from backend.application.api import calculate_calendar, parse_request
from backend.domain.calculations.map_features import map_result
from backend.domain.models.error import CalendarError
from backend.domain.models.map_query import MapQuery

MAX_MONTHS_SENT = 36
TOP_MONTHS = 12
TOP_HEXAGONS = 10
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
                       'periods), yearly ranking, seasonality and indicators. Period defaults to the whole series.',
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
            'hours': {'type': 'integer', 'enum': [24, 72, 168], 'description': 'Time window up to now'}}}}},
]


def pick(row, fields):
    return {field: row.get(field) for field in fields}


def calendar_summary(body):
    months = body['months']
    summary = {'area': body['area'], 'coverage': body['coverage'], 'indicators': body['indicators'],
               # A rank inside a one-year period is always 1 and reads as 'record year', so it goes only with more years.
               'years': [pick(year, YEAR_FIELDS if len(body['years']) > 1 else ONE_YEAR_FIELDS)
                         for year in body['years']],
               'seasonality': [pick(month, ('month_of_year', 'median')) for month in body['seasonality']]}
    if len(months) <= MAX_MONTHS_SENT:
        summary['months'] = [pick(month, MONTH_FIELDS) for month in months]
    else:
        busiest = sorted(months, key=lambda month: month['detections'] or 0, reverse=True)
        summary['top_months'] = [pick(month, MONTH_FIELDS) for month in busiest[:TOP_MONTHS]]
    return summary


class Toolbox:
    """Runs tools inside one read transaction; returns (result for the model, actions, notes)."""

    def __init__(self, reader, now, rules, risk_rules):
        self.reader, self.now, self.rules, self.risk_rules = reader, now, rules, risk_rules
        self.handlers = {'list_regions': self.list_regions, 'get_calendar': self.get_calendar,
                         'get_recent': self.get_recent, 'get_fire_map': self.get_fire_map}

    def run(self, name, arguments):
        handler = self.handlers.get(name)
        if handler is None:
            return failure('unknown_tool', f'No tool named {name}.')
        try:
            parsed = json.loads(arguments or '{}')
            if not isinstance(parsed, dict):
                raise TypeError
            return handler(**parsed)
        except CalendarError as error:  # a ValueError too, so it must come first
            return failure(error.code, str(error))
        except (TypeError, ValueError):
            return failure('invalid_arguments', 'Arguments do not match the tool parameters.')

    def context(self):
        return (f'Today is {self.now.date().isoformat()} (UTC). Data covers 2003-01 to '
                f"{self.reader.meta()['last_month']}; resolve relative dates like 'last year' from today.")

    def list_regions(self):
        return [pick(region, ('region_id', 'name')) for region in self.reader.regions()], [], []

    def calendar(self, region_id, start=None, end=None):
        request = {'area': {'type': 'region', 'region_id': region_id},
                   **{key: value for key, value in (('start', start), ('end', end)) if value is not None}}
        area, first, last = parse_request(request)
        _, body = calculate_calendar(self.reader, area, first, last, self.now.date(), self.rules)
        return request, body

    def get_calendar(self, region_id, start=None, end=None):
        request, body = self.calendar(region_id, start, end)
        return calendar_summary(body), [{'type': 'show_calendar', **request},
                                        {'type': 'download_export', **request}], []

    def get_recent(self, region_id):
        request, body = self.calendar(region_id)
        result = {'area': body['area'], 'coverage': body['coverage'], 'recent': body.get('recent')}
        return result, [{'type': 'show_calendar', **request}], []

    def get_fire_map(self, hours=24):
        boxes = [region['bbox'] for region in self.reader.regions()]
        bbox = ','.join(str(value) for value in (min(b[0] for b in boxes), min(b[1] for b in boxes),
                                                 max(b[2] for b in boxes), max(b[3] for b in boxes)))
        query = MapQuery.parse(bbox, str(hours), MAP_ZOOM, 'hexagons')
        body = map_result(query, self.reader.map_rows(query, self.now), self.reader.meta()['updated_at'],
                          self.rules, self.risk_rules)
        hexagons = sorted(body['features'], key=lambda feature: feature['properties']['detections'], reverse=True)
        alerts = body.get('alerts') or {}
        risk = alerts.get('risk')
        result = {'hours': body['hours'], 'total_detections': body['total_detections'],
                  'top_hexagons': [hexagon_summary(feature['properties']) for feature in hexagons[:TOP_HEXAGONS]],
                  'look_first': [look_first_summary(cell) for cell in alerts.get('priority', [])[:TOP_HEXAGONS]],
                  'risk_tiers': risk['tiers'] if risk else None}
        return result, [], [RISK_NOTE] if risk else []


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
    return {'error': {'code': code, 'message': message}}, [], []

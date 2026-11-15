from backend.application.calendar import CalendarService
from backend.domain.calculations.recent import recent_result
from backend.domain.models.area import Area
from backend.domain.models.error import CalendarError
from backend.domain.models.month import Month


def parse_request(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('area'), dict):
        raise CalendarError('invalid_geometry', 'An area selection is required.')
    try:
        area = Area(**payload['area'])
    except TypeError:
        raise CalendarError('invalid_geometry', 'Invalid area selection.') from None
    for field in ('start', 'end'):
        if field in payload:
            Month.parse(payload[field])
    return area, payload.get('start'), payload.get('end')


def calculate_calendar(reader, area, start, end, today, rules):
    snapshot = reader.history(area)
    result = CalendarService(None, clock=lambda: today).calculate_snapshot(snapshot, start, end)
    if result['coverage']['status'] != 'none':
        result['recent'] = recent_result(**reader.recent(snapshot), rules=rules)
        result['indicators']['last_7_days_vs_typical_pct'] = result['recent']['last_7_days']['difference_pct']
    return snapshot, result

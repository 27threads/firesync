"""Check only the historical section; a full HTTP contract belongs to part 6."""
import json
from pathlib import Path

from tests.unit.services.test_calendar import fixture, run


def test_historical_fields_match_documented_example():
    example = json.loads((Path(__file__).resolve().parents[4] / 'docs' / 'api-exemplo.json').read_text())
    result = run(fixture(), '2020-01', '2020-12')
    for key in ('meta','area','coverage'):
        assert set(result[key]) == set(example[key])
    for key in ('months','years','seasonality'):
        assert set(result[key][0]) == set(example[key][0])
    assert set(result['indicators']) == set(example['indicators']) - {'last_7_days_vs_typical_pct'}
    json.dumps(result, allow_nan=False)

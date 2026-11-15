"""Audit, finding 6: the satellite switch dates live in one place and every copy follows it."""
import ast
from datetime import date, timedelta
from pathlib import Path

from backend.adapters.outbound.postgres.api import coverage_intervals, satellite_sql
from backend.domain.models.month import SATELLITE_SWITCHES, Month, satellite_on
from backend.domain.models.snapshot import HistorySnapshot


def test_month_and_day_follow_the_same_switches():
    assert [satellite_on(d) for d in (date(2012, 1, 31), date(2012, 2, 1), date(2026, 10, 31), date(2026, 11, 1))] == \
        ['Aqua', 'SNPP', 'SNPP', 'N20']
    assert Month(2012, 1).satellite == 'Aqua' and Month(2012, 2).satellite == 'SNPP'
    assert Month(2026, 10).satellite == 'SNPP' and Month(2026, 11).satellite == 'N20'


def test_sql_case_is_built_from_the_switches():
    sql = satellite_sql('datahora_utc', 'timestamptz')
    for start, satellite in SATELLITE_SWITCHES:
        assert f"'{start.isoformat()}'::timestamptz" in sql and f"'{satellite}'" in sql
    assert sql.startswith('satelite = CASE') and "'Aqua'" in sql


def test_viirs_coverage_follows_the_switches():
    periods = tuple({'region_id': 1, 'satellite': s, 'start': date(2000, 1, 1), 'end': date(2030, 1, 1)}
                    for s in ('SNPP', 'N20'))
    snapshot = HistorySnapshot({}, {'biomes': [{'region_id': 1}]}, {}, (), (), periods, frozenset(), frozenset(), ())
    assert coverage_intervals(snapshot) == [(SATELLITE_SWITCHES[0][0], date(2030, 1, 1))]   # SNPP + N20, no gap
    only_snpp = HistorySnapshot({}, {'biomes': [{'region_id': 1}]}, {}, (), (), periods[:1], frozenset(), frozenset(), ())
    assert coverage_intervals(only_snpp) == [(SATELLITE_SWITCHES[0][0], SATELLITE_SWITCHES[1][0] - timedelta(days=1))]


def test_pipeline_aggregation_uses_the_same_switches():
    """agregar.py (data-pipeline) keeps its own table; it must match the API's."""
    source = (Path(__file__).resolve().parents[4] / 'data-pipeline' / 'agregar.py').read_text(encoding='utf-8')
    node = next(n for n in ast.parse(source).body
                if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == 'SATELITE_DO_MES')
    table = eval(compile(ast.Expression(node.value), 'agregar.py', 'eval'), {'date': date})
    assert [(start, satellite) for start, _end, satellite in table[1:]] == list(SATELLITE_SWITCHES)
    assert table[0][2] == 'Aqua'

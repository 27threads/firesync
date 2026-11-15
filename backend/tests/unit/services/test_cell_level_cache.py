"""Revisão do PR #86: o nível de cada célula res 4 não depende do recorte do mapa, só dos dados.
Guardado por versão dos dados, arrastar ou dar zoom não volta ao banco nem refaz a conta."""
from datetime import date

from backend.adapters.outbound.postgres.cell_level_cache import CellLevelCache
from backend.domain.calculations.map_features import alerts_block

VERSION = ('2026-11-14T12:00:00Z', 'v1', date(2026, 11, 14))


def counting(calls):
    def compute(cells):
        calls.append(sorted(cells))
        return {cell: {'alert_level': 'attention', 'detections_7d': 10, 'typical_median': 4.0,
                       'share_followed_by_high': 0.1, 'cell_name': cell} for cell in cells}
    return compute


def test_second_viewport_does_not_recompute_the_cells_it_shares_with_the_first():
    cache, calls = CellLevelCache(), []
    cache.levels(VERSION, ['a', 'b'], counting(calls))
    cache.levels(VERSION, ['b', 'c'], counting(calls))
    assert calls == [['a', 'b'], ['c']]


def test_same_viewport_again_never_reaches_the_database():
    cache, calls = CellLevelCache(), []
    first = cache.levels(VERSION, ['a', 'b'], counting(calls))
    again = cache.levels(VERSION, ['b', 'a'], counting(calls))
    assert calls == [['a', 'b']] and again == first


def test_a_cell_has_the_same_level_in_any_viewport():
    cache = CellLevelCache()
    wide = cache.levels(VERSION, ['a', 'b', 'c'], counting([]))
    narrow = cache.levels(VERSION, ['c'], counting([]))
    assert narrow['c'] == wide['c']
    assert set(narrow) == {'c'}


def test_new_data_version_recomputes_everything():
    cache, calls = CellLevelCache(), []
    cache.levels(VERSION, ['a'], counting(calls))
    cache.levels(('2026-11-14T15:00:00Z', 'v1', date(2026, 11, 14)), ['a'], counting(calls))
    cache.levels((VERSION[0], 'v2', VERSION[2]), ['a'], counting(calls))
    assert len(calls) == 3


def test_only_the_latest_versions_are_kept():
    cache, calls = CellLevelCache(versions=2), []
    for hour in (9, 12, 15):
        cache.levels((f'{hour}', 'v1', VERSION[2]), ['a'], counting(calls))
    cache.levels(('9', 'v1', VERSION[2]), ['a'], counting(calls))      # the oldest one was dropped
    assert len(calls) == 4


def test_nothing_to_compute_for_an_empty_viewport():
    assert CellLevelCache().levels(VERSION, [], counting([])) == {}


def test_alerts_block_accepts_levels_already_computed_and_matches_the_daily_path():
    rules = {'version': 't', 'historical_outcome': {'unit': 'h3_res4', 'horizon_days': 14, 'overall_share': 0.04}}
    levels = {'84a8101ffffffff': {'alert_level': 'critical', 'detections_7d': 30, 'typical_median': 5.0,
                                  'share_followed_by_high': 0.27}}
    block, used = alerts_block({'cell_levels': levels, 'cell_daily': None, 'data_through': date(2026, 11, 14),
                                'coverage_start': date(2012, 1, 19)}, rules)
    assert used == levels
    assert [p['alert_level'] for p in block['priority']] == ['critical']
    assert block['data_through'] == '2026-11-14'


def test_alerts_block_without_levels_or_daily_counts_is_off():
    assert alerts_block({'cell_levels': None, 'cell_daily': None}, {'version': 't'}) == (None, {})

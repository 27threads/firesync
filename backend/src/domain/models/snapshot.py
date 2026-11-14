from dataclasses import dataclass
from datetime import date
from typing import Mapping


@dataclass(frozen=True, slots=True)
class HistorySnapshot:
    """Detached rows from a single consistent database read; all names are English."""

    meta: Mapping
    area: Mapping
    coverage: Mapping
    counts: tuple[Mapping, ...]
    factors: tuple[Mapping, ...]
    periods: tuple[Mapping, ...]
    missing: frozenset[tuple[date, str]]
    provisional: frozenset[tuple[int, int, str]]

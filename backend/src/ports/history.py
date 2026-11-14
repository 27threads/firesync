from typing import Protocol

from backend.domain.models.area import Area
from backend.domain.models.snapshot import HistorySnapshot


class HistoryRepository(Protocol):
    def load(self, area: Area) -> HistorySnapshot:
        """Load full history and metadata from one read-only snapshot."""
        ...

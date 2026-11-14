from typing import Protocol

from firesync_backend.domain.models.area import Area
from firesync_backend.domain.models.snapshot import HistorySnapshot


class HistoryRepository(Protocol):
    def load(self, area: Area) -> HistorySnapshot:
        """Load full history and metadata from one read-only snapshot."""
        ...

class FakeHistoryRepository:
    """In-memory snapshot provider; deliberately contains no calculation logic."""

    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.calls = 0

    def load(self, area):
        self.calls += 1
        return self.snapshot

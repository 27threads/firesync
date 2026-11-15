"""Alert level of each resolution 4 cell, kept per data version and not per map viewport (PR #86 review).

The level of a cell depends only on the data, so dragging or zooming the map must not go back to the database
nor redo the calculation for cells already seen. Cells are computed on demand and reused by every viewport."""
from collections import OrderedDict
from threading import Lock


class CellLevelCache:
    def __init__(self, versions=2):
        self.versions, self.entries, self.lock = versions, OrderedDict(), Lock()

    def levels(self, version, cells, compute):
        """{cell: level} for `cells`; `compute(missing_cells)` runs only for the cells this version has not seen."""
        with self.lock:
            store = self.entries.setdefault(version, {})
            self.entries.move_to_end(version)
            while len(self.entries) > self.versions:
                self.entries.popitem(last=False)
            missing = [cell for cell in cells if cell not in store]
        if missing:
            computed = compute(missing)       # outside the lock: it queries the database
            with self.lock:
                store.update(computed)
        with self.lock:
            return {cell: store[cell] for cell in cells}

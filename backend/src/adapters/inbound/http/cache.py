from collections import OrderedDict
from threading import Lock


class ResponseCache:
    def __init__(self, size=128):
        self.size = size
        self.entries = OrderedDict()
        self.lock = Lock()

    def get(self, key):
        with self.lock:
            if key not in self.entries:
                return None
            self.entries.move_to_end(key)
            return self.entries[key]

    def put(self, key, value):
        with self.lock:
            self.entries[key] = value
            self.entries.move_to_end(key)
            while len(self.entries) > self.size:
                self.entries.popitem(last=False)

from collections import OrderedDict, deque
from math import ceil
from threading import Lock


class RateLimiter:
    """Sliding windows per socket IP; proxy headers must be trusted by the server."""

    def __init__(self, limits, seconds, clock):
        if seconds <= 0 or any(value <= 0 for value in limits.values()):
            raise ValueError('Rate limits and window must be positive.')
        self.limits, self.seconds, self.clock = limits, seconds, clock
        self.requests = OrderedDict()
        self.lock = Lock()

    def retry_after(self, ip, endpoint):
        with self.lock:
            now = self.clock()
            # Ordered by last request, so expired identities never accumulate.
            while self.requests and next(iter(self.requests.values()))['last'] <= now - self.seconds:
                self.requests.popitem(last=False)
            buckets = self.requests.setdefault(ip, {'last': now, **{key: deque() for key in self.limits}})
            buckets['last'] = now
            self.requests.move_to_end(ip)
            keys = ['general'] + ([endpoint] if endpoint != 'general' and endpoint in self.limits else [])
            for key in keys:
                while buckets[key] and buckets[key][0] <= now - self.seconds:
                    buckets[key].popleft()
            waits = [ceil(buckets[key][0] + self.seconds - now) for key in keys
                     if len(buckets[key]) >= self.limits[key]]
            if waits:
                return max(1, max(waits))
            for key in keys:
                buckets[key].append(now)
            return 0

"""Small single-instance abuse guard; replace with a shared limiter before scaling."""
import time
import threading
from collections import deque
from backend.app.services.case_state import fail

_buckets = {}
_lock = threading.Lock()

def enforce_limit(key, limit=30, window=3600):
    now = time.monotonic()
    with _lock:
        if len(_buckets) > 10000:
            for stale in [k for k, q in _buckets.items() if not q or q[-1] < now - 3600]:
                _buckets.pop(stale, None)
        queue = _buckets.setdefault(key, deque())
        while queue and queue[0] <= now - window:
            queue.popleft()
        if len(queue) >= limit:
            fail(429, "RATE_LIMITED", "Too many requests. Please wait before trying again.")
        queue.append(now)

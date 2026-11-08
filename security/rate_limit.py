"""Small process-local login throttle. Use Redis/shared storage for multi-worker deployments."""
from collections import defaultdict, deque
from time import time
from threading import Lock

_attempts = defaultdict(deque)
_lock = Lock()
WINDOW_SECONDS = 15 * 60
MAX_ATTEMPTS = 8

def is_limited(key):
    now=time()
    with _lock:
        queue=_attempts[key]
        while queue and now-queue[0] > WINDOW_SECONDS: queue.popleft()
        return len(queue) >= MAX_ATTEMPTS

def record_failure(key):
    with _lock:
        _attempts[key].append(time())

def clear_attempts(key):
    with _lock:
        _attempts.pop(key, None)

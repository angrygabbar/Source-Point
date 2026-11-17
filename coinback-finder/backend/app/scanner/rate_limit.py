import threading
import time


class RateLimiter:
    """Simple per-source spacing limiter; waits are interruptible by the shutdown event."""

    def __init__(self, per_minute: int) -> None:
        self.interval = 60.0 / max(1, per_minute)
        self._next = 0.0
        self._lock = threading.Lock()

    def acquire(self, stop_event: threading.Event) -> bool:
        with self._lock:
            now = time.monotonic()
            wait = max(0.0, self._next - now)
            self._next = max(now, self._next) + self.interval
        if wait and stop_event.wait(wait):
            return False
        return not stop_event.is_set()

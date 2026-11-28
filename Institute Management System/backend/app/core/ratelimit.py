import time
from collections import defaultdict, deque
from functools import lru_cache
from threading import Lock

import redis

from app.core.config import settings
from app.core.errors import RateLimited
from app.core.logging import get_logger

log = get_logger(__name__)
_local: dict[str, deque] = defaultdict(deque)
_lock = Lock()


@lru_cache
def redis_client() -> redis.Redis:
    return redis.Redis.from_url(settings.REDIS_URL, socket_timeout=2, socket_connect_timeout=2)


def hit(key: str, limit: int, window_seconds: int) -> None:
    """Fixed-window limiter backed by Redis, with an in-process fallback when Redis is unreachable."""
    try:
        r = redis_client()
        bucket = f"rl:{key}:{int(time.time() // window_seconds)}"
        count = r.incr(bucket)
        if count == 1:
            r.expire(bucket, window_seconds)
        if count > limit:
            raise RateLimited("Too many attempts. Please wait and try again.")
        return
    except redis.RedisError:
        log.warning("rate limiter falling back to in-process store")
    now = time.time()
    with _lock:
        q = _local[key]
        while q and q[0] < now - window_seconds:
            q.popleft()
        if len(q) >= limit:
            raise RateLimited("Too many attempts. Please wait and try again.")
        q.append(now)

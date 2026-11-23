"""Shared rate limiting. Memory backend (single process / tests) and Redis backend (several workers/servers): fixed-window counters keyed by client + bucket.
If Redis fails, the limiter degrades to the per-process memory backend and counts the error (so an outage does not lock everyone out, and does not go unnoticed)."""
import os, time
from . import obs

class MemoryBackend:
    def __init__(self, clock=time.time): self.d = {}; self.clock = clock
    def incr(self, key, window):
        now = self.clock(); w = int(now // window); k = (key, w); self.d[k] = self.d.get(k, 0) + 1
        if len(self.d) > 50000: self.d = {kk: v for kk, v in self.d.items() if kk[1] >= w}
        return self.d[k]

class RedisBackend:
    def __init__(self, client, clock=time.time): self.r = client; self.clock = clock
    def incr(self, key, window):
        k = f"rl:{key}:{int(self.clock() // window)}"; p = self.r.pipeline(); p.incr(k); p.expire(k, window * 2); n, _ = p.execute(); return int(n)

class Limiter:
    def __init__(self, backend, fallback=None): self.backend = backend; self.fallback = fallback or MemoryBackend()
    def hit(self, key, limit, window=60):
        try: n = self.backend.incr(key, window)
        except Exception: obs.inc("ratelimit_backend_error"); n = self.fallback.incr(key, window)
        return n <= limit, max(0, limit - n)

def make_limiter():
    url = os.getenv("REDIS_URL")
    if url:
        import redis                      # optional dependency: pip install redis
        return Limiter(RedisBackend(redis.Redis.from_url(url, socket_timeout=0.5)))
    return Limiter(MemoryBackend())

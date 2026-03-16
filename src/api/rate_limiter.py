"""
Rate Limiter for FinClaw REST API.
Token-bucket style rate limiting per client.
"""

from __future__ import annotations

import time
import threading
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class RateLimiter:
    """Per-client rate limiter using token bucket algorithm."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def check(self, client_id: str) -> bool:
        """Check if client can make a request. Returns True if allowed."""
        with self._lock:
            now = time.time()
            bucket = self._buckets.get(client_id)
            if bucket is None:
                bucket = _Bucket(tokens=self.max_requests, last_refill=now)
                self._buckets[client_id] = bucket

            # Refill tokens
            elapsed = now - bucket.last_refill
            refill = elapsed * (self.max_requests / self.window_seconds)
            bucket.tokens = min(self.max_requests, bucket.tokens + refill)
            bucket.last_refill = now

            if bucket.tokens >= 1:
                bucket.tokens -= 1
                return True
            return False

    def remaining(self, client_id: str) -> int:
        """Get remaining requests for a client."""
        with self._lock:
            bucket = self._buckets.get(client_id)
            if bucket is None:
                return self.max_requests
            now = time.time()
            elapsed = now - bucket.last_refill
            refill = elapsed * (self.max_requests / self.window_seconds)
            return int(min(self.max_requests, bucket.tokens + refill))

    def reset(self, client_id: str | None = None) -> None:
        """Reset rate limit for a client or all clients."""
        with self._lock:
            if client_id:
                self._buckets.pop(client_id, None)
            else:
                self._buckets.clear()

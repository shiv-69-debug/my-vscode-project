"""Rate limiting middleware for Flask using a sliding-window in-memory store."""

import time
from collections import defaultdict
from functools import wraps

from flask import request, jsonify


def parse_rate_limit(limit_str: str) -> tuple:
    """Parse a rate-limit string like '100 per minute' into (max_requests, window_seconds)."""
    parts = limit_str.strip().split()
    if len(parts) >= 3:
        max_requests = int(parts[0])
        unit = parts[2].lower()
    else:
        max_requests = 100
        unit = "minute"

    multipliers = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
    window = multipliers.get(unit, 60)
    return max_requests, window


class RateLimiter:
    """Simple sliding-window rate limiter keyed by client IP."""

    def __init__(self, limit_str: str = "100 per minute") -> None:
        self.max_requests, self.window = parse_rate_limit(limit_str)
        self._store: dict[str, list] = defaultdict(list)

    def _clean(self, key: str) -> None:
        now = time.time()
        cutoff = now - self.window
        self._store[key] = [t for t in self._store[key] if t > cutoff]

    def is_allowed(self, key: str) -> bool:
        self._clean(key)
        return len(self._store[key]) < self.max_requests

    def hit(self, key: str) -> None:
        self._store[key].append(time.time())

    def middleware(self):
        """Decorator for Flask routes to apply rate limiting."""
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                client_ip = request.remote_addr or "127.0.0.1"
                if not self.is_allowed(client_ip):
                    return jsonify({
                        "error": "Rate limit exceeded. Try again later.",
                        "retry_after_seconds": self.window,
                    }), 429
                self.hit(client_ip)
                return fn(*args, **kwargs)
            return wrapper
        return decorator

"""Per-user rate limiting and quotas.

The default implementation is process-local. Multi-worker production
deployments must replace it with a shared store (Redis, etc.) or accept
that limits are not enforced across processes.

Limits are intentionally conservative. Generation requests are more
expensive than status checks.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from threading import RLock

from app.models.exception import HttpException
from app.security.jwt_auth import AuthenticatedUser


@dataclass
class RateLimitConfig:
    requests_per_minute: int = 60
    generations_per_hour: int = 10
    concurrent_tasks: int = 2
    max_upload_bytes: int = 10 * 1024 * 1024


class InMemoryRateLimiter:
    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or RateLimitConfig()
        self._request_windows: dict[str, list[float]] = defaultdict(list)
        self._generation_windows: dict[str, list[float]] = defaultdict(list)
        self._lock = RLock()

    def check_request(self, user: AuthenticatedUser, request_id: str) -> None:
        self._enforce(user.sub, self._request_windows, 60.0, self.config.requests_per_minute, request_id)

    def check_generation(self, user: AuthenticatedUser, request_id: str) -> None:
        self._enforce(
            user.sub,
            self._generation_windows,
            3600.0,
            self.config.generations_per_hour,
            request_id,
        )

    def _enforce(
        self,
        key: str,
        windows: dict[str, list[float]],
        window_seconds: float,
        limit: int,
        request_id: str,
    ) -> None:
        now = time.monotonic()
        with self._lock:
            timestamps = windows[key]
            timestamps[:] = [t for t in timestamps if now - t < window_seconds]
            if len(timestamps) >= limit:
                raise HttpException(
                    task_id=request_id,
                    status_code=429,
                    message="rate limit exceeded",
                )
            timestamps.append(now)


rate_limiter = InMemoryRateLimiter()

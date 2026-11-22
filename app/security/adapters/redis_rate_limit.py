"""Redis-backed distributed rate limiter.

Atomic INCR + EXPIRE. Requires REDIS_URL. Does not fall back to process-local
counters when Redis is unavailable.
"""

from __future__ import annotations

import os
from app.models.exception import HttpException
from app.security.jwt_auth import AuthenticatedUser
from app.security.rate_limit import RateLimitConfig


class RedisRateLimiter:
    def __init__(self, url: str | None = None, config: RateLimitConfig | None = None) -> None:
        self.url = url or os.getenv("REDIS_URL")
        self.config = config or RateLimitConfig()
        if not self.url:
            raise RuntimeError("REDIS_URL is required for RedisRateLimiter")
        try:
            import redis
            self._redis = redis.StrictRedis.from_url(self.url, decode_responses=True)
        except ImportError as exc:
            raise RuntimeError("redis package is required for the Redis rate limiter") from exc

    def check_request(self, user: AuthenticatedUser, request_id: str) -> None:
        self._incr(f"rl:req:{user.sub}", 60, self.config.requests_per_minute, request_id)

    def check_generation(self, user: AuthenticatedUser, request_id: str) -> None:
        self._incr(f"rl:gen:{user.sub}", 3600, self.config.generations_per_hour, request_id)

    def _incr(self, key: str, ttl: int, limit: int, request_id: str) -> None:
        try:
            pipe = self._redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl, nx=True)
            count, _ = pipe.execute()
        except Exception as exc:
            raise HttpException(
                task_id=request_id,
                status_code=503,
                message="rate limiting service unavailable",
            ) from exc
        if int(count) > limit:
            raise HttpException(
                task_id=request_id,
                status_code=429,
                message="rate limit exceeded",
            )

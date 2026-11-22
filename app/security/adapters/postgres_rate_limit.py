"""PostgreSQL-backed distributed rate limiter.

Atomic counter updates via INSERT ... ON CONFLICT DO UPDATE RETURNING.
No Redis. No process-local fallback. Requires DATABASE_URL.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from app.models.exception import HttpException
from app.security.jwt_auth import AuthenticatedUser
from app.security.rate_limit import RateLimitConfig


class PostgresRateLimiter:
    def __init__(self, dsn: str | None = None, config: RateLimitConfig | None = None) -> None:
        self.dsn = dsn or os.getenv("DATABASE_URL")
        self.config = config or RateLimitConfig()
        if not self.dsn:
            raise RuntimeError("DATABASE_URL is required for PostgresRateLimiter")
        try:
            import psycopg2
            self._driver = psycopg2
        except ImportError as exc:
            raise RuntimeError("psycopg2 is required") from exc

    def _conn(self):
        return self._driver.connect(self.dsn)

    def check_request(self, user: AuthenticatedUser, request_id: str) -> None:
        self._incr(f"req:{user.sub}", 60, self.config.requests_per_minute, request_id)

    def check_generation(self, user: AuthenticatedUser, request_id: str) -> None:
        self._incr(f"gen:{user.sub}", 3600, self.config.generations_per_hour, request_id)

    def _incr(self, key: str, window_seconds: int, limit: int, request_id: str) -> None:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=window_seconds)
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO rate_limit_counters (key, count, window_start, expires_at)
                        VALUES (%s, 1, %s, %s)
                        ON CONFLICT (key) DO UPDATE
                        SET count = CASE
                            WHEN rate_limit_counters.expires_at < NOW() THEN 1
                            ELSE rate_limit_counters.count + 1
                        END,
                        window_start = CASE
                            WHEN rate_limit_counters.expires_at < NOW() THEN EXCLUDED.window_start
                            ELSE rate_limit_counters.window_start
                        END,
                        expires_at = CASE
                            WHEN rate_limit_counters.expires_at < NOW() THEN EXCLUDED.expires_at
                            ELSE rate_limit_counters.expires_at
                        END
                        RETURNING count
                        """,
                        (key, now, expires),
                    )
                    count = cur.fetchone()[0]
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

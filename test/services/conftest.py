"""Shared service-test isolation for process-local security state."""

import pytest


@pytest.fixture(autouse=True)
def reset_in_memory_rate_limits():
    """Keep rate-limit state isolated between tests without disabling enforcement."""
    from app.security.rate_limit import InMemoryRateLimiter, rate_limiter

    if not isinstance(rate_limiter, InMemoryRateLimiter):
        yield
        return

    def clear_windows():
        with rate_limiter._lock:
            rate_limiter._request_windows.clear()
            rate_limiter._generation_windows.clear()

    clear_windows()
    try:
        yield
    finally:
        clear_windows()

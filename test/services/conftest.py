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


@pytest.fixture(autouse=True)
def prepare_direct_memory_workers(request, monkeypatch):
    """Model API task creation for service-level direct worker tests only.

    Route/CLI integration tests are excluded and must prove their own task
    creation. This adapter supplies the required precondition for direct calls
    to task.start() on the process-local test backend; production behavior and
    generation fencing remain unchanged.
    """
    integration_modules = {
        "test_controller_video.py", "test_cli.py", "test_webui_task.py",
        "test_redis_delete_ownership.py", "test_redis_short_form_requests.py",
        "test_concurrent_task_delete.py",
        "test_phase1_security.py", "test_task_manager.py",
    }
    if request.node.path.name in integration_modules:
        yield
        return

    from functools import wraps
    from app.services import task
    from app.services.state import MemoryState

    original_start = task.start

    @wraps(original_start)
    def start_after_task_creation(task_id, *args, **kwargs):
        state = task.sm.state
        if isinstance(state, MemoryState) and state.get_task(task_id) is None:
            state.create_task(task_id)
        return original_start(task_id, *args, **kwargs)

    monkeypatch.setattr(task, "start", start_after_task_creation)

    original_get_video_materials = task.get_video_materials

    @wraps(original_get_video_materials)
    def get_materials_in_worker_scope(task_id, *args, **kwargs):
        state = task.sm.state
        if (
            isinstance(state, MemoryState)
            and task.current_generation.get() is None
        ):
            if state.get_task(task_id) is None:
                state.create_task(task_id)
            generation = state.acquire_generation(task_id)
            token = task.current_generation.set(generation)
            try:
                return original_get_video_materials(task_id, *args, **kwargs)
            finally:
                task.current_generation.reset(token)
        return original_get_video_materials(task_id, *args, **kwargs)

    monkeypatch.setattr(task, "get_video_materials", get_materials_in_worker_scope)
    yield

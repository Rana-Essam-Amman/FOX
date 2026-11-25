"""Tests that generation ContextVar is bound at start and propagated safely."""

import contextvars
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.services.state import current_generation


def test_contextvar_not_shared_across_threads_by_default():
    """A ContextVar set in the parent must not leak into a raw thread pool worker."""
    token = current_generation.set(42)
    try:
        def worker():
            return current_generation.get()
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(worker)
            assert future.result() is None  # not inherited by default
    finally:
        current_generation.reset(token)


def test_copy_context_propagates_generation():
    token = current_generation.set(7)
    try:
        ctx = contextvars.copy_context()
        def worker():
            return current_generation.get()
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(ctx.run, worker)
            assert future.result() == 7
    finally:
        current_generation.reset(token)


def test_independent_contexts_do_not_interfere():
    results = []
    def run_with_gen(gen):
        token = current_generation.set(gen)
        try:
            # Simulate concurrent workers each seeing their own value
            return current_generation.get()
        finally:
            current_generation.reset(token)

    with ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(run_with_gen, 1)
        f2 = ex.submit(run_with_gen, 2)
        results.append(f1.result())
        results.append(f2.result())
    assert sorted(results) == [1, 2]

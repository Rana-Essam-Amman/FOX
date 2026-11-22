"""Runtime adapter selection.

Production uses durable PostgreSQL and Supabase Storage.
Development and tests use in-memory adapters.
Fails closed if production configuration is incomplete.
"""

from __future__ import annotations

import os

from app.security.config_validation import is_production, validate_production_config


def create_ownership_store():
    from app.security.ownership import TaskOwnershipStore
    if is_production():
        validate_production_config()
        from app.security.adapters.postgres_ownership import PostgresOwnershipStore
        return PostgresOwnershipStore()
    from app.security.ownership import InMemoryOwnershipStore
    return InMemoryOwnershipStore()


def create_rate_limiter():
    if is_production():
        validate_production_config()
        from app.security.adapters.postgres_rate_limit import PostgresRateLimiter
        return PostgresRateLimiter()
    from app.security.rate_limit import InMemoryRateLimiter
    return InMemoryRateLimiter()


def create_storage():
    if is_production():
        validate_production_config()
        from app.security.adapters.supabase_storage import SupabaseStorageAdapter
        return SupabaseStorageAdapter()
    from app.security.adapters.storage import LocalFilesystemStorage
    return LocalFilesystemStorage()

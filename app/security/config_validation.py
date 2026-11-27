"""Production configuration validation.

Fails closed if required infrastructure is missing when FOX_ENV=production.
Development adapters are never activated automatically in production.
"""

from __future__ import annotations

import os


class ProductionConfigError(RuntimeError):
    pass


def is_production() -> bool:
    return os.getenv("FOX_ENV", "").lower() == "production"


def validate_production_config() -> None:
    if not is_production():
        return

    missing = []
    if not os.getenv("FOX_OIDC_ISSUER"):
        missing.append("FOX_OIDC_ISSUER")
    if not os.getenv("FOX_OIDC_AUDIENCE"):
        missing.append("FOX_OIDC_AUDIENCE")
    if not os.getenv("FOX_OIDC_JWKS_URL"):
        missing.append("FOX_OIDC_JWKS_URL")
    if not os.getenv("DATABASE_URL"):
        missing.append("DATABASE_URL")
    # Production workers need shared Redis task state and generation fencing.
    # PostgreSQL remains the ownership and rate-limit persistence layer.
    from app.config import config
    if config.app.get("enable_redis") is not True:
        missing.append("app.enable_redis=true (shared Redis task state and worker fencing)")
    # Supabase Storage credentials are required for production media.
    if not os.getenv("SUPABASE_URL"):
        missing.append("SUPABASE_URL")
    if not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        missing.append("SUPABASE_SERVICE_ROLE_KEY")

    if missing:
        raise ProductionConfigError(
            f"Production startup refused. Missing required configuration: {', '.join(missing)}"
        )

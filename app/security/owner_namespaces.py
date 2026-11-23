"""Owner namespaces and execution policies for private material ownership.

Authenticated users own their materials under their JWT subject. Trusted
in-process entry points (WebUI, CLI) use fixed internal namespaces. The
internal prefix is reserved: no authenticated user may be bound to it, so a
token cannot claim an internal owner.
"""

from __future__ import annotations

INTERNAL_PREFIX = "internal:"
WEBUI_OWNER = "internal:webui"
CLI_OWNER = "internal:cli"

POLICY_USER = "user"
POLICY_WEBUI = "webui"
POLICY_CLI = "cli"
KNOWN_POLICIES = frozenset({POLICY_USER, POLICY_WEBUI, POLICY_CLI})

_INTERNAL_OWNER_FOR_POLICY = {POLICY_WEBUI: WEBUI_OWNER, POLICY_CLI: CLI_OWNER}


class OwnerNamespaceError(ValueError):
    """An owner identifier is empty, malformed or uses a reserved namespace."""


def user_owner_id(subject: object) -> str:
    """Return the owner ID for an authenticated subject, or raise."""
    if not isinstance(subject, str) or not subject.strip():
        raise OwnerNamespaceError("authenticated subject is missing")
    if subject.startswith(INTERNAL_PREFIX):
        raise OwnerNamespaceError("authenticated subject uses a reserved namespace")
    return subject


def internal_owner_for_policy(policy: str) -> str | None:
    """Return the fixed internal owner for a trusted policy, or None for users."""
    return _INTERNAL_OWNER_FOR_POLICY.get(policy)


def is_reserved_owner(owner_id: str) -> bool:
    return owner_id.startswith(INTERNAL_PREFIX)

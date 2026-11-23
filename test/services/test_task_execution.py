"""Worker-side task grant rules, exercised against the real ownership store."""

from datetime import datetime, timezone

import pytest

from app.security.owner_namespaces import (
    CLI_OWNER,
    OwnerNamespaceError,
    POLICY_CLI,
    POLICY_USER,
    POLICY_WEBUI,
    WEBUI_OWNER,
    internal_owner_for_policy,
    user_owner_id,
)
from app.security.ownership import InMemoryOwnershipStore, TaskOwnershipRecord
from app.security.task_execution import ExecutionDenied, authorize_task_execution

TASK = "task-1"


def _store_with(owner_id, policy=POLICY_USER, kind="video", task_id=TASK, metadata=None):
    store = InMemoryOwnershipStore()
    meta = {"policy": policy} if metadata is None else metadata
    store.create(TaskOwnershipRecord(
        task_id=task_id, owner_id=owner_id,
        created_at=datetime.now(timezone.utc), kind=kind, metadata=meta,
    ))
    return store


def _grant(store, task_id=TASK, kind="video"):
    return authorize_task_execution(task_id, expected_kind=kind, lookup=store.get)


def test_user_task_grants_its_owner():
    grant = _grant(_store_with("user-a"))
    assert (grant.owner_id, grant.policy) == ("user-a", POLICY_USER)


def test_webui_task_grants_fixed_webui_namespace():
    grant = _grant(_store_with(WEBUI_OWNER, policy=POLICY_WEBUI))
    assert (grant.owner_id, grant.policy) == (WEBUI_OWNER, POLICY_WEBUI)


def test_cli_task_grants_fixed_cli_namespace():
    grant = _grant(_store_with(CLI_OWNER, policy=POLICY_CLI))
    assert (grant.owner_id, grant.policy) == (CLI_OWNER, POLICY_CLI)


def test_missing_ownership_record_is_denied():
    with pytest.raises(ExecutionDenied, match="missing"):
        _grant(InMemoryOwnershipStore())


def test_record_for_a_different_task_is_denied():
    store = _store_with("user-a", task_id="other-task")
    with pytest.raises(ExecutionDenied):
        authorize_task_execution(TASK, expected_kind="video", lookup=lambda _: store.get("other-task"))


def test_kind_mismatch_is_denied():
    with pytest.raises(ExecutionDenied, match="kind"):
        _grant(_store_with("user-a", kind="audio"), kind="video")


def test_record_without_policy_is_denied_as_legacy():
    """Records created before policies existed must fail closed, not default to user."""
    with pytest.raises(ExecutionDenied, match="policy"):
        _grant(_store_with("user-a", metadata={"request_id": "r"}))


@pytest.mark.parametrize("policy", ["admin", "", None, "skip_ownership_check"])
def test_unknown_policy_is_denied(policy):
    with pytest.raises(ExecutionDenied, match="policy"):
        _grant(_store_with("user-a", metadata={"policy": policy}))


def test_user_task_cannot_run_under_internal_namespace():
    with pytest.raises(ExecutionDenied, match="reserved"):
        _grant(_store_with(WEBUI_OWNER, policy=POLICY_USER))


def test_internal_task_cannot_be_reassigned_to_a_user():
    with pytest.raises(ExecutionDenied, match="policy"):
        _grant(_store_with("user-a", policy=POLICY_WEBUI))


def test_cli_policy_cannot_claim_webui_namespace():
    with pytest.raises(ExecutionDenied, match="policy"):
        _grant(_store_with(WEBUI_OWNER, policy=POLICY_CLI))


def test_empty_owner_is_denied():
    with pytest.raises(ExecutionDenied, match="owner"):
        _grant(_store_with(""))


def test_malformed_task_identifier_is_denied_before_lookup():
    def lookup(_):
        raise AssertionError("lookup must not run for a malformed task ID")

    for bad in (None, "", 7):
        with pytest.raises(ExecutionDenied):
            authorize_task_execution(bad, expected_kind="video", lookup=lookup)


def test_unavailable_ownership_store_is_not_swallowed():
    def broken_lookup(_):
        raise ConnectionError("ownership store down")

    with pytest.raises(ConnectionError):
        authorize_task_execution(TASK, expected_kind="video", lookup=broken_lookup)


def test_owner_comes_from_record_not_from_metadata():
    store = _store_with("user-a", metadata={"policy": POLICY_USER, "owner_id": "user-b"})
    assert _grant(store).owner_id == "user-a"


@pytest.mark.parametrize("subject", ["user-a", "a", "sub|123"])
def test_user_owner_id_accepts_ordinary_subjects(subject):
    assert user_owner_id(subject) == subject


@pytest.mark.parametrize("subject", ["", "   ", None, "internal:webui", "internal:anything"])
def test_user_owner_id_rejects_missing_and_reserved_subjects(subject):
    with pytest.raises(OwnerNamespaceError):
        user_owner_id(subject)


def test_internal_owner_for_policy_is_fixed():
    assert internal_owner_for_policy(POLICY_WEBUI) == WEBUI_OWNER
    assert internal_owner_for_policy(POLICY_CLI) == CLI_OWNER
    assert internal_owner_for_policy(POLICY_USER) is None

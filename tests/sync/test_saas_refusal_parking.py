"""WP07/T034 lease-bound generic SaaS and hosted-tracker operations."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from kernel.clock import UTC, datetime, now_utc, now_utc_iso, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

from specify_cli.saas_client import client as generic_module
from specify_cli.saas_client.client import SaasClient
from specify_cli.saas_client.errors import SaasClientError
from specify_cli.sync import transport_attempts as attempts_module
from specify_cli.sync.consent import record_project_opt_in
from specify_cli.sync.project_store import ProjectStoreError, ProjectSyncStore
from specify_cli.sync.transport_attempts import (
    DeliveryAttemptSpec,
    DeliveryAttemptState,
    DeliveryOutcome,
    DeliveryTerminalResultStatus,
    LogicalOperationDisposition,
    LogicalOperationRepeatability,
    LogicalOperationRequest,
    allocate_logical_delivery_operation,
    attach_remote_operation_id,
    execute_remote_operation_query,
    get_delivery_terminal_result_projection,
    mark_delivery_result_unknown,
    mark_transport_started,
    prepare_delivery_attempt,
    read_remote_operation_id,
    record_delivery_result,
    settle_attempts_for_opt_out_under_lease,
)
from specify_cli.sync.transport_lease import TransportLeaseContext, acquire_project_transport_lease
from specify_cli.tracker import saas_client as tracker_module
from specify_cli.tracker.saas_client import SaaSTrackerClient, SaaSTrackerClientError

pytestmark = pytest.mark.fast

@pytest.fixture(autouse=True)
def _canonical_home(canonical_home: None) -> None:
    """R1a #3121: route this module's home through the ONE canonical owner."""
    del canonical_home


_REAL_GENERIC_AUTHORITY = generic_module._authenticated_authority_for_token
_REAL_TRACKER_AUTHORITY = tracker_module._hosted_authority_for_token


@pytest.fixture(autouse=True)
def _token_matched_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.saas_client.client._authenticated_authority_for_token",
        lambda _token: ("account-t034", "team-t034", "team-t034"),
    )
    monkeypatch.setattr(
        tracker_module,
        "_hosted_authority_for_token",
        lambda _token: tracker_module._HostedTrackerAuthority(
            account_identity="account-t034",
            private_teamspace_id="team-t034",
            collaborative_team_slug="team-t034",
        ),
    )


def _write_project(root: Path, project_uuid: str) -> None:
    config = root / ".kittify" / "config.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        "\n".join(
            (
                "project:",
                f"  uuid: {project_uuid}",
                "  slug: t034-project",
                "  node_id: node-t034",
                "  repo_slug: tests/t034-project",
                f"  build_id: {project_uuid}",
                "sync:",
                "  enabled: true",
            )
        )
        + "\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize("collaborative_ids", [(), ("collab-a", "collab-b")])
def test_token_authority_rejects_absent_or_ambiguous_collaborative_teamspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    collaborative_ids: tuple[str, ...],
) -> None:
    teams = [SimpleNamespace(id="private", is_private_teamspace=True)]
    teams.extend(SimpleNamespace(id=team_id, is_private_teamspace=False) for team_id in collaborative_ids)
    session = SimpleNamespace(
        access_token="token",
        user_id="account",
        default_team_id="private",
        teams=teams,
    )
    manager = SimpleNamespace(get_current_session=lambda: session)
    monkeypatch.setattr(generic_module, "get_token_manager", lambda: manager)
    monkeypatch.setattr(tracker_module, "get_token_manager", lambda: manager)
    monkeypatch.setattr(
        generic_module,
        "_authenticated_authority_for_token",
        _REAL_GENERIC_AUTHORITY,
    )
    monkeypatch.setattr(
        tracker_module,
        "_hosted_authority_for_token",
        _REAL_TRACKER_AUTHORITY,
    )

    assert _REAL_GENERIC_AUTHORITY("token") is None
    assert _REAL_TRACKER_AUTHORITY("token") is None
    root, store = _seed_project(
        tmp_path,
        monkeypatch,
        "5b5b5b5b-5b5b-4b5b-8b5b-5b5b5b5b5b5b",
    )

    class _TripwireHttp:
        """Any send during an authority refusal fails the test."""

        calls: list[tuple[str, str]] = []

        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def get(self, url: str, *, timeout: float | None = None) -> None:
            _TripwireHttp.calls.append(("GET", url))
            raise AssertionError(f"transport reached during authority refusal: {url}")

        def post(self, url: str, **kwargs: object) -> None:
            del kwargs
            _TripwireHttp.calls.append(("POST", url))
            raise AssertionError(f"transport reached during authority refusal: {url}")

        def request(self, method: str, url: str, **kwargs: object) -> None:
            del kwargs
            _TripwireHttp.calls.append((method, url))
            raise AssertionError(f"transport reached during authority refusal: {url}")

    generic = SaasClient(
        "https://app.spec-kitty.ai",
        "token",
        project_root=root,
        _http=_TripwireHttp(),
    )
    with pytest.raises(SaasClientError, match="Collaborative Teamspace"):
        generic.get_team_integrations("collab-a")
    tracker = SaaSTrackerClient(project_root=root)
    monkeypatch.setattr(tracker_module, "_fetch_access_token_sync", lambda: "token")
    monkeypatch.setattr(tracker_module, "httpx", SimpleNamespace(Client=_TripwireHttp))
    with pytest.raises(SaaSTrackerClientError, match="Collaborative Teamspace"):
        tracker.status("github", "project")
    assert _TripwireHttp.calls == []
    assert _attempt_rows(store) == []


def test_private_default_never_replaces_unique_collaborative_teamspace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = SimpleNamespace(
        access_token="token",
        user_id="account",
        default_team_id="private",
        teams=[
            SimpleNamespace(id="private", is_private_teamspace=True),
            SimpleNamespace(id="collaborative", is_private_teamspace=False),
        ],
    )
    manager = SimpleNamespace(get_current_session=lambda: session)
    monkeypatch.setattr(generic_module, "get_token_manager", lambda: manager)
    monkeypatch.setattr(tracker_module, "get_token_manager", lambda: manager)

    assert _REAL_GENERIC_AUTHORITY("token") == (
        "account",
        "private",
        "collaborative",
    )
    assert _REAL_TRACKER_AUTHORITY("token") == (
        tracker_module._HostedTrackerAuthority(
            account_identity="account",
            private_teamspace_id="private",
            collaborative_team_slug="collaborative",
        )
    )


def test_generic_caller_cannot_mint_authenticated_authority() -> None:
    with pytest.raises(TypeError, match="authenticated_account_identity"):
        SaasClient(
            "https://app.spec-kitty.ai",
            "token",
            authenticated_account_identity="forged",  # type: ignore[call-arg]
        )


def _seed_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    project_uuid: str,
    *,
    admitted: bool = True,
) -> tuple[Path, ProjectSyncStore]:
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    root = tmp_path / "checkout"
    root.mkdir()
    _write_project(root, project_uuid)
    record_project_opt_in(project_uuid, actor="t034-test")
    store = ProjectSyncStore(project_uuid)
    if admitted:
        with store.unit_of_work() as unit:
            unit.execute(
                "INSERT INTO project_target_admissions "
                "(project_uuid, target_identity, account_identity, private_teamspace_id, "
                "configuration_generation, admission_state, admission_generation, binding_audience) "
                "VALUES (?, 'https://app.spec-kitty.ai', 'account-t034', 'team-t034', 4, "
                "'admitted', 'admission-t034', 'private-teamspace:team-t034')",
                (project_uuid,),
            )
    return root, store


def _attempt_rows(store: ProjectSyncStore) -> list[tuple[Any, ...]]:
    with store.unit_of_work() as unit:
        return [
            tuple(row)
            for row in unit.execute(
                "SELECT attempt_id, state, payload_reference FROM delivery_attempts WHERE project_uuid = ? ORDER BY created_at",
                (store.project_uuid.storage_token,),
            ).fetchall()
        ]


def _result_rows(store: ProjectSyncStore) -> list[tuple[Any, ...]]:
    with store.unit_of_work() as unit:
        return [
            tuple(row)
            for row in unit.execute(
                "SELECT attempt_id, outcome, terminal_refusal_category FROM delivery_results WHERE project_uuid = ? ORDER BY recorded_at",
                (store.project_uuid.storage_token,),
            ).fetchall()
        ]


def test_opt_out_under_lease_rejects_cross_project_wrong_path_and_stale_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "project-a").mkdir()
    (tmp_path / "project-b").mkdir()
    _, store_a = _seed_project(
        tmp_path / "project-a",
        monkeypatch,
        "12121212-1212-4212-8212-121212121212",
    )
    _, store_b = _seed_project(
        tmp_path / "project-b",
        monkeypatch,
        "13131313-1313-4313-8313-131313131313",
    )
    spec = DeliveryAttemptSpec(
        attempt_id="attempt-project-b",
        write_kind="event",
        native_identity="event-project-b",
        payload_hash="sha256:project-b",
        payload_reference="event:project-b",
        deadline_at="2999-01-01T00:00:00Z",
        reconciliation_policy="native_identity_query",
    )
    with acquire_project_transport_lease(store_b) as lease_b, lease_b.unit_of_work() as (unit, context):
        prepare_delivery_attempt(unit, context, spec)

    with acquire_project_transport_lease(store_a) as lease_a:
        cross_project = TransportLeaseContext(
            store=store_b,
            lease_identity=lease_a.lease_identity,
            lock_path=lease_a.lock_path,
        )
        with pytest.raises(ProjectStoreError, match="live project transport lease"):
            settle_attempts_for_opt_out_under_lease(
                cross_project,
                reason="forged-cross-project",
            )

        wrong_path = TransportLeaseContext(
            store=store_a,
            lease_identity=lease_a.lease_identity,
            lock_path=store_b.egress_lock_path,
        )
        with pytest.raises(ProjectStoreError, match="live project transport lease"):
            settle_attempts_for_opt_out_under_lease(
                wrong_path,
                reason="forged-wrong-path",
            )

    with pytest.raises(ProjectStoreError, match="live project transport lease"):
        settle_attempts_for_opt_out_under_lease(
            lease_a,
            reason="stale-context",
        )
    assert _attempt_rows(store_b)[0][1] == DeliveryAttemptState.PREPARED.value


def _deadline(*, minutes: int = 5) -> str:
    return (now_utc() + timedelta(minutes=minutes)).isoformat()


def _operation_request(
    *,
    semantic_key: str = "team-integrations:team-t034",
    repeatability: LogicalOperationRepeatability = LogicalOperationRepeatability.REPEATABLE_READ,
    payload_hash: str = "sha256:t034-payload",
    policy: str = "native_identity_retry",
    deadline_at: str | None = None,
    recover_with_persisted_deadline: bool = False,
) -> LogicalOperationRequest:
    return LogicalOperationRequest(
        write_kind="generic_saas_get" if repeatability is LogicalOperationRepeatability.REPEATABLE_READ else "tracker_hosted_push",
        semantic_key=semantic_key,
        payload_hash=payload_hash,
        payload_reference=f"t034:{semantic_key}",
        repeatability=repeatability,
        reconciliation_policy=policy,
        deadline_at=deadline_at or _deadline(),
        recover_with_persisted_deadline=recover_with_persisted_deadline,
    )


def _finish_operation(
    store: ProjectSyncStore,
    attempt_id: str,
    outcome: DeliveryOutcome,
    *,
    refusal_category: str | None = None,
) -> None:
    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        mark_transport_started(unit, context, attempt_id)
        record_delivery_result(
            unit,
            context,
            result_id=f"{attempt_id}:test-result",
            attempt_id=attempt_id,
            outcome=outcome,
            terminal_refusal_category=refusal_category,
        )


def test_repeatable_reads_allocate_distinct_durable_identities_after_terminal_prior(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "55555555-5555-4555-8555-555555555555")
    request = _operation_request()

    first = allocate_logical_delivery_operation(store, request)
    _finish_operation(store, first.attempt_id, DeliveryOutcome.DELIVERED)
    second = allocate_logical_delivery_operation(store, request)

    assert first.disposition is LogicalOperationDisposition.NEW_PREPARED
    assert second.disposition is LogicalOperationDisposition.NEW_PREPARED
    assert first.attempt_id != second.attempt_id
    assert first.native_identity != second.native_identity
    assert len(_attempt_rows(store)) == 2


def test_concurrent_repeatable_read_allocation_converges_on_same_nonterminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "66666666-6666-4666-8666-666666666666")
    request = _operation_request()

    with ThreadPoolExecutor(max_workers=2) as executor:
        decisions = list(executor.map(lambda _index: allocate_logical_delivery_operation(store, request), range(2)))

    assert {decision.disposition for decision in decisions} == {
        LogicalOperationDisposition.NEW_PREPARED,
        LogicalOperationDisposition.PREPARED_RETRY,
    }
    assert len({decision.attempt_id for decision in decisions}) == 1
    assert len({decision.native_identity for decision in decisions}) == 1
    assert len(_attempt_rows(store)) == 1


@pytest.mark.parametrize(
    ("outcome", "refusal_category"),
    (
        (DeliveryOutcome.DELIVERED, None),
        (DeliveryOutcome.DUPLICATE, None),
        (DeliveryOutcome.REFUSED, "project_not_admitted"),
    ),
)
def test_idempotent_write_returns_terminal_prior_without_resend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: DeliveryOutcome,
    refusal_category: str | None,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "77777777-7777-4777-8777-777777777777")
    request = _operation_request(
        semantic_key="tracker-push:github:project:batch-1",
        repeatability=LogicalOperationRepeatability.IDEMPOTENT_WRITE,
    )

    first = allocate_logical_delivery_operation(store, request)
    _finish_operation(store, first.attempt_id, outcome, refusal_category=refusal_category)
    terminal = allocate_logical_delivery_operation(store, request)

    assert terminal.disposition is LogicalOperationDisposition.TERMINAL_PRIOR
    assert terminal.attempt_id == first.attempt_id
    assert terminal.native_identity == first.native_identity
    assert terminal.outcome is outcome
    assert terminal.terminal_refusal_category == refusal_category
    assert terminal.may_resend is False
    assert terminal.may_query is False
    assert terminal.requires_operator_review is False
    assert len(_attempt_rows(store)) == 1


def test_authority_drift_returns_operator_review_without_new_operation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "88888888-8888-4888-8888-888888888888")
    request = _operation_request()
    first = allocate_logical_delivery_operation(store, request)
    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE project_target_admissions SET configuration_generation = 5, admission_generation = 'admission-t034-next' WHERE project_uuid = ?",
            (store.project_uuid.storage_token,),
        )

    drifted = allocate_logical_delivery_operation(store, request)

    assert drifted.disposition is LogicalOperationDisposition.OPERATOR_REVIEW
    assert drifted.attempt_id == first.attempt_id
    assert drifted.may_resend is False
    assert "authority" in drifted.diagnostic
    assert "project_not_admitted" not in drifted.diagnostic
    assert len(_attempt_rows(store)) == 1


def test_payload_and_semantic_key_drift_fail_to_operator_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "99999999-9999-4999-8999-999999999999")
    request = _operation_request(
        semantic_key="tracker-push:github:project:batch-drift",
        repeatability=LogicalOperationRepeatability.IDEMPOTENT_WRITE,
    )
    first = allocate_logical_delivery_operation(store, request)

    payload_drift = allocate_logical_delivery_operation(
        store,
        _operation_request(
            semantic_key=request.semantic_key,
            repeatability=request.repeatability,
            payload_hash="sha256:different-payload",
        ),
    )
    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT payload_reference FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (store.project_uuid.storage_token, first.attempt_id),
        ).fetchone()
        assert row is not None
        metadata = json.loads(str(row[0]))
        metadata["logical_operation_semantic_key"] = "tracker-push:corrupt-key"
        unit.execute(
            "UPDATE delivery_attempts SET payload_reference = ? WHERE project_uuid = ? AND attempt_id = ?",
            (json.dumps(metadata, sort_keys=True), store.project_uuid.storage_token, first.attempt_id),
        )
    key_drift = allocate_logical_delivery_operation(store, request)

    assert payload_drift.disposition is LogicalOperationDisposition.OPERATOR_REVIEW
    assert "payload" in payload_drift.diagnostic
    assert key_drift.disposition is LogicalOperationDisposition.OPERATOR_REVIEW
    assert "semantic" in key_drift.diagnostic
    assert len(_attempt_rows(store)) == 1


def test_recovery_request_policy_and_deadline_drift_require_operator_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "13131313-1313-4313-8313-131313131313")
    request = _operation_request()
    first = allocate_logical_delivery_operation(store, request)
    policy_drift = allocate_logical_delivery_operation(
        store,
        LogicalOperationRequest(
            write_kind=request.write_kind,
            semantic_key=request.semantic_key,
            payload_hash=request.payload_hash,
            payload_reference=request.payload_reference,
            repeatability=request.repeatability,
            reconciliation_policy="operator_review",
            deadline_at=request.deadline_at,
        ),
    )
    deadline_drift = allocate_logical_delivery_operation(
        store,
        LogicalOperationRequest(
            write_kind=request.write_kind,
            semantic_key=request.semantic_key,
            payload_hash=request.payload_hash,
            payload_reference=request.payload_reference,
            repeatability=request.repeatability,
            reconciliation_policy=request.reconciliation_policy,
            deadline_at=_deadline(minutes=6),
        ),
    )

    assert policy_drift.disposition is LogicalOperationDisposition.OPERATOR_REVIEW
    assert "policy drift" in policy_drift.diagnostic
    assert deadline_drift.disposition is LogicalOperationDisposition.OPERATOR_REVIEW
    assert "deadline drift" in deadline_drift.diagnostic
    assert policy_drift.attempt_id == deadline_drift.attempt_id == first.attempt_id
    assert len(_attempt_rows(store)) == 1


def test_corrupt_unrelated_logical_row_does_not_block_requested_operation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "14141414-1414-4414-8414-141414141414")
    requested = _operation_request(semantic_key="requested-read")
    unrelated = _operation_request(semantic_key="unrelated-read")
    first = allocate_logical_delivery_operation(store, requested)
    other = allocate_logical_delivery_operation(store, unrelated)
    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE delivery_attempts SET payload_reference = '{not-json' WHERE project_uuid = ? AND attempt_id = ?",
            (store.project_uuid.storage_token, other.attempt_id),
        )

    recovered = allocate_logical_delivery_operation(store, requested)

    assert recovered.disposition is LogicalOperationDisposition.PREPARED_RETRY
    assert recovered.attempt_id == first.attempt_id
    assert len(_attempt_rows(store)) == 2


@pytest.mark.parametrize(
    "state",
    (
        DeliveryAttemptState.IN_FLIGHT,
        DeliveryAttemptState.PENDING_REMOTE,
        DeliveryAttemptState.UNKNOWN,
    ),
)
def test_query_policy_exposes_query_only_for_uncertain_states(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: DeliveryAttemptState,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    request = _operation_request(policy="native_identity_query")
    first = allocate_logical_delivery_operation(store, request)
    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        mark_transport_started(unit, context, first.attempt_id)
        if state is DeliveryAttemptState.PENDING_REMOTE:
            attach_remote_operation_id(unit, context, attempt_id=first.attempt_id, remote_operation_id="remote-query-1")
            record_delivery_result(
                unit,
                context,
                result_id=f"{first.attempt_id}:pending",
                attempt_id=first.attempt_id,
                outcome=DeliveryOutcome.PENDING,
            )
        elif state is DeliveryAttemptState.UNKNOWN:
            mark_delivery_result_unknown(unit, context, attempt_id=first.attempt_id, reason="lost response")

    decision = allocate_logical_delivery_operation(store, request)

    assert decision.disposition is LogicalOperationDisposition.QUERY_NATIVE
    assert decision.state is state
    assert decision.may_resend is False
    assert decision.may_query is True
    assert decision.requires_operator_review is False
    assert decision.remote_operation_id == ("remote-query-1" if state is DeliveryAttemptState.PENDING_REMOTE else None)


def test_prepared_retry_and_retryable_restart_remain_distinct(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    request = _operation_request()
    first = allocate_logical_delivery_operation(store, request)
    prepared = allocate_logical_delivery_operation(store, request)
    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        mark_transport_started(unit, context, first.attempt_id)
        record_delivery_result(
            unit,
            context,
            result_id=f"{first.attempt_id}:retryable",
            attempt_id=first.attempt_id,
            outcome=DeliveryOutcome.RETRYABLE_NO_EFFECT,
        )
    retryable = allocate_logical_delivery_operation(store, request)

    assert prepared.disposition is LogicalOperationDisposition.PREPARED_RETRY
    assert prepared.state is DeliveryAttemptState.PREPARED
    assert retryable.disposition is LogicalOperationDisposition.RETRYABLE_RESTART
    assert retryable.state is DeliveryAttemptState.RETRYABLE_NO_EFFECT
    assert retryable.attempt_id == first.attempt_id
    assert retryable.may_resend is True


def test_allocator_persists_caller_deadline_and_rejects_unbounded_sentinel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "cccccccc-cccc-4ccc-8ccc-cccccccccccc")
    deadline = _deadline(minutes=5)
    decision = allocate_logical_delivery_operation(store, _operation_request(deadline_at=deadline))
    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT deadline_at FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (store.project_uuid.storage_token, decision.attempt_id),
        ).fetchone()

    assert row == (deadline,)
    with pytest.raises(ValueError, match="bounded"):
        allocate_logical_delivery_operation(
            store,
            _operation_request(semantic_key="unbounded", deadline_at="2999-01-01T00:00:00Z"),
        )


def test_expired_persisted_prepared_operation_returns_typed_operator_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "cdcdcdcd-cdcd-4dcd-8dcd-cdcdcdcdcdcd")
    allocation_time = datetime(2026, 1, 1, tzinfo=UTC)
    request = _operation_request(deadline_at=(allocation_time + timedelta(minutes=5)).isoformat())
    first = allocate_logical_delivery_operation(store, request, now=allocation_time)

    recovered = allocate_logical_delivery_operation(
        store,
        request,
        now=allocation_time + timedelta(minutes=6),
    )

    assert recovered.attempt_id == first.attempt_id
    assert recovered.state is DeliveryAttemptState.PREPARED
    assert recovered.disposition is LogicalOperationDisposition.OPERATOR_REVIEW
    assert recovered.may_resend is False
    assert recovered.may_query is False
    assert "deadline expired" in recovered.diagnostic
    assert len(_attempt_rows(store)) == 1


@pytest.mark.parametrize(
    ("state", "expected"),
    (
        (DeliveryAttemptState.PREPARED, LogicalOperationDisposition.PREPARED_RETRY),
        (DeliveryAttemptState.RETRYABLE_NO_EFFECT, LogicalOperationDisposition.RETRYABLE_RESTART),
        (DeliveryAttemptState.PENDING_REMOTE, LogicalOperationDisposition.QUERY_NATIVE),
        (DeliveryAttemptState.UNKNOWN, LogicalOperationDisposition.QUERY_NATIVE),
    ),
)
def test_fresh_request_recovers_exact_nonterminal_with_persisted_deadline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: DeliveryAttemptState,
    expected: LogicalOperationDisposition,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "cececece-cece-4ece-8ece-cececececece")
    request = _operation_request(policy="native_identity_retry_then_query", deadline_at=_deadline(minutes=5))
    first = allocate_logical_delivery_operation(store, request)
    if state is not DeliveryAttemptState.PREPARED:
        with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
            mark_transport_started(unit, context, first.attempt_id)
            if state is DeliveryAttemptState.RETRYABLE_NO_EFFECT:
                record_delivery_result(
                    unit,
                    context,
                    result_id=f"{first.attempt_id}:retryable",
                    attempt_id=first.attempt_id,
                    outcome=DeliveryOutcome.RETRYABLE_NO_EFFECT,
                )
            elif state is DeliveryAttemptState.PENDING_REMOTE:
                attach_remote_operation_id(unit, context, attempt_id=first.attempt_id, remote_operation_id="fresh-process")
                record_delivery_result(
                    unit,
                    context,
                    result_id=f"{first.attempt_id}:pending",
                    attempt_id=first.attempt_id,
                    outcome=DeliveryOutcome.PENDING,
                )
            else:
                mark_delivery_result_unknown(unit, context, attempt_id=first.attempt_id, reason="fresh process")
    recovered_request = _operation_request(
        policy=request.reconciliation_policy,
        deadline_at=_deadline(minutes=6),
        recover_with_persisted_deadline=True,
    )

    recovered = allocate_logical_delivery_operation(store, recovered_request)

    assert recovered.disposition is expected
    assert recovered.attempt_id == first.attempt_id
    assert recovered.deadline_at == request.deadline_at


def test_persisted_deadline_recovery_still_fails_closed_when_expired(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "cfcfcfcf-cfcf-4fcf-8fcf-cfcfcfcfcfcf")
    allocation_time = datetime(2026, 2, 1, tzinfo=UTC)
    request = _operation_request(deadline_at=(allocation_time + timedelta(minutes=5)).isoformat())
    first = allocate_logical_delivery_operation(store, request, now=allocation_time)
    recovered_request = _operation_request(
        deadline_at=(allocation_time + timedelta(minutes=20)).isoformat(),
        recover_with_persisted_deadline=True,
    )

    recovered = allocate_logical_delivery_operation(
        store,
        recovered_request,
        now=allocation_time + timedelta(minutes=6),
    )

    assert recovered.disposition is LogicalOperationDisposition.OPERATOR_REVIEW
    assert recovered.attempt_id == first.attempt_id
    assert recovered.may_resend is False
    assert "expired" in recovered.diagnostic


def test_terminal_repeatable_read_uses_fresh_caller_deadline_not_prior_deadline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "d0d0d0d0-d0d0-40d0-80d0-d0d0d0d0d0d0")
    first_request = _operation_request(deadline_at=_deadline(minutes=5))
    first = allocate_logical_delivery_operation(store, first_request)
    _finish_operation(store, first.attempt_id, DeliveryOutcome.DELIVERED)
    fresh_deadline = _deadline(minutes=6)

    second = allocate_logical_delivery_operation(
        store,
        _operation_request(
            deadline_at=fresh_deadline,
            recover_with_persisted_deadline=True,
        ),
    )

    assert second.disposition is LogicalOperationDisposition.NEW_PREPARED
    assert second.attempt_id != first.attempt_id
    assert second.deadline_at == fresh_deadline


def test_persisted_deadline_is_not_adopted_from_corrupt_or_ambiguous_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "d1d1d1d1-d1d1-41d1-81d1-d1d1d1d1d1d1")
    corrupt_request = _operation_request(semantic_key="corrupt-deadline-adoption")
    corrupt = allocate_logical_delivery_operation(store, corrupt_request)
    ambiguous_request = _operation_request(semantic_key="ambiguous-deadline-adoption")
    ambiguous = allocate_logical_delivery_operation(store, ambiguous_request)
    duplicate_id = f"{ambiguous.attempt_id.rsplit(':', 1)[0]}:00000000-0000-4000-8000-000000000099"
    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE delivery_attempts SET payload_reference = '{not-json' WHERE project_uuid = ? AND attempt_id = ?",
            (store.project_uuid.storage_token, corrupt.attempt_id),
        )
        row = unit.execute(
            "SELECT payload_reference FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (store.project_uuid.storage_token, ambiguous.attempt_id),
        ).fetchone()
        assert row is not None
        metadata = json.loads(str(row[0]))
        metadata["native_identity"] = duplicate_id
        unit.execute(
            "INSERT INTO delivery_attempts "
            "(attempt_id, project_uuid, epoch_id, outbox_task_id, consent_generation, target_generation, "
            "admission_generation, binding_audience, payload_hash, payload_reference, state, deadline_at, "
            "reconciliation_policy, created_at) "
            "SELECT ?, project_uuid, epoch_id, outbox_task_id, consent_generation, target_generation, "
            "admission_generation, binding_audience, payload_hash, ?, state, deadline_at, reconciliation_policy, ? "
            "FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (
                duplicate_id,
                json.dumps(metadata, sort_keys=True),
                now_utc_iso(),
                store.project_uuid.storage_token,
                ambiguous.attempt_id,
            ),
        )

    corrupt_recovery = allocate_logical_delivery_operation(
        store,
        _operation_request(
            semantic_key=corrupt_request.semantic_key,
            deadline_at=_deadline(minutes=6),
            recover_with_persisted_deadline=True,
        ),
    )
    ambiguous_recovery = allocate_logical_delivery_operation(
        store,
        _operation_request(
            semantic_key=ambiguous_request.semantic_key,
            deadline_at=_deadline(minutes=6),
            recover_with_persisted_deadline=True,
        ),
    )

    assert corrupt_recovery.disposition is LogicalOperationDisposition.OPERATOR_REVIEW
    assert "metadata" in corrupt_recovery.diagnostic
    assert ambiguous_recovery.disposition is LogicalOperationDisposition.OPERATOR_REVIEW
    assert "multiple nonterminal" in ambiguous_recovery.diagnostic


def test_corrupt_logical_operation_metadata_requires_operator_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "dddddddd-dddd-4ddd-8ddd-dddddddddddd")
    request = _operation_request()
    first = allocate_logical_delivery_operation(store, request)
    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE delivery_attempts SET payload_reference = '{not-json' WHERE project_uuid = ? AND attempt_id = ?",
            (store.project_uuid.storage_token, first.attempt_id),
        )

    decision = allocate_logical_delivery_operation(store, request)

    assert decision.disposition is LogicalOperationDisposition.OPERATOR_REVIEW
    assert decision.attempt_id == first.attempt_id
    assert decision.native_identity is None
    assert decision.requires_operator_review is True
    assert "metadata" in decision.diagnostic


def test_remote_operation_correlation_is_durable_for_pending_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
    request = _operation_request(policy="native_identity_query")
    first = allocate_logical_delivery_operation(store, request)
    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        mark_transport_started(unit, context, first.attempt_id)
        attach_remote_operation_id(unit, context, attempt_id=first.attempt_id, remote_operation_id="remote-operation-7")
        record_delivery_result(
            unit,
            context,
            result_id=f"{first.attempt_id}:pending",
            attempt_id=first.attempt_id,
            outcome=DeliveryOutcome.PENDING,
        )
    with store.unit_of_work() as unit:
        attached = read_remote_operation_id(unit, attempt_id=first.attempt_id)
    recovered = allocate_logical_delivery_operation(store, request)

    assert attached == "remote-operation-7"
    assert recovered.disposition is LogicalOperationDisposition.QUERY_NATIVE
    assert recovered.remote_operation_id == "remote-operation-7"
    assert recovered.may_resend is False


@pytest.mark.parametrize(
    ("uncertain_state", "queried_outcome"),
    (
        (DeliveryAttemptState.PENDING_REMOTE, DeliveryOutcome.DELIVERED),
        (DeliveryAttemptState.PENDING_REMOTE, DeliveryOutcome.RETRYABLE_NO_EFFECT),
        (DeliveryAttemptState.UNKNOWN, DeliveryOutcome.DELIVERED),
        (DeliveryAttemptState.UNKNOWN, DeliveryOutcome.RETRYABLE_NO_EFFECT),
    ),
)
def test_uncertain_result_promotion_requires_query_execution_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    uncertain_state: DeliveryAttemptState,
    queried_outcome: DeliveryOutcome,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "abababab-abab-4bab-8bab-abababababab")
    request = _operation_request(policy="native_identity_query")
    first = allocate_logical_delivery_operation(store, request)
    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        mark_transport_started(unit, context, first.attempt_id)
        attach_remote_operation_id(unit, context, attempt_id=first.attempt_id, remote_operation_id="remote-proof-1")
        if uncertain_state is DeliveryAttemptState.PENDING_REMOTE:
            record_delivery_result(
                unit,
                context,
                result_id=f"{first.attempt_id}:pending",
                attempt_id=first.attempt_id,
                outcome=DeliveryOutcome.PENDING,
            )
        else:
            mark_delivery_result_unknown(unit, context, attempt_id=first.attempt_id, reason="query recovery")
    with (
        acquire_project_transport_lease(store) as lease,
        lease.unit_of_work() as (unit, context),
        pytest.raises(ProjectStoreError, match="query execution seam"),
    ):
        record_delivery_result(
            unit,
            context,
            result_id=f"{first.attempt_id}:terminal",
            attempt_id=first.attempt_id,
            outcome=queried_outcome,
        )
    assert not hasattr(attempts_module, "_RemoteOperationQueryProof")
    with (
        acquire_project_transport_lease(store) as lease,
        lease.unit_of_work() as (unit, context),
        pytest.raises(TypeError, match="unexpected keyword"),
    ):
        record_delivery_result(
            unit,
            context,
            result_id=f"{first.attempt_id}:forged",
            attempt_id=first.attempt_id,
            outcome=queried_outcome,
            _query_proof=object(),
        )
    queried: list[str] = []

    def _query(remote_operation_id: str) -> object:
        with store.unit_of_work() as unit:
            unit.execute("SELECT 1").fetchone()
        queried.append(remote_operation_id)
        return {"status": "completed"}

    value = execute_remote_operation_query(
        store,
        attempt_id=first.attempt_id,
        result_id=f"{first.attempt_id}:terminal",
        query=_query,
        classify=lambda _value: (queried_outcome, None),
    )

    recovered = allocate_logical_delivery_operation(store, request)
    assert value == {"status": "completed"}
    assert queried == ["remote-proof-1"]
    if queried_outcome is DeliveryOutcome.DELIVERED:
        assert recovered.disposition is LogicalOperationDisposition.NEW_PREPARED
        assert recovered.attempt_id != first.attempt_id
    else:
        assert recovered.disposition is LogicalOperationDisposition.OPERATOR_REVIEW
        assert recovered.state is DeliveryAttemptState.RETRYABLE_NO_EFFECT
        assert recovered.attempt_id == first.attempt_id


def test_operator_review_policy_never_claims_query_or_resend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "bcbcbcbc-bcbc-4cbc-8cbc-bcbcbcbcbcbc")
    request = _operation_request(policy="operator_review")
    first = allocate_logical_delivery_operation(store, request)
    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        mark_transport_started(unit, context, first.attempt_id)

    decision = allocate_logical_delivery_operation(store, request)

    assert decision.disposition is LogicalOperationDisposition.OPERATOR_REVIEW
    assert decision.state is DeliveryAttemptState.IN_FLIGHT
    assert decision.may_resend is False
    assert decision.may_query is False
    assert decision.requires_operator_review is True


@pytest.mark.parametrize("expired", (False, True))
def test_query_executor_obeys_persisted_policy_and_deadline_before_callback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    expired: bool,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "bdbdbdbd-bdbd-4dbd-8dbd-bdbdbdbdbdbd")
    policy = "native_identity_query" if expired else "operator_review"
    request = _operation_request(policy=policy)
    first = allocate_logical_delivery_operation(store, request)
    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        mark_transport_started(unit, context, first.attempt_id)
        attach_remote_operation_id(
            unit,
            context,
            attempt_id=first.attempt_id,
            remote_operation_id="remote-policy-deadline",
        )
    if expired:
        expired_at = (now_utc() - timedelta(minutes=1)).isoformat()
        with store.unit_of_work() as unit:
            row = unit.execute(
                "SELECT payload_reference FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
                (store.project_uuid.storage_token, first.attempt_id),
            ).fetchone()
            assert row is not None
            metadata = json.loads(str(row[0]))
            metadata["deadline_at"] = expired_at
            unit.execute(
                "UPDATE delivery_attempts SET deadline_at = ?, payload_reference = ? WHERE project_uuid = ? AND attempt_id = ?",
                (
                    expired_at,
                    json.dumps(metadata, sort_keys=True),
                    store.project_uuid.storage_token,
                    first.attempt_id,
                ),
            )
    queried: list[str] = []

    with pytest.raises(ProjectStoreError, match="remote operation query is not authorized"):
        execute_remote_operation_query(
            store,
            attempt_id=first.attempt_id,
            result_id=f"{first.attempt_id}:forbidden-query",
            query=lambda remote_id: queried.append(remote_id),
            classify=lambda _value: (DeliveryOutcome.DELIVERED, None),
        )

    assert queried == []
    assert _result_rows(store) == []


def test_repeatable_identity_is_uuid_based_and_independent_of_retained_row_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "ffffffff-ffff-4fff-8fff-ffffffffffff")
    identities = iter((UUID("00000000-0000-4000-8000-000000000001"), UUID("00000000-0000-4000-8000-000000000002")))
    monkeypatch.setattr("specify_cli.sync.transport_attempts.uuid4", lambda: next(identities))
    request = _operation_request()
    first = allocate_logical_delivery_operation(store, request)
    _finish_operation(store, first.attempt_id, DeliveryOutcome.DELIVERED)
    with store.unit_of_work() as unit:
        unit.execute(
            "DELETE FROM delivery_results WHERE project_uuid = ? AND attempt_id = ?",
            (store.project_uuid.storage_token, first.attempt_id),
        )
        unit.execute(
            "DELETE FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (store.project_uuid.storage_token, first.attempt_id),
        )
    second = allocate_logical_delivery_operation(store, request)

    assert first.attempt_id.endswith("00000000-0000-4000-8000-000000000001")
    assert second.attempt_id.endswith("00000000-0000-4000-8000-000000000002")
    assert not second.attempt_id.endswith(":1")


def test_allocator_returns_only_after_prepared_row_is_durable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "12121212-1212-4212-8212-121212121212")

    decision = allocate_logical_delivery_operation(store, _operation_request())

    assert decision.disposition is LogicalOperationDisposition.NEW_PREPARED
    assert decision.state is DeliveryAttemptState.PREPARED
    assert _attempt_rows(store)[0][0:2] == (decision.attempt_id, DeliveryAttemptState.PREPARED.value)


@pytest.mark.parametrize(
    ("attempt_id", "semantic_key", "repeatability", "message"),
    (
        ("logical-operation:unscoped", None, None, "requires logical operation metadata"),
        ("logical-operation:partial", "partial", None, "requires both"),
        ("logical-operation:invalid", "invalid", "replayable", "repeatability is invalid"),
        (
            "logical-operation:not-derived",
            "not-derived",
            LogicalOperationRepeatability.IDEMPOTENT_WRITE.value,
            "not derived",
        ),
        (
            "ordinary-attempt",
            "ordinary-with-logical-fields",
            LogicalOperationRepeatability.IDEMPOTENT_WRITE.value,
            "requires a reserved",
        ),
    ),
)
def test_prepare_rejects_invalid_reserved_logical_operation_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attempt_id: str,
    semantic_key: str | None,
    repeatability: str | None,
    message: str,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "34343434-3434-4434-8434-343434343434")

    with (
        acquire_project_transport_lease(store) as lease,
        lease.unit_of_work() as (unit, context),
        pytest.raises(ProjectStoreError, match=message),
    ):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id=attempt_id,
                write_kind="generic_saas_get",
                native_identity=attempt_id,
                payload_hash="sha256:reserved-namespace",
                payload_reference="t034:reserved-namespace",
                deadline_at=_deadline(),
                reconciliation_policy="native_identity_retry",
                logical_operation_semantic_key=semantic_key,
                logical_operation_repeatability=repeatability,
            ),
        )

    assert _attempt_rows(store) == []


def test_allocator_is_the_valid_reserved_logical_operation_control(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "35353535-3535-4535-8535-353535353535")

    decision = allocate_logical_delivery_operation(store, _operation_request(semantic_key="valid-control"))

    assert decision.disposition is LogicalOperationDisposition.NEW_PREPARED
    assert decision.attempt_id.startswith("logical-operation:read:")
    assert _attempt_rows(store)[0][0] == decision.attempt_id


@pytest.mark.parametrize(
    ("state", "expected"),
    (
        (DeliveryAttemptState.PREPARED, LogicalOperationDisposition.PREPARED_RETRY),
        (DeliveryAttemptState.RETRYABLE_NO_EFFECT, LogicalOperationDisposition.RETRYABLE_RESTART),
        (DeliveryAttemptState.IN_FLIGHT, LogicalOperationDisposition.QUERY_NATIVE),
        (DeliveryAttemptState.PENDING_REMOTE, LogicalOperationDisposition.QUERY_NATIVE),
        (DeliveryAttemptState.UNKNOWN, LogicalOperationDisposition.QUERY_NATIVE),
    ),
)
def test_retry_then_query_policy_maps_each_recoverable_state_exactly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: DeliveryAttemptState,
    expected: LogicalOperationDisposition,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "36363636-3636-4636-8636-363636363636")
    request = _operation_request(policy="native_identity_retry_then_query")
    first = allocate_logical_delivery_operation(store, request)
    if state is not DeliveryAttemptState.PREPARED:
        with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
            mark_transport_started(unit, context, first.attempt_id)
            if state is DeliveryAttemptState.RETRYABLE_NO_EFFECT:
                record_delivery_result(
                    unit,
                    context,
                    result_id=f"{first.attempt_id}:no-effect",
                    attempt_id=first.attempt_id,
                    outcome=DeliveryOutcome.RETRYABLE_NO_EFFECT,
                )
            elif state is DeliveryAttemptState.PENDING_REMOTE:
                attach_remote_operation_id(unit, context, attempt_id=first.attempt_id, remote_operation_id="combined-op")
                record_delivery_result(
                    unit,
                    context,
                    result_id=f"{first.attempt_id}:pending",
                    attempt_id=first.attempt_id,
                    outcome=DeliveryOutcome.PENDING,
                )
            elif state is DeliveryAttemptState.UNKNOWN:
                mark_delivery_result_unknown(unit, context, attempt_id=first.attempt_id, reason="combined uncertainty")

    decision = allocate_logical_delivery_operation(store, request)

    assert decision.disposition is expected
    assert decision.attempt_id == first.attempt_id
    assert decision.may_resend is (expected in {LogicalOperationDisposition.PREPARED_RETRY, LogicalOperationDisposition.RETRYABLE_RESTART})
    assert decision.may_query is (expected is LogicalOperationDisposition.QUERY_NATIVE)
    assert decision.requires_operator_review is False


def test_retry_then_query_policy_executes_only_pending_native_query_and_rejects_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "37373737-3737-4737-8737-373737373737")
    request = _operation_request(policy="native_identity_retry_then_query")
    first = allocate_logical_delivery_operation(store, request)
    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        mark_transport_started(unit, context, first.attempt_id)
        attach_remote_operation_id(unit, context, attempt_id=first.attempt_id, remote_operation_id="combined-query")
        record_delivery_result(
            unit,
            context,
            result_id=f"{first.attempt_id}:pending",
            attempt_id=first.attempt_id,
            outcome=DeliveryOutcome.PENDING,
        )
    queried: list[str] = []

    execute_remote_operation_query(
        store,
        attempt_id=first.attempt_id,
        result_id=f"{first.attempt_id}:delivered",
        query=lambda remote_id: queried.append(remote_id),
        classify=lambda _value: (DeliveryOutcome.DELIVERED, None),
    )

    assert queried == ["combined-query"]
    with pytest.raises(ProjectStoreError, match="not authorized"):
        execute_remote_operation_query(
            store,
            attempt_id=first.attempt_id,
            result_id=f"{first.attempt_id}:replay",
            query=lambda remote_id: queried.append(remote_id),
            classify=lambda _value: (DeliveryOutcome.DELIVERED, None),
        )
    assert queried == ["combined-query"]


def _projection_spec(attempt_id: str = "projection-attempt") -> DeliveryAttemptSpec:
    return DeliveryAttemptSpec(
        attempt_id=attempt_id,
        write_kind="history_preflight_chunk",
        native_identity=f"history:{attempt_id}",
        payload_hash="sha256:projection",
        payload_reference="history:exact-chunk",
        deadline_at=_deadline(),
        reconciliation_policy="native_identity_retry_then_query",
    )


@pytest.mark.parametrize(
    ("outcome", "category", "terminal_state"),
    (
        (DeliveryOutcome.DELIVERED, None, DeliveryAttemptState.SUCCEEDED),
        (DeliveryOutcome.DUPLICATE, None, DeliveryAttemptState.SUCCEEDED),
        (DeliveryOutcome.REFUSED, "project_not_admitted", DeliveryAttemptState.REFUSED),
        (DeliveryOutcome.TERMINAL_UNKNOWN, "opt_out", DeliveryAttemptState.TERMINAL_UNKNOWN),
    ),
)
def test_terminal_projection_distinguishes_absent_nonterminal_and_exact_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: DeliveryOutcome,
    category: str | None,
    terminal_state: DeliveryAttemptState,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "38383838-3838-4838-8838-383838383838")
    spec = _projection_spec()
    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        absent = get_delivery_terminal_result_projection(unit, context, spec)
        prepare_delivery_attempt(unit, context, spec)
        nonterminal = get_delivery_terminal_result_projection(unit, context, spec)
        mark_transport_started(unit, context, spec.attempt_id)
        record_delivery_result(
            unit,
            context,
            result_id=f"{spec.attempt_id}:delivered",
            attempt_id=spec.attempt_id,
            outcome=outcome,
            terminal_refusal_category=category,
        )
        terminal = get_delivery_terminal_result_projection(unit, context, spec)

    assert absent.status is DeliveryTerminalResultStatus.ABSENT
    assert nonterminal.status is DeliveryTerminalResultStatus.NONTERMINAL
    assert nonterminal.state is DeliveryAttemptState.PREPARED
    assert terminal.status is DeliveryTerminalResultStatus.TERMINAL
    assert terminal.state is terminal_state
    assert terminal.outcome is outcome
    assert terminal.terminal_refusal_category == category


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("write_kind", "other-kind", "write_kind"),
        ("native_identity", "history:other", "native_identity"),
        ("payload_hash", "sha256:other", "payload hash"),
        ("payload_reference", "history:other", "payload_reference"),
    ),
)
def test_terminal_projection_fails_closed_on_exact_identity_or_payload_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
    message: str,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "39393939-3939-4939-8939-393939393939")
    spec = _projection_spec()
    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(unit, context, spec)
        mark_transport_started(unit, context, spec.attempt_id)
        record_delivery_result(
            unit,
            context,
            result_id=f"{spec.attempt_id}:delivered",
            attempt_id=spec.attempt_id,
            outcome=DeliveryOutcome.DELIVERED,
        )
    values = {
        "attempt_id": spec.attempt_id,
        "write_kind": spec.write_kind,
        "native_identity": spec.native_identity,
        "payload_hash": spec.payload_hash,
        "payload_reference": spec.payload_reference,
        "deadline_at": spec.deadline_at,
        "reconciliation_policy": spec.reconciliation_policy,
    }
    values[field] = value
    mismatched = DeliveryAttemptSpec(**values)

    with (
        acquire_project_transport_lease(store) as lease,
        lease.unit_of_work() as (unit, context),
        pytest.raises(ProjectStoreError, match=message),
    ):
        get_delivery_terminal_result_projection(unit, context, mismatched)


def test_terminal_projection_fails_closed_on_corruption_old_authority_and_missing_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "40404040-4040-4040-8040-404040404040")
    corrupt = _projection_spec("projection-corrupt")
    missing = _projection_spec("projection-missing")
    old = _projection_spec("projection-old")
    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        for spec in (corrupt, missing, old):
            prepare_delivery_attempt(unit, context, spec)
        unit.execute(
            "UPDATE delivery_attempts SET payload_reference = '{not-json' WHERE project_uuid = ? AND attempt_id = ?",
            (store.project_uuid.storage_token, corrupt.attempt_id),
        )
        unit.execute(
            "UPDATE delivery_attempts SET state = ? WHERE project_uuid = ? AND attempt_id = ?",
            (DeliveryAttemptState.SUCCEEDED.value, store.project_uuid.storage_token, missing.attempt_id),
        )
    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        with pytest.raises(ProjectStoreError, match="authority|metadata"):
            get_delivery_terminal_result_projection(unit, context, corrupt)
        with pytest.raises(ProjectStoreError, match="exactly one"):
            get_delivery_terminal_result_projection(unit, context, missing)
    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE project_target_admissions SET configuration_generation = 5, admission_generation = 'new-generation' WHERE project_uuid = ?",
            (store.project_uuid.storage_token,),
        )
    with (
        acquire_project_transport_lease(store) as lease,
        lease.unit_of_work() as (unit, context),
        pytest.raises(ProjectStoreError, match="authority"),
    ):
        get_delivery_terminal_result_projection(unit, context, old)


@pytest.mark.parametrize(
    ("corruption", "message"),
    (
        ("nonterminal_terminal_result", "contradictory terminal result"),
        ("invalid_state", "state is invalid"),
        ("invalid_outcome", "result row is corrupt"),
        ("invalid_result_authority", "result row is corrupt"),
    ),
)
def test_terminal_projection_normalizes_state_result_and_authority_corruption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corruption: str,
    message: str,
) -> None:
    _, store = _seed_project(tmp_path, monkeypatch, "41414141-4141-4141-8141-414141414141")
    spec = _projection_spec(f"projection-{corruption}")
    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(unit, context, spec)
        if corruption == "invalid_state":
            unit.execute(
                "UPDATE delivery_attempts SET state = 'invented' WHERE project_uuid = ? AND attempt_id = ?",
                (store.project_uuid.storage_token, spec.attempt_id),
            )
        else:
            result_outcome = "invented" if corruption == "invalid_outcome" else DeliveryOutcome.DELIVERED.value
            result_target_generation: object = (
                "not-an-integer"
                if corruption == "invalid_result_authority"
                else (context.target_audience.configuration_generation if context.target_audience is not None else None)
            )
            unit.execute(
                "INSERT INTO delivery_results "
                "(result_id, project_uuid, epoch_id, attempt_id, target_generation, admission_generation, outcome, "
                "terminal_refusal_category, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?)",
                (
                    f"{spec.attempt_id}:corrupt",
                    store.project_uuid.storage_token,
                    context.epoch_id,
                    spec.attempt_id,
                    result_target_generation,
                    context.admission_generation,
                    result_outcome,
                    now_utc_iso(),
                ),
            )

    with (
        acquire_project_transport_lease(store) as lease,
        lease.unit_of_work() as (unit, context),
        pytest.raises(ProjectStoreError, match=message),
    ):
        get_delivery_terminal_result_projection(unit, context, spec)

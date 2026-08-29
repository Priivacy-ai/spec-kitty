"""T033 acceptance tests for history and dossier transport convergence."""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
import requests

from specify_cli.delivery.interfaces import DeliveryTarget, TargetIdentity
from specify_cli.delivery.receivers import (
    DeliveryEffectCertainty,
    DeliveryOutcome,
    DeliveryResult,
    TeamspaceReceiver,
)
from specify_cli.delivery.targets import compute_target_id
from specify_cli.migration.envelope_seam import build_teamspace_envelope
from specify_cli.dossier.emitter_adapter import (
    fire_dossier_event,
    register_dossier_emitter,
    reset_dossier_emitter,
)
from specify_cli.dossier.events import emit_snapshot_computed
from specify_cli.dossier.models import ArtifactRef
from specify_cli.sync.body_queue import OfflineBodyUploadQueue
from specify_cli.sync.body_upload import prepare_body_uploads
from specify_cli.sync.consent import (
    allocate_capture_sequence,
    record_project_opt_in,
    record_project_opt_out,
)
from specify_cli.sync.client import WebSocketClient
from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.history_disclosure import (
    HistoryDisclosureCapability,
    confirm_history_disclosure,
    preview_sealed_history,
)
from specify_cli.sync.history_import.upload import (
    PreflightRejected,
    _delivery_classification,
    _history_disclosures,
    run_import_upload,
    upload_envelopes,
)
from specify_cli.sync.project_context import AdmissionState, ProjectSyncContext
from specify_cli.sync.project_identity import CanonicalProjectUUID, ProjectIdentity
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.namespace import NamespaceRef, UploadStatus

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT = "aaaaaaaa-0000-0000-0000-0000000000aa"
OTHER = "bbbbbbbb-0000-0000-0000-0000000000bb"
SERVER = "https://app.spec-kitty.ai"


class _Response:
    def __init__(self, body: dict[str, Any], *, status_code: int = 200) -> None:
        self._body = body
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        return self._body


class _RecordingIngress:
    def __init__(self, store: ProjectSyncStore) -> None:
        self.store = store
        self.requests: list[tuple[str, bytes]] = []

    def __call__(
        self,
        url: str,
        *,
        data: bytes,
        headers: dict[str, str],
        timeout: float,
    ) -> _Response:
        del timeout
        # The canonical gate must not retain a project UoW across network I/O.
        with self.store.unit_of_work() as unit:
            assert unit.execute("SELECT 1").fetchone() == (1,)
        self.requests.append((url, data))
        assert headers["X-Spec-Kitty-Sync-Protocol"] == "2.0"
        events = json.loads(gzip.decompress(data).decode("utf-8"))["events"] if headers.get("Content-Encoding") == "gzip" else json.loads(data)["events"]
        if url.endswith("/preflight/"):
            return _Response({"results": [{"event_id": event["event_id"], "status": "success"} for event in events]})
        return _Response({"results": [{"event_id": event["event_id"], "status": "success"} for event in events]})


def _envelope(event_id: str, project_uuid: str = PROJECT) -> dict[str, Any]:
    canonical = build_teamspace_envelope(
        event_id=event_id,
        event_type="WPStatusChanged",
        aggregate_id="WP01",
        aggregate_type="WorkPackage",
        payload={"mission_slug": "private-engagement", "wp_id": "WP01"},
        timestamp="2026-08-01T00:00:00+00:00",
        build_id="interactive-transport-test",
        node_id="interactive-transport-test",
        lamport_clock=1,
        project_uuid=project_uuid,
        project_slug="private-engagement",
        repo_slug=None,
        correlation_id=event_id,
    ).model_dump()
    return {key: canonical[key] for key in ("event_id", "event_type", "project_uuid", "payload")}


def _target(project_uuid: str = PROJECT) -> DeliveryTarget:
    identity = TargetIdentity(
        target_identity=SERVER,
        account_identity="account-1",
        private_teamspace_id="teamspace-1",
        project_uuid=CanonicalProjectUUID.parse(project_uuid),
        configuration_generation=4,
    )
    return DeliveryTarget(
        target_id=compute_target_id(
            target_identity=identity.target_identity,
            account_identity=identity.account_identity,
            private_teamspace_id=identity.private_teamspace_id,
            project_uuid=identity.project_uuid,
            configuration_generation=identity.configuration_generation,
        ),
        identity=identity,
        admission_state=AdmissionState.ADMITTED,
        admission_generation=9,
        binding_audience="private-teamspace:teamspace-1",
        last_error_category=None,
    )


def _admitted_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    project_uuid: str = PROJECT,
) -> tuple[ProjectSyncStore, ProjectSyncContext]:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    store = ProjectSyncStore(project_uuid)
    layout = store.layout_generation()
    layout.begin_cutover("t032-interactive")
    layout.publish_project_only("t032-interactive", verify_exact=lambda: True)
    record_project_opt_in(project_uuid, actor="operator:alice")
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, ?, 'account-1', 'teamspace-1', 4, 'admitted', '9', "
            "'private-teamspace:teamspace-1')",
            (project_uuid, SERVER),
        )
    return store, store.create_context()


def _admitted_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    envelopes: list[dict[str, Any]],
) -> tuple[ProjectSyncStore, ProjectSyncContext, HistoryDisclosureCapability]:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    store = ProjectSyncStore(PROJECT)
    with store.unit_of_work() as unit:
        for envelope in envelopes:
            assignment = allocate_capture_sequence(unit)
            unit.execute(
                "INSERT INTO journal_entries (entry_id, project_uuid, epoch_id, capture_sequence, payload_json) VALUES (?, ?, ?, ?, ?)",
                (
                    envelope["event_id"],
                    PROJECT,
                    assignment.epoch_id,
                    assignment.capture_sequence,
                    json.dumps(envelope, sort_keys=True, separators=(",", ":")),
                ),
            )
    record_project_opt_in(PROJECT, actor="operator:alice")
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, ?, 'account-1', 'teamspace-1', 4, 'admitted', '9', "
            "'private-teamspace:teamspace-1')",
            (PROJECT, SERVER),
        )
    context = store.create_context()
    capability = confirm_history_disclosure(
        store,
        preview_sealed_history(store),
        actor="operator:alice",
        idempotency_key="history-upload-1",
        context=context,
    )
    return store, context, capability


@pytest.fixture(autouse=True)
def _reset_adapter() -> Iterator[None]:
    reset_dossier_emitter()
    yield
    reset_dossier_emitter()


def test_history_preflight_and_upload_each_use_exact_project_attempts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelopes = [_envelope("old-1"), _envelope("old-2")]
    store, context, capability = _admitted_history(tmp_path, monkeypatch, envelopes)
    ingress = _RecordingIngress(store)
    receiver = TeamspaceReceiver(
        resolved_server_url=SERVER,
        auth_token="token",
        poster=ingress,
    )

    report = run_import_upload(
        envelopes,
        receiver=receiver,
        server_url=SERVER,
        auth_token="token",
        poster=ingress,
        project_context=context,
        target=_target(),
        history_capability=capability,
    )

    assert report.success == 2
    assert [url for url, _body in ingress.requests] == [
        f"{SERVER}/api/v1/events/preflight/",
        f"{SERVER}/api/v1/events/batch/",
    ]
    with store.unit_of_work() as unit:
        attempts = unit.execute(
            "SELECT state, payload_reference FROM delivery_attempts WHERE project_uuid = ? ORDER BY attempt_id",
            (PROJECT,),
        ).fetchall()
    assert len(attempts) == 4
    metadata = [json.loads(str(row[1])) for row in attempts]
    assert {item["write_kind"] for item in metadata} == {
        "history_preflight",
        "history_upload",
    }
    assert {item["native_identity"] for item in metadata} == {"old-1", "old-2"}
    assert {str(row[0]) for row in attempts} == {"succeeded"}

    rerun = run_import_upload(
        envelopes,
        receiver=receiver,
        server_url=SERVER,
        auth_token="token",
        poster=ingress,
        project_context=context,
        target=_target(),
        history_capability=capability,
    )
    assert rerun.success == 2
    assert not rerun.refused
    assert len(ingress.requests) == 2
    with store.unit_of_work() as unit:
        assert unit.execute(
            "SELECT COUNT(*) FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone() == (4,)


def test_history_upload_only_terminal_rerun_is_zero_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelopes = [_envelope("old-1")]
    store, context, capability = _admitted_history(tmp_path, monkeypatch, envelopes)
    ingress = _RecordingIngress(store)
    receiver = TeamspaceReceiver(
        resolved_server_url=SERVER,
        auth_token="token",
        poster=ingress,
    )

    first = upload_envelopes(
        envelopes,
        receiver=receiver,
        project_context=context,
        target=_target(),
        history_capability=capability,
    )
    rerun = upload_envelopes(
        envelopes,
        receiver=receiver,
        project_context=context,
        target=_target(),
        history_capability=capability,
    )

    assert first.success == rerun.success == 1
    assert len(ingress.requests) == 1


@pytest.mark.parametrize(
    ("outcome", "expected_counter"),
    [
        (DeliveryOutcome.DUPLICATE, "duplicate"),
        (DeliveryOutcome.TERMINAL_FAILED, "rejected"),
    ],
)
def test_history_upload_terminal_duplicate_or_refusal_rerun_is_zero_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: DeliveryOutcome,
    expected_counter: str,
) -> None:
    envelopes = [_envelope("old-1")]
    _store, context, capability = _admitted_history(tmp_path, monkeypatch, envelopes)

    class TerminalReceiver:
        endpoint_url = SERVER

        def __init__(self) -> None:
            self.calls = 0

        def deliver(self, batch: Any) -> list[DeliveryResult]:
            self.calls += 1
            event = next(iter(batch))
            return [
                DeliveryResult(
                    event_id=event.event_id,
                    outcome=outcome,
                    error=("project is not admitted" if outcome is DeliveryOutcome.TERMINAL_FAILED else None),
                    effect_certainty=DeliveryEffectCertainty.TERMINAL,
                    raw=({"code": "project_not_admitted"} if outcome is DeliveryOutcome.TERMINAL_FAILED else None),
                )
            ]

    receiver = TerminalReceiver()
    first = upload_envelopes(
        envelopes,
        receiver=receiver,
        project_context=context,
        target=_target(),
        history_capability=capability,
    )
    rerun = upload_envelopes(
        envelopes,
        receiver=receiver,
        project_context=context,
        target=_target(),
        history_capability=capability,
    )

    assert getattr(first, expected_counter) == 1
    assert receiver.calls == 1
    if outcome is DeliveryOutcome.DUPLICATE:
        assert rerun.duplicate == 1
        assert not rerun.refused
    else:
        assert rerun.rejected == 1
        assert rerun.refused
        assert "project_not_admitted" in rerun.rejected_samples[0]


def test_later_preflight_rejection_rerun_replays_prefix_then_refuses_without_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelopes = [_envelope("old-1"), _envelope("old-2")]
    store, context, capability = _admitted_history(tmp_path, monkeypatch, envelopes)
    calls: list[str] = []

    def reject_second(
        url: str,
        *,
        data: bytes,
        headers: dict[str, str],
        timeout: float,
    ) -> _Response:
        del timeout
        calls.append(url)
        event_id = json.loads(data)["events"][0]["event_id"]
        if event_id == "old-2":
            return _Response(
                {
                    "error": "project is not admitted",
                    "details": [
                        {
                            "event_id": "old-2",
                            "error_category": "project_not_admitted",
                        }
                    ],
                },
                status_code=400,
            )
        return _Response({"results": [{"event_id": event_id, "status": "success"}]})

    receiver = TeamspaceReceiver(
        resolved_server_url=SERVER,
        auth_token="token",
        poster=reject_second,
    )
    with pytest.raises(PreflightRejected, match="project is not admitted"):
        run_import_upload(
            envelopes,
            receiver=receiver,
            server_url=SERVER,
            auth_token="token",
            poster=reject_second,
            chunk_size=1,
            project_context=context,
            target=_target(),
            history_capability=capability,
        )
    calls_after_first = list(calls)

    with pytest.raises(PreflightRejected, match="project_not_admitted"):
        run_import_upload(
            envelopes,
            receiver=receiver,
            server_url=SERVER,
            auth_token="token",
            poster=reject_second,
            chunk_size=1,
            project_context=context,
            target=_target(),
            history_capability=capability,
        )

    assert calls_after_first == [
        f"{SERVER}/api/v1/events/preflight/",
        f"{SERVER}/api/v1/events/preflight/",
    ]
    assert calls == calls_after_first


def test_structured_preflight_400_preserves_correlated_project_not_admitted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelopes = [_envelope("old-1"), _envelope("old-2")]
    store, context, capability = _admitted_history(tmp_path, monkeypatch, envelopes)

    def structured_refusal(
        url: str,
        *,
        data: bytes,
        headers: dict[str, str],
        timeout: float,
    ) -> _Response:
        del url, data, headers, timeout
        return _Response(
            {
                "error": "batch validation failed",
                "details": [
                    {
                        "event_id": "old-2",
                        "reason": "project is not admitted",
                        "code": "project_not_admitted",
                    }
                ],
            },
            status_code=400,
        )

    receiver = TeamspaceReceiver(
        resolved_server_url=SERVER,
        auth_token="token",
        poster=structured_refusal,
    )
    with pytest.raises(PreflightRejected, match="batch validation failed"):
        run_import_upload(
            envelopes,
            receiver=receiver,
            server_url=SERVER,
            auth_token="token",
            poster=structured_refusal,
            project_context=context,
            target=_target(),
            history_capability=capability,
        )

    with store.unit_of_work() as unit:
        rows = unit.execute(
            "SELECT delivery_attempts.payload_reference, delivery_attempts.state, "
            "delivery_results.terminal_refusal_category "
            "FROM delivery_attempts JOIN delivery_results "
            "ON delivery_results.project_uuid = delivery_attempts.project_uuid "
            "AND delivery_results.attempt_id = delivery_attempts.attempt_id "
            "WHERE delivery_attempts.project_uuid = ?",
            (PROJECT,),
        ).fetchall()
    categories = {json.loads(str(reference))["native_identity"]: (str(state), str(category)) for reference, state, category in rows}
    assert categories == {
        "old-1": ("retryable_no_effect", "None"),
        "old-2": ("refused", "project_not_admitted"),
    }


@pytest.mark.parametrize("category_field", ["error_category", "category", "code"])
def test_structured_preflight_200_refusal_terminalizes_only_correlated_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    category_field: str,
) -> None:
    envelopes = [_envelope("old-1"), _envelope("old-2")]
    store, context, capability = _admitted_history(tmp_path, monkeypatch, envelopes)
    calls = 0

    def mixed_response(
        url: str,
        *,
        data: bytes,
        headers: dict[str, str],
        timeout: float,
    ) -> _Response:
        del url, data, headers, timeout
        nonlocal calls
        calls += 1
        return _Response(
            {
                "results": [
                    {"event_id": "old-1", "status": "success"},
                    {
                        "event_id": "old-2",
                        "status": "rejected",
                        category_field: "project_not_admitted",
                        "retryable": False,
                    },
                ]
            }
        )

    receiver = TeamspaceReceiver(
        resolved_server_url=SERVER,
        auth_token="token",
        poster=mixed_response,
    )
    with pytest.raises(PreflightRejected, match="project_not_admitted"):
        run_import_upload(
            envelopes,
            receiver=receiver,
            server_url=SERVER,
            auth_token="token",
            poster=mixed_response,
            project_context=context,
            target=_target(),
            history_capability=capability,
        )

    with store.unit_of_work() as unit:
        rows = unit.execute(
            "SELECT delivery_attempts.payload_reference, delivery_attempts.state, "
            "delivery_results.terminal_refusal_category "
            "FROM delivery_attempts JOIN delivery_results "
            "ON delivery_results.project_uuid = delivery_attempts.project_uuid "
            "AND delivery_results.attempt_id = delivery_attempts.attempt_id "
            "WHERE delivery_attempts.project_uuid = ?",
            (PROJECT,),
        ).fetchall()
    categories = {json.loads(str(reference))["native_identity"]: (str(state), str(category)) for reference, state, category in rows}
    assert categories == {
        "old-1": ("succeeded", "None"),
        "old-2": ("refused", "project_not_admitted"),
    }
    assert calls == 1


def test_history_content_or_cross_project_target_cannot_reuse_confirmed_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelopes = [_envelope("old-1")]
    store, context, capability = _admitted_history(tmp_path, monkeypatch, envelopes)
    ingress = _RecordingIngress(store)
    receiver = TeamspaceReceiver(
        resolved_server_url=SERVER,
        auth_token="token",
        poster=ingress,
    )
    changed = [_envelope("old-1")]
    changed[0]["payload"]["mission_slug"] = "different-engagement"

    changed_report = run_import_upload(
        changed,
        receiver=receiver,
        server_url=SERVER,
        auth_token="token",
        poster=ingress,
        project_context=context,
        target=_target(),
        history_capability=capability,
    )
    cross_target_report = run_import_upload(
        envelopes,
        receiver=receiver,
        server_url=SERVER,
        auth_token="token",
        poster=ingress,
        project_context=context,
        target=_target(OTHER),
        history_capability=capability,
    )

    assert changed_report.refused and cross_target_report.refused
    assert ingress.requests == []
    with store.unit_of_work() as unit:
        assert unit.execute(
            "SELECT COUNT(*) FROM journal_entries WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone() == (1,)


def test_preflight_transport_uncertainty_keeps_the_same_attempt_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelopes = [_envelope("old-1")]
    store, context, capability = _admitted_history(tmp_path, monkeypatch, envelopes)
    calls: list[str] = []

    def raising_poster(
        url: str,
        *,
        data: bytes,
        headers: dict[str, str],
        timeout: float,
    ) -> _Response:
        del data, headers, timeout
        calls.append(url)
        raise requests.ConnectionError("connection reset after disclosure")

    receiver = TeamspaceReceiver(
        resolved_server_url=SERVER,
        auth_token="token",
        poster=raising_poster,
    )

    with pytest.raises(PreflightRejected, match="transport failed"):
        run_import_upload(
            envelopes,
            receiver=receiver,
            server_url=SERVER,
            auth_token="token",
            poster=raising_poster,
            project_context=context,
            target=_target(),
            history_capability=capability,
        )

    with store.unit_of_work() as unit:
        attempts = unit.execute(
            "SELECT state, payload_reference FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchall()
    assert len(attempts) == 1
    assert str(attempts[0][0]) == "unknown"
    assert json.loads(str(attempts[0][1]))["native_identity"] == "old-1"

    rerun = run_import_upload(
        envelopes,
        receiver=receiver,
        server_url=SERVER,
        auth_token="token",
        poster=raising_poster,
        project_context=context,
        target=_target(),
        history_capability=capability,
    )
    assert rerun.refused
    assert calls == [f"{SERVER}/api/v1/events/preflight/"]


def test_history_rerun_refuses_mixed_terminal_and_absent_upload_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelopes = [_envelope("old-1"), _envelope("old-2")]
    store, context, capability = _admitted_history(tmp_path, monkeypatch, envelopes)
    ingress = _RecordingIngress(store)
    receiver = TeamspaceReceiver(
        resolved_server_url=SERVER,
        auth_token="token",
        poster=ingress,
    )
    assert (
        run_import_upload(
            envelopes,
            receiver=receiver,
            server_url=SERVER,
            auth_token="token",
            poster=ingress,
            project_context=context,
            target=_target(),
            history_capability=capability,
        ).success
        == 2
    )
    with store.unit_of_work() as unit:
        rows = unit.execute(
            "SELECT attempt_id, payload_reference FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchall()
        upload_old_2 = next(
            str(attempt_id)
            for attempt_id, reference in rows
            if json.loads(str(reference))["write_kind"] == "history_upload" and json.loads(str(reference))["native_identity"] == "old-2"
        )
        unit.execute(
            "DELETE FROM delivery_results WHERE project_uuid = ? AND attempt_id = ?",
            (PROJECT, upload_old_2),
        )
        unit.execute(
            "DELETE FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (PROJECT, upload_old_2),
        )
    calls_before = list(ingress.requests)

    rerun = run_import_upload(
        envelopes,
        receiver=receiver,
        server_url=SERVER,
        auth_token="token",
        poster=ingress,
        project_context=context,
        target=_target(),
        history_capability=capability,
    )

    assert rerun.refused
    assert "mixed or nonterminal" in rerun.rejected_samples[0]
    assert ingress.requests == calls_before


def test_history_rerun_refuses_corrupt_terminal_metadata_without_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelopes = [_envelope("old-1")]
    store, context, capability = _admitted_history(tmp_path, monkeypatch, envelopes)
    ingress = _RecordingIngress(store)
    receiver = TeamspaceReceiver(
        resolved_server_url=SERVER,
        auth_token="token",
        poster=ingress,
    )
    assert (
        run_import_upload(
            envelopes,
            receiver=receiver,
            server_url=SERVER,
            auth_token="token",
            poster=ingress,
            project_context=context,
            target=_target(),
            history_capability=capability,
        ).success
        == 1
    )
    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE delivery_attempts SET payload_reference = '{}' WHERE project_uuid = ? AND attempt_id LIKE 'history_upload:%'",
            (PROJECT,),
        )
    calls_before = list(ingress.requests)

    rerun = run_import_upload(
        envelopes,
        receiver=receiver,
        server_url=SERVER,
        auth_token="token",
        poster=ingress,
        project_context=context,
        target=_target(),
        history_capability=capability,
    )

    assert rerun.refused
    assert "terminal result projection refused" in rerun.rejected_samples[0]
    assert ingress.requests == calls_before


def test_history_rerun_refuses_terminal_attempt_with_old_admission_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelopes = [_envelope("old-1")]
    store, context, capability = _admitted_history(tmp_path, monkeypatch, envelopes)
    ingress = _RecordingIngress(store)
    receiver = TeamspaceReceiver(
        resolved_server_url=SERVER,
        auth_token="token",
        poster=ingress,
    )
    assert (
        run_import_upload(
            envelopes,
            receiver=receiver,
            server_url=SERVER,
            auth_token="token",
            poster=ingress,
            project_context=context,
            target=_target(),
            history_capability=capability,
        ).success
        == 1
    )
    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE delivery_attempts SET admission_generation = '8' WHERE project_uuid = ? AND attempt_id LIKE 'history_upload:%'",
            (PROJECT,),
        )
    calls_before = list(ingress.requests)

    rerun = run_import_upload(
        envelopes,
        receiver=receiver,
        server_url=SERVER,
        auth_token="token",
        poster=ingress,
        project_context=context,
        target=_target(),
        history_capability=capability,
    )

    assert rerun.refused
    assert "attempt authority" in rerun.rejected_samples[0]
    assert ingress.requests == calls_before


def test_preflight_413_is_retryable_no_effect_not_terminal_refusal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelopes = [_envelope("old-1")]
    store, context, capability = _admitted_history(tmp_path, monkeypatch, envelopes)
    requests_seen: list[str] = []

    def too_large(
        url: str,
        *,
        data: bytes,
        headers: dict[str, str],
        timeout: float,
    ) -> _Response:
        del data, headers, timeout
        requests_seen.append(url)
        return _Response(
            {"error": "request too large"},
            status_code=413,
        )

    receiver = TeamspaceReceiver(
        resolved_server_url=SERVER,
        auth_token="token",
        poster=too_large,
    )
    with pytest.raises(PreflightRejected, match="request too large"):
        run_import_upload(
            envelopes,
            receiver=receiver,
            server_url=SERVER,
            auth_token="token",
            poster=too_large,
            project_context=context,
            target=_target(),
            history_capability=capability,
        )

    assert requests_seen == [f"{SERVER}/api/v1/events/preflight/"]
    with store.unit_of_work() as unit:
        attempt = unit.execute(
            "SELECT state FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone()
    assert attempt == ("retryable_no_effect",)


def test_preflight_413_splits_and_restarts_the_same_attempt_identities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelopes = [_envelope("old-1"), _envelope("old-2")]
    store, context, capability = _admitted_history(tmp_path, monkeypatch, envelopes)
    request_sizes: list[int] = []

    def split_ingress(
        url: str,
        *,
        data: bytes,
        headers: dict[str, str],
        timeout: float,
    ) -> _Response:
        del timeout
        events = json.loads(gzip.decompress(data).decode("utf-8"))["events"] if headers.get("Content-Encoding") == "gzip" else json.loads(data)["events"]
        request_sizes.append(len(events))
        if url.endswith("/preflight/") and len(events) > 1:
            return _Response(
                {"error": "request too large"},
                status_code=413,
            )
        if url.endswith("/preflight/"):
            return _Response({"results": [{"event_id": event["event_id"], "status": "success"} for event in events]})
        return _Response({"results": [{"event_id": event["event_id"], "status": "success"} for event in events]})

    receiver = TeamspaceReceiver(
        resolved_server_url=SERVER,
        auth_token="token",
        poster=split_ingress,
    )
    report = run_import_upload(
        envelopes,
        receiver=receiver,
        server_url=SERVER,
        auth_token="token",
        poster=split_ingress,
        project_context=context,
        target=_target(),
        history_capability=capability,
    )

    assert report.success == 2
    assert request_sizes == [2, 1, 1, 2]
    with store.unit_of_work() as unit:
        rows = unit.execute(
            "SELECT state, payload_reference FROM delivery_attempts WHERE project_uuid = ? ORDER BY attempt_id",
            (PROJECT,),
        ).fetchall()
    assert len(rows) == 4
    assert {str(row[0]) for row in rows} == {"succeeded"}
    assert {json.loads(str(row[1]))["native_identity"] for row in rows} == {"old-1", "old-2"}


@pytest.mark.parametrize(
    ("delivery_outcome", "certainty", "durable_outcome"),
    [
        (
            DeliveryOutcome.REJECTED,
            DeliveryEffectCertainty.KNOWN_NO_EFFECT,
            "retryable_no_effect",
        ),
        (
            DeliveryOutcome.PENDING,
            DeliveryEffectCertainty.ACCEPTED_PENDING,
            "pending",
        ),
        (
            DeliveryOutcome.REJECTED,
            DeliveryEffectCertainty.POSSIBLY_EFFECTIVE,
            "unknown",
        ),
        (
            DeliveryOutcome.PENDING,
            DeliveryEffectCertainty.POSSIBLY_EFFECTIVE,
            "unknown",
        ),
    ],
)
def test_history_delivery_classification_requires_typed_effect_certainty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    delivery_outcome: DeliveryOutcome,
    certainty: DeliveryEffectCertainty,
    durable_outcome: str,
) -> None:
    envelopes = [_envelope("old-1")]
    _store, context, capability = _admitted_history(tmp_path, monkeypatch, envelopes)
    disclosures = _history_disclosures(
        envelopes,
        sink="history_upload",
        project_context=context,
        target=_target(),
        history_capability=capability,
    )
    result = DeliveryResult(
        event_id="old-1",
        outcome=delivery_outcome,
        effect_certainty=certainty,
    )

    classified = _delivery_classification([result], disclosures)

    assert classified == {disclosures[0].attempt_id: (durable_outcome, None)}


def test_dossier_adapter_requires_and_preserves_store_minted_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelopes = [_envelope("old-1")]
    store, _context, _capability = _admitted_history(tmp_path, monkeypatch, envelopes)
    seen: list[ProjectSyncContext] = []

    def emitter(**kwargs: Any) -> dict[str, Any]:
        seen.append(kwargs.pop("project_context"))
        return dict(kwargs)

    register_dossier_emitter(emitter)
    payload = {"namespace": {"project_uuid": PROJECT}}

    assert (
        fire_dossier_event(
            event_type="MissionDossierSnapshotComputed",
            aggregate_id="mission:snapshot",
            aggregate_type="MissionDossier",
            payload=payload,
        )
        is None
    )
    layout = store.layout_generation()
    with store.unit_of_work() as unit:
        context = store.create_context()
        result = fire_dossier_event(
            event_type="MissionDossierSnapshotComputed",
            aggregate_id="mission:snapshot",
            aggregate_type="MissionDossier",
            payload=payload,
            project_context=context,
            project_unit=unit,
            project_layout=layout,
        )

    assert result is not None
    assert seen == [context]


def test_dossier_explicit_context_captures_locally_without_ambient_or_remote_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT)
    layout = store.layout_generation()
    layout.begin_cutover("t033-dossier-capture")
    layout.publish_project_only(
        "t033-dossier-capture",
        verify_exact=lambda: True,
    )
    emitter = EventEmitter(queue=object())  # type: ignore[arg-type]

    def ambient_forbidden(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        raise AssertionError("explicit dossier capture consulted ambient/remote authority")

    monkeypatch.setattr(emitter, "_get_identity", ambient_forbidden)
    monkeypatch.setattr(emitter, "_get_team_slug", ambient_forbidden)
    monkeypatch.setattr(emitter, "_get_git_metadata", ambient_forbidden)
    monkeypatch.setattr(emitter, "_route_event", ambient_forbidden)
    register_dossier_emitter(emitter._emit)

    with store.unit_of_work() as unit:
        context = store.create_context()
        result = emit_snapshot_computed(
            mission_slug="private-engagement",
            parity_hash_sha256="a" * 64,
            total_artifacts=1,
            required_artifacts=1,
            required_present=1,
            required_missing=0,
            optional_artifacts=0,
            optional_present=0,
            completeness_status="complete",
            snapshot_id="snapshot-1",
            namespace={
                "project_uuid": PROJECT,
                "mission_slug": "private-engagement",
                "target_branch": "develop",
                "mission_type": "software-dev",
                "manifest_version": "1",
            },
            project_context=context,
            project_unit=unit,
            project_layout=layout,
        )

    assert result is not None
    assert result["project_uuid"] == PROJECT
    with store.unit_of_work() as unit:
        journal_rows = unit.execute(
            "SELECT project_uuid, payload_json FROM journal_entries WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchall()
        outbox_count = unit.execute(
            "SELECT COUNT(*) FROM outbox_tasks WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone()
    assert len(journal_rows) == 1
    assert str(journal_rows[0][0]) == PROJECT
    assert "private-engagement" in str(journal_rows[0][1])
    assert outbox_count == (1,)


def test_dossier_rejects_mismatched_unit_before_store_creation_or_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    expected_store = ProjectSyncStore(PROJECT)
    wrong_store = ProjectSyncStore(OTHER)
    expected_layout = expected_store.layout_generation()
    emitter = EventEmitter(queue=object())  # type: ignore[arg-type]

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        raise AssertionError("mismatched authority reached store creation or remote routing")

    monkeypatch.setattr(emitter, "_route_event", forbidden)
    register_dossier_emitter(emitter._emit)
    with expected_store.unit_of_work():
        expected_context = expected_store.create_context()

    # From this point the rejection must use only the supplied capabilities. A
    # path/UUID-derived store reopen would run this sentinel before it could
    # discover that the active unit belongs to another aggregate.
    monkeypatch.setattr(ProjectSyncStore, "__init__", forbidden)
    with wrong_store.unit_of_work() as wrong_unit:
        result = fire_dossier_event(
            event_type="MissionDossierSnapshotComputed",
            aggregate_id="mission:snapshot",
            aggregate_type="MissionDossier",
            payload={"namespace": {"project_uuid": PROJECT}},
            project_context=expected_context,
            project_unit=wrong_unit,
            project_layout=expected_layout,
        )

    assert result is None
    with expected_store.unit_of_work() as expected_unit:
        assert expected_unit.execute(
            "SELECT COUNT(*) FROM journal_entries WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone() == (0,)
    with wrong_store.unit_of_work() as wrong_unit:
        assert wrong_unit.execute(
            "SELECT COUNT(*) FROM journal_entries WHERE project_uuid = ?",
            (OTHER,),
        ).fetchone() == (0,)


def test_body_capture_rejects_same_uuid_layout_from_another_runtime_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_a = tmp_path / "runtime-a"
    runtime_b = tmp_path / "runtime-b"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime_a))
    store = ProjectSyncStore(PROJECT)
    layout = store.layout_generation()
    layout.begin_cutover("t033-body-root")
    layout.publish_project_only("t033-body-root", verify_exact=lambda: True)

    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime_b))
    foreign_layout = ProjectSyncStore(PROJECT).layout_generation()
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime_a))
    namespace = NamespaceRef(
        project_uuid=PROJECT,
        mission_slug="private-engagement",
        target_branch="develop",
        mission_type="software-dev",
        manifest_version="1",
    )
    artifact = ArtifactRef(
        artifact_key="input.spec",
        artifact_class="input",
        relative_path="spec.md",
        content_hash_sha256="a" * 64,
        size_bytes=10,
        required_status="required",
    )

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        raise AssertionError("foreign layout reached artifact read or body write")

    monkeypatch.setattr(
        "specify_cli.sync.body_upload._read_and_rehash",
        forbidden,
    )
    monkeypatch.setattr(OfflineBodyUploadQueue, "enqueue", forbidden)
    with store.unit_of_work() as unit:
        context = store.create_context_from_unit(unit)
        queue = OfflineBodyUploadQueue(unit, layout)
        with pytest.raises(ValueError, match="another runtime root"):
            prepare_body_uploads(
                [artifact],
                namespace,
                queue,
                tmp_path,
                project_context=context,
                project_unit=unit,
                project_layout=foreign_layout,
            )
        assert unit.execute(
            "SELECT COUNT(*) FROM body_upload_tasks WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone() == (0,)


def test_explicit_body_capture_does_not_require_an_egress_grant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    content = "# Private mission\n"
    (tmp_path / "spec.md").write_text(content, encoding="utf-8")
    artifact = ArtifactRef(
        artifact_key="input.spec",
        artifact_class="input",
        relative_path="spec.md",
        content_hash_sha256=hashlib.sha256(content.encode()).hexdigest(),  # noqa: TID251
        size_bytes=len(content.encode()),
        required_status="required",
    )
    namespace = NamespaceRef(
        project_uuid=PROJECT,
        mission_slug="private-engagement",
        target_branch="develop",
        mission_type="software-dev",
        manifest_version="1",
    )
    store = ProjectSyncStore(PROJECT)
    layout = store.layout_generation()
    layout.begin_cutover("t033-body-capture")
    layout.publish_project_only("t033-body-capture", verify_exact=lambda: True)

    with store.unit_of_work() as unit:
        context = store.create_context_from_unit(unit)
        assert context.consent_state is None
        queue = OfflineBodyUploadQueue(unit, layout)
        outcomes = prepare_body_uploads(
            [artifact],
            namespace,
            queue,
            tmp_path,
            project_context=context,
            project_unit=unit,
            project_layout=layout,
        )
        assert outcomes[0].status is UploadStatus.QUEUED
        row = unit.execute(
            "SELECT epoch_id, state FROM body_upload_tasks WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone()
        assert row is not None
        epoch = unit.execute(
            "SELECT state FROM consent_epochs WHERE project_uuid = ? AND epoch_id = ?",
            (PROJECT, row[0]),
        ).fetchone()
        assert epoch == ("capture_only",)


class _AckingWebSocket:
    def __init__(self, client: WebSocketClient, response: Any) -> None:
        self.client = client
        self.response = response
        self.frames: list[dict[str, Any]] = []
        self.raw_frames: list[str] = []

    async def send(self, raw: str) -> None:
        self.raw_frames.append(raw)
        frame = json.loads(raw)
        self.frames.append(frame)
        response = self.response(frame) if callable(self.response) else self.response
        if response is not None:
            await self.client._handle_message(response)


def _event_frame(event_id: str = "01KZT032EVENTACK0000000001") -> dict[str, Any]:
    event: dict[str, Any] = build_teamspace_envelope(
        event_id=event_id,
        event_type="WPStatusChanged",
        aggregate_id="WP01",
        aggregate_type="WorkPackage",
        build_id="build-1",
        payload={
            "wp_id": "WP01",
            "from_lane": "planned",
            "to_lane": "in_progress",
            "actor": "agent",
        },
        node_id="node-1",
        lamport_clock=1,
        causation_id=None,
        correlation_id=event_id,
        timestamp="2026-08-11T12:00:00+00:00",
        project_uuid=PROJECT,
        project_slug="private-engagement",
        repo_slug="private/project",
    ).model_dump()
    event.update(
        team_slug="teamspace-1",
        git_branch="develop",
        head_commit_sha="a" * 40,
        drain_blocked_reason=None,
    )
    return event


@pytest.mark.parametrize(
    ("status", "durable_state", "durable_outcome"),
    [
        ("accepted", "succeeded", "delivered"),
        ("duplicate", "succeeded", "duplicate"),
        ("rejected", "refused", "refused"),
    ],
)
def test_websocket_event_ack_is_exact_proof_bearing_and_durable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    durable_state: str,
    durable_outcome: str,
) -> None:
    store, _context = _admitted_project(tmp_path, monkeypatch)
    event = _event_frame()
    layout = store.layout_generation()
    with store.unit_of_work() as unit:
        OfflineQueue(unit, layout).queue_event(event)

    client = WebSocketClient()
    client.connected = True

    def response(frame: dict[str, Any]) -> dict[str, Any]:
        if status == "rejected":
            return {
                "type": "error",
                "event_id": frame["event_id"],
                "status": "rejected",
                "error_category": "project_not_admitted",
                "retryable": False,
            }
        return {"type": "ack", "event_id": frame["event_id"], "status": status}

    websocket = _AckingWebSocket(client, response)
    client.ws = websocket  # type: ignore[assignment]
    if status == "rejected":
        with pytest.raises(Exception, match="project_not_admitted"):
            asyncio.run(client.send_event(event))
    else:
        assert asyncio.run(client.send_event(event)) is True

    assert len(websocket.frames) == 1
    wire = websocket.frames[0]
    assert wire["project_uuid"] == PROJECT
    assert wire["type"] == "event"
    assert wire["admission_generation"] == 9
    assert wire["binding_audience"] == "private-teamspace:teamspace-1"
    assert wire["spec_kitty_delivery_identity"] == event["event_id"]
    with store.unit_of_work() as unit:
        attempt = unit.execute(
            "SELECT state, payload_reference, payload_hash FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone()
        result = unit.execute(
            "SELECT outcome, terminal_refusal_category FROM delivery_results WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone()
    assert attempt is not None and attempt[0] == durable_state
    metadata = json.loads(str(attempt[1]))
    assert metadata["write_kind"] == "event"
    assert metadata["native_identity"] == wire["spec_kitty_delivery_identity"]
    assert (
        attempt[2]
        == "sha256:"
        + hashlib.sha256(  # noqa: TID251 - exact transport-byte assertion
            websocket.raw_frames[0].encode("utf-8")
        ).hexdigest()
    )
    assert result == (
        durable_outcome,
        "project_not_admitted" if status == "rejected" else None,
    )


def test_websocket_event_missing_ack_stays_unknown_and_is_not_resent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _context = _admitted_project(tmp_path, monkeypatch)
    event = _event_frame()
    client = WebSocketClient()
    client.connected = True
    websocket = _AckingWebSocket(client, None)
    client.ws = websocket  # type: ignore[assignment]
    monkeypatch.setattr(client, "ACK_TIMEOUT_SECONDS", 0.01)

    with pytest.raises(Exception, match="acknowledgement"):
        asyncio.run(client.send_event(event))
    with pytest.raises(Exception, match="recovery"):
        asyncio.run(client.send_event(event))

    assert len(websocket.frames) == 1
    with store.unit_of_work() as unit:
        assert unit.execute(
            "SELECT state FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone() == ("unknown",)


def test_websocket_event_cross_correlated_ack_stays_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _context = _admitted_project(tmp_path, monkeypatch)
    event = _event_frame()
    client = WebSocketClient()
    client.connected = True
    websocket = _AckingWebSocket(
        client,
        {"type": "ack", "event_id": "foreign-event", "status": "accepted"},
    )
    client.ws = websocket  # type: ignore[assignment]
    monkeypatch.setattr(client, "ACK_TIMEOUT_SECONDS", 0.01)

    with pytest.raises(Exception, match="acknowledgement"):
        asyncio.run(client.send_event(event))

    assert len(websocket.frames) == 1
    with store.unit_of_work() as unit:
        assert unit.execute(
            "SELECT state FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone() == ("unknown",)


def test_websocket_event_revocation_is_zero_io_at_final_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _context = _admitted_project(tmp_path, monkeypatch)
    from specify_cli.delivery import consent_gate

    original_execute = consent_gate.execute_project_transport_disclosure

    def revoke_at_final_gate(*args: Any, **kwargs: Any) -> Any:
        record_project_opt_out(PROJECT, actor="operator:alice")
        return original_execute(*args, **kwargs)

    monkeypatch.setattr(
        consent_gate,
        "execute_project_transport_disclosure",
        revoke_at_final_gate,
    )
    client = WebSocketClient()
    client.connected = True
    websocket = _AckingWebSocket(client, None)
    client.ws = websocket  # type: ignore[assignment]

    with pytest.raises(Exception, match="project_not_admitted"):
        asyncio.run(client.send_event(_event_frame()))

    assert websocket.frames == []
    with store.unit_of_work() as unit:
        assert unit.execute(
            "SELECT COUNT(*) FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone() == (0,)


@pytest.mark.parametrize(
    ("committed_at", "received_at"),
    [
        ("2026-08-11T12:00:00Z", "2026-08-11T12:00:01Z"),
        ("2026-08-11T14:00:00+02:00", "2026-08-11T14:00:01+02:00"),
        ("2026-08-11t12:00:00+00:00", "2026-08-11t12:00:01+00:00"),
        ("2026-08-11T12:00:00z", "2026-08-11T12:00:01z"),
        ("2026-08-11t12:00:00z", "2026-08-11t12:00:01z"),
    ],
)
def test_local_commit_ack_requires_the_full_authority_tuple_before_removal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    committed_at: str,
    received_at: str,
) -> None:
    store, _context = _admitted_project(tmp_path, monkeypatch)
    repo_root = tmp_path / "repo"
    (repo_root / ".kittify").mkdir(parents=True)
    (repo_root / ".kittify" / "config.yaml").write_text(
        f"project:\n  uuid: {PROJECT}\n  slug: private-engagement\n",
        encoding="utf-8",
    )
    from specify_cli.sync.local_commit import SyncState, load_sync_state, save_sync_state

    pending = {
        "type": "LocalCommit",
        "git_hash": "a" * 40,
        "mission_id": "01KZT032MISSION00000000001",
        "build_id": "build-1",
        "project_uuid": PROJECT,
        "changed_files": ["kitty-specs/private-engagement/spec.md"],
        "committed_at": committed_at,
    }
    foreign = {**pending, "project_uuid": OTHER, "build_id": "build-2"}
    save_sync_state(
        repo_root,
        SyncState(pending_local_commits=[pending, foreign]),
    )

    client = WebSocketClient(repo_root=repo_root)
    client.connected = True

    def response(frame: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "LocalCommitAck",
            "git_hash": frame["git_hash"],
            "build_id": frame["build_id"],
            "project_uuid": frame["project_uuid"],
            "admission_generation": frame["admission_generation"],
            "binding_audience": frame["binding_audience"],
            "status": "accepted",
            "received_at": received_at,
        }

    websocket = _AckingWebSocket(client, response)
    client.ws = websocket  # type: ignore[assignment]
    assert asyncio.run(client.send_local_commit(pending)) is True

    state = load_sync_state(repo_root)
    assert state.pending_local_commits == [foreign]
    assert state.last_saas_confirmed_hash == "a" * 40
    assert websocket.frames[0]["project_uuid"] == PROJECT
    assert websocket.frames[0]["admission_generation"] == 9
    assert websocket.frames[0]["binding_audience"] == "private-teamspace:teamspace-1"
    assert websocket.frames[0]["committed_at"] == committed_at
    with store.unit_of_work() as unit:
        assert unit.execute(
            "SELECT state FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone() == ("succeeded",)


@pytest.mark.parametrize(
    "received_at",
    [
        "2026-08-11T12:00:01",
        "2026-08-11 12:00:01+00:00",
        "2026-02-30T12:00:01Z",
    ],
)
def test_invalid_local_commit_ack_time_stays_unknown_and_retains_queue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    received_at: str,
) -> None:
    store, _context = _admitted_project(tmp_path, monkeypatch)
    repo_root = tmp_path / "repo"
    pending = {
        "type": "LocalCommit",
        "git_hash": "b" * 40,
        "mission_id": "01KZT032MISSION00000000001",
        "build_id": "build-invalid-ack-time",
        "project_uuid": PROJECT,
        "changed_files": ["kitty-specs/private-engagement/spec.md"],
        "committed_at": "2026-08-11T12:00:00Z",
    }
    from specify_cli.sync.local_commit import SyncState, load_sync_state, save_sync_state

    save_sync_state(repo_root, SyncState(pending_local_commits=[pending]))
    client = WebSocketClient(repo_root=repo_root)
    client.connected = True

    def response(frame: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "LocalCommitAck",
            "git_hash": frame["git_hash"],
            "build_id": frame["build_id"],
            "project_uuid": frame["project_uuid"],
            "admission_generation": frame["admission_generation"],
            "binding_audience": frame["binding_audience"],
            "status": "accepted",
            "received_at": received_at,
        }

    websocket = _AckingWebSocket(client, response)
    client.ws = websocket  # type: ignore[assignment]

    with pytest.raises(Exception, match="result correlation failed"):
        asyncio.run(client.send_local_commit(pending))

    assert len(websocket.frames) == 1
    assert load_sync_state(repo_root).pending_local_commits == [pending]
    with store.unit_of_work() as unit:
        assert unit.execute(
            "SELECT state FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone() == ("unknown",)


def test_local_commit_project_not_admitted_is_durable_and_terminalized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _context = _admitted_project(tmp_path, monkeypatch)
    repo_root = tmp_path / "repo"
    pending = {
        "type": "LocalCommit",
        "git_hash": "c" * 40,
        "mission_id": "01KZT032MISSION00000000001",
        "build_id": "build-refused",
        "project_uuid": PROJECT,
        "changed_files": ["kitty-specs/private-engagement/spec.md"],
        "committed_at": "2026-08-11T12:00:00+00:00",
    }
    from specify_cli.sync.local_commit import SyncState, load_sync_state, save_sync_state

    save_sync_state(repo_root, SyncState(pending_local_commits=[pending]))
    client = WebSocketClient(repo_root=repo_root)
    client.connected = True

    def response(frame: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "LocalCommitAck",
            "git_hash": frame["git_hash"],
            "build_id": frame["build_id"],
            "project_uuid": frame["project_uuid"],
            "admission_generation": frame["admission_generation"],
            "binding_audience": frame["binding_audience"],
            "status": "rejected",
            "error_category": "project_not_admitted",
            "retryable": False,
        }

    websocket = _AckingWebSocket(client, response)
    client.ws = websocket  # type: ignore[assignment]
    assert asyncio.run(client.send_local_commit(pending)) is False

    assert load_sync_state(repo_root).pending_local_commits == []
    with store.unit_of_work() as unit:
        assert unit.execute(
            "SELECT state FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone() == ("refused",)
        assert unit.execute(
            "SELECT outcome, terminal_refusal_category FROM delivery_results WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone() == ("refused", "project_not_admitted")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda frame: {**frame, "type": "event"},
        lambda frame: {key: value for key, value in frame.items() if key != "mission_id"},
        lambda frame: {**frame, "changed_files": "kitty-specs/private/spec.md"},
        lambda frame: {**frame, "committed_at": "2026-08-11T12:00:00"},
        lambda frame: {**frame, "committed_at": "2026-08-11 12:00:00+00:00"},
        lambda frame: {**frame, "committed_at": "2026-02-30T12:00:00Z"},
    ],
)
def test_malformed_local_commit_is_rejected_before_attempt_or_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate: Any,
) -> None:
    store, _context = _admitted_project(tmp_path, monkeypatch)
    frame = mutate(
        {
            "type": "LocalCommit",
            "git_hash": "d" * 40,
            "mission_id": "01KZT032MISSION00000000001",
            "build_id": "build-malformed",
            "project_uuid": PROJECT,
            "changed_files": ["kitty-specs/private-engagement/spec.md"],
            "committed_at": "2026-08-11T12:00:00+00:00",
        }
    )
    client = WebSocketClient(repo_root=tmp_path)
    client.connected = True
    websocket = _AckingWebSocket(client, None)
    client.ws = websocket  # type: ignore[assignment]

    with pytest.raises(ValueError):
        asyncio.run(client.send_local_commit(frame))

    assert websocket.frames == []
    with store.unit_of_work() as unit:
        assert unit.execute(
            "SELECT COUNT(*) FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone() == (0,)


def test_http_event_success_reconciles_ws_outbox_without_a_frame(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, context = _admitted_project(tmp_path, monkeypatch)
    event = _event_frame("01KZT032HTTPTHENWS0000001")
    with store.unit_of_work() as unit:
        OfflineQueue(unit, store.layout_generation()).queue_event(event)

    from specify_cli.delivery.consent_gate import execute_project_transport_disclosure
    from specify_cli.delivery.dispatcher import prepare_event_transport

    prepared = prepare_event_transport(
        event,
        event_id=event["event_id"],
        project_uuid=PROJECT,
        context=context,
    )
    execute_project_transport_disclosure(
        prepared.disclosure,
        send=lambda: {
            "type": "ack",
            "event_id": event["event_id"],
            "status": "accepted",
        },
        classify=lambda _value: ("delivered", None),
    )
    with store.unit_of_work() as unit:
        queued_event = OfflineQueue(unit, store.layout_generation()).drain_queue()[0].event
    replay_prepared = prepare_event_transport(
        queued_event,
        event_id=event["event_id"],
        project_uuid=PROJECT,
        context=store.create_context(),
    )
    assert replay_prepared.wire_payload == prepared.wire_payload
    assert replay_prepared.disclosure.payload_hash == prepared.disclosure.payload_hash

    identity = ProjectIdentity(
        project_uuid=UUID(PROJECT),
        project_slug="private-engagement",
        node_id="node-1",
        build_id="build-1",
    )
    client = WebSocketClient(project_identity=identity)
    client.connected = True
    websocket = _AckingWebSocket(client, None)
    client.ws = websocket  # type: ignore[assignment]
    asyncio.run(client._flush_pending_project_events())

    assert websocket.frames == []
    with store.unit_of_work() as unit:
        assert OfflineQueue(unit, store.layout_generation()).drain_queue() == []


def test_local_commit_terminal_result_reconciles_after_crash_without_resend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _store, _context = _admitted_project(tmp_path, monkeypatch)
    repo_root = tmp_path / "repo"
    pending = {
        "type": "LocalCommit",
        "git_hash": "e" * 40,
        "mission_id": "01KZT032MISSION00000000001",
        "build_id": "build-crash",
        "project_uuid": PROJECT,
        "changed_files": ["kitty-specs/private-engagement/spec.md"],
        "committed_at": "2026-08-11T12:00:00+00:00",
    }
    from specify_cli.sync.local_commit import SyncState, load_sync_state, save_sync_state

    save_sync_state(repo_root, SyncState(pending_local_commits=[pending]))
    client = WebSocketClient(repo_root=repo_root)
    client.connected = True

    def response(frame: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "LocalCommitAck",
            "git_hash": frame["git_hash"],
            "build_id": frame["build_id"],
            "project_uuid": frame["project_uuid"],
            "admission_generation": frame["admission_generation"],
            "binding_audience": frame["binding_audience"],
            "status": "accepted",
            "received_at": "2026-08-11T12:00:01+00:00",
        }

    websocket = _AckingWebSocket(client, response)
    client.ws = websocket  # type: ignore[assignment]
    monkeypatch.setattr(
        "specify_cli.sync.local_commit.record_local_commit_ack",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("crash")),
    )
    with pytest.raises(RuntimeError, match="crash"):
        asyncio.run(client.send_local_commit(pending))
    assert len(websocket.frames) == 1
    assert load_sync_state(repo_root).pending_local_commits == [pending]

    assert asyncio.run(client.send_local_commit(pending)) is True
    assert len(websocket.frames) == 1
    assert load_sync_state(repo_root).pending_local_commits == []

"""Direct unit tests for the helpers extracted during the WP05 Sonar S3776
(cognitive complexity) remediation of the 7 sync-complexity files.

Each extracted helper below already has indirect coverage through its
parent function's existing test file (e.g. ``test_dossier_pipeline.py``,
``test_orphan_sweep_classification.py``); these tests pin the *helper's own*
contract directly, per the WP05 task's "helpers tested ... or the module's
test file" requirement and CLAUDE.md's "every new branch/helper needs tests
in the same PR."

Files covered: dossier_pipeline.py, runtime_event_emitter.py, body_upload.py,
owner.py, orphan_sweep.py, background.py, classification.py.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from specify_cli.dossier.models import ArtifactRef, MissionDossier
    from specify_cli.sync.body_queue import BodyUploadTask
    from specify_cli.sync.classification import (
        CandidateProbe,
        CleanupClass,
        DaemonIdentityRecord,
        HealthProbe,
        SkipReason,
    )
    from specify_cli.sync.namespace import NamespaceRef

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


# ---------------------------------------------------------------------------
# dossier_pipeline.py — _emit_artifact_events / _emit_snapshot / _emit_drift /
# _prepare_bodies (extracted from sync_feature_dossier, S3776 33 → ≤15)
# ---------------------------------------------------------------------------


class TestDossierPipelineHelpers:
    def _sha256(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()  # noqa: TID251 — test-only checksum, not charter freshness hashing

    def _artifact(self, relative_path: str = "spec.md", *, is_present: bool = True) -> ArtifactRef:
        from specify_cli.dossier.models import ArtifactRef

        content = "# Spec\n"
        return ArtifactRef(
            artifact_key=f"input.{Path(relative_path).stem}",
            artifact_class="input",
            relative_path=relative_path,
            content_hash_sha256=self._sha256(content) if is_present else "",
            size_bytes=len(content.encode("utf-8")) if is_present else 0,
            required_status="required",
            is_present=is_present,
            error_reason=None if is_present else "not_found",
        )

    def _dossier(self, artifacts: list[ArtifactRef]) -> MissionDossier:
        from specify_cli.dossier.models import MissionDossier

        return MissionDossier(
            mission_type="software-dev",
            mission_run_id="test-run-id",
            mission_slug="047-feat",
            feature_dir="/nonexistent/feature",
            artifacts=artifacts,
        )

    def _namespace(self) -> NamespaceRef:
        from specify_cli.sync.namespace import NamespaceRef

        return NamespaceRef(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            mission_slug="047-feat",
            target_branch="main",
            mission_type="software-dev",
            manifest_version="1",
        )

    def test_emit_artifact_events_counts_present_and_missing(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from specify_cli.sync import dossier_pipeline as mod

        emit_indexed = MagicMock(return_value={"event_type": "Indexed"})
        emit_missing = MagicMock(return_value={"event_type": "Missing"})
        monkeypatch.setattr(
            "specify_cli.dossier.events.emit_artifact_indexed", emit_indexed,
        )
        monkeypatch.setattr(
            "specify_cli.dossier.events.emit_artifact_missing", emit_missing,
        )

        present = self._artifact("spec.md")
        missing = self._artifact("plan.md", is_present=False)
        dossier = self._dossier([present, missing])
        ns = self._namespace()

        events = mod._emit_artifact_events(dossier, ns, None, ns.to_dict())

        assert events == 2
        emit_indexed.assert_called_once()
        emit_missing.assert_called_once()

    def test_emit_artifact_events_isolates_per_artifact_failure(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """One artifact's emission failure must not block the other (per-step isolation)."""
        from specify_cli.sync import dossier_pipeline as mod

        emit_indexed = MagicMock(
            side_effect=[RuntimeError("boom"), {"event_type": "Indexed"}],
        )
        monkeypatch.setattr(
            "specify_cli.dossier.events.emit_artifact_indexed", emit_indexed,
        )

        a1 = self._artifact("spec.md")
        a2 = self._artifact("plan.md")
        dossier = self._dossier([a1, a2])
        ns = self._namespace()

        events = mod._emit_artifact_events(dossier, ns, None, ns.to_dict())

        assert events == 1  # only the second emission succeeded
        assert emit_indexed.call_count == 2

    def test_emit_artifact_events_none_result_not_counted(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from specify_cli.sync import dossier_pipeline as mod

        monkeypatch.setattr(
            "specify_cli.dossier.events.emit_artifact_indexed",
            MagicMock(return_value=None),
        )
        dossier = self._dossier([self._artifact("spec.md")])
        ns = self._namespace()

        events = mod._emit_artifact_events(dossier, ns, None, ns.to_dict())

        assert events == 0

    def test_emit_snapshot_success_returns_snapshot_and_event(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        from specify_cli.sync import dossier_pipeline as mod

        fake_snapshot = SimpleNamespace(
            parity_hash_sha256="h",
            total_artifacts=1,
            required_artifacts=1,
            required_present=1,
            required_missing=0,
            optional_artifacts=0,
            optional_present=0,
            completeness_status="complete",
            snapshot_id="snap-1",
            model_dump=lambda mode: {},
        )
        monkeypatch.setattr(
            "specify_cli.dossier.snapshot.compute_snapshot",
            MagicMock(return_value=fake_snapshot),
        )
        monkeypatch.setattr(
            "specify_cli.dossier.snapshot.save_snapshot", MagicMock(),
        )
        monkeypatch.setattr(
            "specify_cli.dossier.events.emit_snapshot_computed",
            MagicMock(return_value={"event_type": "SnapshotComputed"}),
        )
        dossier = self._dossier([self._artifact("spec.md")])
        ns = self._namespace()

        snapshot, events = mod._emit_snapshot(dossier, tmp_path, ns, ns.to_dict())

        assert snapshot is fake_snapshot
        assert events == 1
        assert dossier.latest_snapshot == {}

    def test_emit_snapshot_failure_returns_none_and_zero(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        from specify_cli.sync import dossier_pipeline as mod

        monkeypatch.setattr(
            "specify_cli.dossier.snapshot.compute_snapshot",
            MagicMock(side_effect=RuntimeError("boom")),
        )
        dossier = self._dossier([])
        ns = self._namespace()

        snapshot, events = mod._emit_snapshot(dossier, tmp_path, ns, ns.to_dict())

        assert snapshot is None
        assert events == 0

    def test_emit_drift_emits_when_drift_detected(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        from specify_cli.sync import dossier_pipeline as mod

        monkeypatch.setattr(
            "specify_cli.dossier.drift_detector.detect_drift",
            MagicMock(
                return_value=(
                    True,
                    {
                        "local_parity_hash": "a" * 64,
                        "baseline_parity_hash": "b" * 64,
                        "missing_in_local": [],
                        "missing_in_baseline": [],
                        "severity": "warning",
                    },
                )
            ),
        )
        emit_drift = MagicMock(return_value={"event_type": "Drift"})
        monkeypatch.setattr(
            "specify_cli.dossier.events.emit_parity_drift_detected", emit_drift,
        )
        ns = self._namespace()
        snapshot = SimpleNamespace()
        identity = SimpleNamespace()

        events = mod._emit_drift(snapshot, tmp_path, ns, ns.to_dict(), tmp_path, identity)

        assert events == 1
        emit_drift.assert_called_once()

    def test_emit_drift_no_drift_emits_nothing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        from specify_cli.sync import dossier_pipeline as mod

        monkeypatch.setattr(
            "specify_cli.dossier.drift_detector.detect_drift",
            MagicMock(return_value=(False, None)),
        )
        ns = self._namespace()

        events = mod._emit_drift(
            SimpleNamespace(), tmp_path, ns, ns.to_dict(), tmp_path, SimpleNamespace(),
        )

        assert events == 0

    def test_emit_drift_failure_does_not_raise(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        from specify_cli.sync import dossier_pipeline as mod

        monkeypatch.setattr(
            "specify_cli.dossier.drift_detector.detect_drift",
            MagicMock(side_effect=RuntimeError("boom")),
        )
        ns = self._namespace()

        events = mod._emit_drift(
            SimpleNamespace(), tmp_path, ns, ns.to_dict(), tmp_path, SimpleNamespace(),
        )

        assert events == 0

    def test_prepare_bodies_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        from specify_cli.sync import dossier_pipeline as mod
        from specify_cli.sync.namespace import UploadOutcome, UploadStatus

        outcome = UploadOutcome(
            artifact_path="spec.md", status=UploadStatus.QUEUED, reason="enqueued",
        )
        monkeypatch.setattr(
            "specify_cli.sync.body_upload.prepare_body_uploads",
            MagicMock(return_value=[outcome]),
        )
        dossier = self._dossier([self._artifact("spec.md")])
        ns = self._namespace()

        outcomes, errors = mod._prepare_bodies(dossier, ns, MagicMock(), tmp_path)

        assert outcomes == [outcome]
        assert errors == []

    def test_prepare_bodies_failure_records_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        from specify_cli.sync import dossier_pipeline as mod

        monkeypatch.setattr(
            "specify_cli.sync.body_upload.prepare_body_uploads",
            MagicMock(side_effect=RuntimeError("queue failure")),
        )
        dossier = self._dossier([self._artifact("spec.md")])
        ns = self._namespace()

        outcomes, errors = mod._prepare_bodies(dossier, ns, MagicMock(), tmp_path)

        assert outcomes == []
        assert len(errors) == 1
        assert "body_upload_preparation_failed" in errors[0]
        assert "queue failure" in errors[0]


# ---------------------------------------------------------------------------
# runtime_event_emitter.py — _phase_from_* (extracted from
# _infer_phase_from_snapshot, S3776 21 → ≤15)
# ---------------------------------------------------------------------------


class TestPhaseFromSnapshotHelpers:
    def test_phase_from_issued_step_present(self) -> None:
        from specify_cli.sync.runtime_event_emitter import SyncRuntimeEventEmitter

        snap = SimpleNamespace(issued_step_id="implement")
        assert SyncRuntimeEventEmitter._phase_from_issued_step(snap) == "implement"

    def test_phase_from_issued_step_absent(self) -> None:
        from specify_cli.sync.runtime_event_emitter import SyncRuntimeEventEmitter

        snap = SimpleNamespace(issued_step_id=None)
        assert SyncRuntimeEventEmitter._phase_from_issued_step(snap) is None

    def test_phase_from_pending_decisions_finds_step_id(self) -> None:
        from specify_cli.sync.runtime_event_emitter import SyncRuntimeEventEmitter

        snap = SimpleNamespace(
            pending_decisions={"d1": {"step_id": "clarify"}},
        )
        assert (
            SyncRuntimeEventEmitter._phase_from_pending_decisions(snap) == "clarify"
        )

    def test_phase_from_pending_decisions_empty(self) -> None:
        from specify_cli.sync.runtime_event_emitter import SyncRuntimeEventEmitter

        snap = SimpleNamespace(pending_decisions={})
        assert SyncRuntimeEventEmitter._phase_from_pending_decisions(snap) is None

    def test_phase_from_completed_steps_returns_last(self) -> None:
        from specify_cli.sync.runtime_event_emitter import SyncRuntimeEventEmitter

        snap = SimpleNamespace(completed_steps=["specify", "plan"])
        assert SyncRuntimeEventEmitter._phase_from_completed_steps(snap) == "plan"

    def test_phase_from_completed_steps_empty(self) -> None:
        from specify_cli.sync.runtime_event_emitter import SyncRuntimeEventEmitter

        snap = SimpleNamespace(completed_steps=[])
        assert SyncRuntimeEventEmitter._phase_from_completed_steps(snap) is None

    def test_phase_from_blocked_reason_present(self) -> None:
        from specify_cli.sync.runtime_event_emitter import SyncRuntimeEventEmitter

        snap = SimpleNamespace(blocked_reason="stuck")
        assert SyncRuntimeEventEmitter._phase_from_blocked_reason(snap) == "blocked"

    def test_phase_from_blocked_reason_absent(self) -> None:
        from specify_cli.sync.runtime_event_emitter import SyncRuntimeEventEmitter

        snap = SimpleNamespace(blocked_reason=None)
        assert SyncRuntimeEventEmitter._phase_from_blocked_reason(snap) is None

    def test_infer_phase_priority_order_issued_step_wins(self) -> None:
        """issued_step_id outranks completed_steps and blocked_reason."""
        from specify_cli.sync.runtime_event_emitter import SyncRuntimeEventEmitter

        snap = SimpleNamespace(
            issued_step_id="implement",
            pending_decisions={},
            completed_steps=["specify"],
            blocked_reason="stuck",
        )
        assert SyncRuntimeEventEmitter._infer_phase_from_snapshot(snap) == "implement"

    def test_infer_phase_falls_through_to_blocked_reason(self) -> None:
        from specify_cli.sync.runtime_event_emitter import SyncRuntimeEventEmitter

        snap = SimpleNamespace(
            issued_step_id=None,
            pending_decisions={},
            completed_steps=[],
            blocked_reason="waiting_on_operator",
        )
        assert SyncRuntimeEventEmitter._infer_phase_from_snapshot(snap) == "blocked"

    def test_infer_phase_returns_none_when_nothing_matches(self) -> None:
        from specify_cli.sync.runtime_event_emitter import SyncRuntimeEventEmitter

        snap = SimpleNamespace(
            issued_step_id=None,
            pending_decisions={},
            completed_steps=[],
            blocked_reason=None,
        )
        assert SyncRuntimeEventEmitter._infer_phase_from_snapshot(snap) is None


# ---------------------------------------------------------------------------
# body_upload.py — _process_artifact / _enqueue_artifact (extracted from
# prepare_body_uploads, S3776 19 → ≤15)
# ---------------------------------------------------------------------------


class TestBodyUploadHelpers:
    def _namespace(self) -> NamespaceRef:
        from specify_cli.sync.namespace import NamespaceRef

        return NamespaceRef(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            mission_slug="047-feat",
            target_branch="main",
            mission_type="software-dev",
            manifest_version="1",
        )

    def _artifact(
        self, relative_path: str = "spec.md", *, is_present: bool = True, size_bytes: int = 8,
    ) -> ArtifactRef:
        from specify_cli.dossier.models import ArtifactRef

        content = "# Spec\n"
        return ArtifactRef(
            artifact_key=f"input.{Path(relative_path).stem}",
            artifact_class="input",
            relative_path=relative_path,
            content_hash_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest()  # noqa: TID251 — test-only checksum
            if is_present
            else "",
            size_bytes=size_bytes,
            required_status="required",
            is_present=is_present,
            error_reason=None if is_present else "not_found",
        )

    def test_process_artifact_not_present_skips(self, tmp_path: Path) -> None:
        from specify_cli.sync.body_upload import _process_artifact
        from specify_cli.sync.namespace import UploadStatus

        artifact = self._artifact("spec.md", is_present=False)
        outcome = _process_artifact(artifact, self._namespace(), MagicMock(), tmp_path)

        assert outcome.status == UploadStatus.SKIPPED
        assert "not_present" in outcome.reason

    def test_process_artifact_unsupported_surface_skips(self, tmp_path: Path) -> None:
        from specify_cli.sync.body_upload import _process_artifact
        from specify_cli.sync.namespace import UploadStatus

        artifact = self._artifact("random.txt")
        outcome = _process_artifact(artifact, self._namespace(), MagicMock(), tmp_path)

        assert outcome.status == UploadStatus.SKIPPED
        assert outcome.reason == "unsupported_surface"

    def test_process_artifact_deleted_after_scan_skips(self, tmp_path: Path) -> None:
        from specify_cli.sync.body_upload import _process_artifact
        from specify_cli.sync.namespace import UploadStatus

        # spec.md is a supported surface/format, but the file was never written
        # to tmp_path, so the re-hash guard reports deleted_after_scan.
        artifact = self._artifact("spec.md")
        outcome = _process_artifact(artifact, self._namespace(), MagicMock(), tmp_path)

        assert outcome.status == UploadStatus.SKIPPED
        assert outcome.reason == "deleted_after_scan"

    def test_process_artifact_success_enqueues(self, tmp_path: Path) -> None:
        from specify_cli.sync.body_queue import BodyEnqueueResult
        from specify_cli.sync.body_upload import _process_artifact
        from specify_cli.sync.namespace import UploadStatus

        content = "# Spec\n"
        (tmp_path / "spec.md").write_text(content)
        artifact = self._artifact("spec.md")

        queue = MagicMock()
        queue.enqueue.return_value = BodyEnqueueResult.ENQUEUED

        outcome = _process_artifact(artifact, self._namespace(), queue, tmp_path)

        assert outcome.status == UploadStatus.QUEUED
        assert outcome.reason == "enqueued"
        queue.enqueue.assert_called_once()

    def test_enqueue_artifact_already_exists(self) -> None:
        from specify_cli.sync.body_queue import BodyEnqueueResult
        from specify_cli.sync.body_upload import _enqueue_artifact
        from specify_cli.sync.namespace import UploadStatus

        artifact = self._artifact("spec.md")
        queue = MagicMock()
        queue.enqueue.return_value = BodyEnqueueResult.ALREADY_EXISTS

        outcome = _enqueue_artifact(artifact, self._namespace(), queue, "content", "hash123")

        assert outcome.status == UploadStatus.ALREADY_EXISTS
        assert outcome.reason == "already_in_queue"

    def test_enqueue_artifact_queue_full(self) -> None:
        from specify_cli.sync.body_queue import BodyEnqueueResult
        from specify_cli.sync.body_upload import _enqueue_artifact
        from specify_cli.sync.namespace import UploadStatus

        artifact = self._artifact("spec.md")
        queue = MagicMock()
        queue.enqueue.return_value = BodyEnqueueResult.QUEUE_FULL

        outcome = _enqueue_artifact(artifact, self._namespace(), queue, "content", "hash123")

        assert outcome.status == UploadStatus.FAILED
        assert outcome.reason == "queue_full"


# ---------------------------------------------------------------------------
# owner.py — _orphan_disposition (extracted from reap_orphan_daemons,
# S3776 17 → ≤15)
# ---------------------------------------------------------------------------


class TestOrphanDispositionHelper:
    def _record(
        self,
        cleanup_class: CleanupClass,
        skip_reason: SkipReason | None,
        *,
        spawn_shape_ok: bool = True,
    ) -> DaemonIdentityRecord:
        from specify_cli.sync.classification import (
            DaemonIdentityRecord,
            IdentitySource,
        )

        return DaemonIdentityRecord(
            daemon_family="sync",
            pid=9001,
            port=9401,
            protocol_version=1,
            package_version="3.2.2",
            singleton_scope_id="/scope",
            daemon_root="/scope",
            queue_db_path=None,
            auth_scope=None,
            server_url=None,
            owner_present=False,
            identity_source=IdentitySource.health_self_report,
            executable_summary="/usr/bin/python3",
            spawn_shape_ok=spawn_shape_ok,
            self_report_matches_listener=True,
            is_recorded_singleton=False,
            cleanup_class=cleanup_class,
            skip_reason=skip_reason,
        )

    def test_cross_root_is_out_of_scope(self) -> None:
        from specify_cli.sync.classification import CleanupClass, SkipReason
        from specify_cli.sync.owner import _orphan_disposition

        record = self._record(CleanupClass.OPERATOR_REQUIRED, SkipReason.cross_root)
        assert _orphan_disposition(record) == "skip_out_of_scope"

    def test_unresponsive_is_in_scope_but_not_reaped(self) -> None:
        """operator_required/unresponsive is skipped, but NOT bucketed as out-of-scope."""
        from specify_cli.sync.classification import CleanupClass, SkipReason
        from specify_cli.sync.owner import _orphan_disposition

        record = self._record(CleanupClass.OPERATOR_REQUIRED, SkipReason.unresponsive)
        assert _orphan_disposition(record) == "skip_in_scope"

    def test_safe_auto_without_spawn_shape_is_out_of_scope(self) -> None:
        from specify_cli.sync.classification import CleanupClass
        from specify_cli.sync.owner import _orphan_disposition

        record = self._record(CleanupClass.SAFE_AUTO, None, spawn_shape_ok=False)
        assert _orphan_disposition(record) == "skip_out_of_scope"

    def test_safe_auto_with_spawn_shape_is_reap(self) -> None:
        from specify_cli.sync.classification import CleanupClass
        from specify_cli.sync.owner import _orphan_disposition

        record = self._record(CleanupClass.SAFE_AUTO, None, spawn_shape_ok=True)
        assert _orphan_disposition(record) == "reap"


# ---------------------------------------------------------------------------
# orphan_sweep.py — _classify_reset_action / _skipped_entry / _swept_entry
# (extracted from reset_orphans, S3776 17 → ≤15)
# ---------------------------------------------------------------------------


class TestResetOrphansHelpers:
    def _record(
        self,
        cleanup_class: CleanupClass,
        skip_reason: SkipReason | None,
        *,
        package_version: str | None = "3.2.2",
    ) -> DaemonIdentityRecord:
        from specify_cli.sync.classification import (
            DaemonIdentityRecord,
            IdentitySource,
        )

        return DaemonIdentityRecord(
            daemon_family="sync",
            pid=9001,
            port=9401,
            protocol_version=1,
            package_version=package_version,
            singleton_scope_id="/scope",
            daemon_root="/scope",
            queue_db_path=None,
            auth_scope=None,
            server_url=None,
            owner_present=False,
            identity_source=IdentitySource.health_self_report,
            executable_summary="/usr/bin/python3",
            spawn_shape_ok=True,
            self_report_matches_listener=True,
            is_recorded_singleton=False,
            cleanup_class=cleanup_class,
            skip_reason=skip_reason,
        )

    def test_classify_reset_action_never_touch(self) -> None:
        from specify_cli.sync.classification import CleanupClass, SkipReason
        from specify_cli.sync.orphan_sweep import _classify_reset_action

        record = self._record(CleanupClass.NEVER_TOUCH, SkipReason.out_of_range)
        assert (
            _classify_reset_action(record, include_operator_required=False)
            == "skip_never_touch"
        )

    def test_classify_reset_action_operator_required_default(self) -> None:
        from specify_cli.sync.classification import CleanupClass, SkipReason
        from specify_cli.sync.orphan_sweep import _classify_reset_action

        record = self._record(CleanupClass.OPERATOR_REQUIRED, SkipReason.unresponsive)
        assert (
            _classify_reset_action(record, include_operator_required=False)
            == "skip_operator_required"
        )

    def test_classify_reset_action_operator_required_with_force(self) -> None:
        from specify_cli.sync.classification import CleanupClass, SkipReason
        from specify_cli.sync.orphan_sweep import _classify_reset_action

        record = self._record(CleanupClass.OPERATOR_REQUIRED, SkipReason.unresponsive)
        assert (
            _classify_reset_action(record, include_operator_required=True) == "sweep"
        )

    def test_classify_reset_action_safe_auto_sweeps(self) -> None:
        from specify_cli.sync.classification import CleanupClass
        from specify_cli.sync.orphan_sweep import _classify_reset_action

        record = self._record(CleanupClass.SAFE_AUTO, None)
        assert (
            _classify_reset_action(record, include_operator_required=False) == "sweep"
        )

    def test_skipped_entry_fields(self) -> None:
        from specify_cli.sync.classification import CleanupClass, SkipReason
        from specify_cli.sync.orphan_sweep import _skipped_entry

        record = self._record(CleanupClass.OPERATOR_REQUIRED, SkipReason.cross_root)
        entry = _skipped_entry(record)

        assert entry.pid == 9001
        assert entry.port == 9401
        assert entry.cleanup_class == "operator_required"
        assert entry.skip_reason == "cross_root"

    def test_swept_entry_stale_version_reason(self) -> None:
        from specify_cli.sync.classification import CleanupClass
        from specify_cli.sync.orphan_sweep import _swept_entry

        record = self._record(CleanupClass.SAFE_AUTO, None, package_version="3.2.1")
        entry = _swept_entry(record, "terminate")

        assert entry.cleanup_path == "terminate"
        assert entry.reason == "safe_auto stale-version"

    def test_swept_entry_no_package_version_plain_reason(self) -> None:
        from specify_cli.sync.classification import CleanupClass
        from specify_cli.sync.orphan_sweep import _swept_entry

        record = self._record(CleanupClass.SAFE_AUTO, None, package_version=None)
        entry = _swept_entry(record, "kill")

        assert entry.reason == "safe_auto"


# ---------------------------------------------------------------------------
# background.py — _partition_window (extracted from
# _collect_consenting_body_tasks, S3776 17 → ≤15)
# ---------------------------------------------------------------------------


class TestPartitionWindowHelper:
    def _task(
        self, row_id: int, project_uuid: str, artifact_path: str = "spec.md",
    ) -> BodyUploadTask:
        from kernel.clock import now_epoch
        from specify_cli.sync.body_queue import BodyUploadTask

        return BodyUploadTask(
            row_id=row_id,
            project_uuid=project_uuid,
            # Per-project store identity fields (ProjectSyncStore migration):
            # required by the branch's consent-epoch capture model.
            epoch_id=1,
            capture_sequence=row_id,
            mission_slug="047-feat",
            target_branch="main",
            mission_type="software-dev",
            manifest_version="1",
            artifact_path=artifact_path,
            content_hash="abc123",
            hash_algorithm="sha256",
            content_body="# Spec\n",
            size_bytes=8,
            retry_count=0,
            next_attempt_at=0.0,
            created_at=now_epoch(),
            last_error=None,
        )

    def test_partition_window_splits_granted_and_denied(self) -> None:
        from specify_cli.sync.background import _partition_window

        granted_task = self._task(1, "proj-a")
        denied_task = self._task(2, "proj-b")

        consenting, newly_denied, withheld = _partition_window(
            [granted_task, denied_task], frozenset({"proj-a"}),
        )

        assert consenting == [granted_task]
        assert newly_denied == {"proj-b"}
        assert withheld == 1

    def test_partition_window_all_granted(self) -> None:
        from specify_cli.sync.background import _partition_window

        tasks = [self._task(1, "proj-a"), self._task(2, "proj-a")]

        consenting, newly_denied, withheld = _partition_window(
            tasks, frozenset({"proj-a"}),
        )

        assert consenting == tasks
        assert newly_denied == set()
        assert withheld == 0

    def test_partition_window_blank_identity_grouped_as_empty_string(self) -> None:
        from specify_cli.sync.background import _partition_window

        task = self._task(1, "  ")  # blank/whitespace-only project_uuid

        consenting, newly_denied, withheld = _partition_window([task], frozenset())

        assert consenting == []
        assert newly_denied == {""}
        assert withheld == 1


# ---------------------------------------------------------------------------
# classification.py — _classify_never_touch_or_singleton /
# _classify_operator_required (extracted from classify_candidate,
# S3776 16 → ≤15)
# ---------------------------------------------------------------------------


class TestClassifyCandidateHelpers:
    def _probe(
        self,
        *,
        port: int = 9401,
        listener_pid: int | None = 9001,
        singleton_scope_id: str | None = "/scope",
        spawn_shape_ok: bool = True,
        health: HealthProbe | None = None,
        owner_present: bool = False,
    ) -> CandidateProbe:
        from specify_cli.sync.classification import CandidateProbe

        return CandidateProbe(
            port=port,
            listener_pid=listener_pid,
            health=health,
            singleton_scope_id=singleton_scope_id,
            spawn_shape_ok=spawn_shape_ok,
            executable_summary="/usr/bin/python3",
            owner_present=owner_present,
        )

    def _health(
        self, *, responded: bool = True, owner_pid: int = 9001, owner_port: int = 9401,
    ) -> HealthProbe:
        from specify_cli.sync.classification import HealthProbe

        return HealthProbe(
            responded=responded,
            status="ok" if responded else None,
            protocol_version=1,
            package_version="3.2.2",
            daemon_family="sync",
            queue_db_path=None,
            auth_scope=None,
            server_url=None,
            owner_pid=owner_pid,
            owner_port=owner_port,
        )

    def test_never_touch_out_of_range_port(self) -> None:
        from specify_cli.sync.classification import (
            CleanupClass,
            SkipReason,
            _classify_never_touch_or_singleton,
        )

        probe = self._probe(port=9999)
        record = _classify_never_touch_or_singleton(probe, is_singleton=False)

        assert record is not None
        assert record.cleanup_class == CleanupClass.NEVER_TOUCH
        assert record.skip_reason == SkipReason.out_of_range

    def test_never_touch_no_spawn_shape(self) -> None:
        from specify_cli.sync.classification import (
            CleanupClass,
            SkipReason,
            _classify_never_touch_or_singleton,
        )

        probe = self._probe(spawn_shape_ok=False, health=self._health())
        record = _classify_never_touch_or_singleton(probe, is_singleton=False)

        assert record is not None
        assert record.cleanup_class == CleanupClass.NEVER_TOUCH
        assert record.skip_reason == SkipReason.third_party

    def test_never_touch_returns_none_when_in_range_and_singleton_false_and_sk_identity_present(
        self,
    ) -> None:
        """When rows 1–3 all fall through, the helper returns None (delegates onward)."""
        from specify_cli.sync.classification import _classify_never_touch_or_singleton

        probe = self._probe(health=self._health())
        record = _classify_never_touch_or_singleton(probe, is_singleton=False)

        assert record is None

    def test_never_touch_singleton_short_circuits(self) -> None:
        from specify_cli.sync.classification import (
            CleanupClass,
            SkipReason,
            _classify_never_touch_or_singleton,
        )

        probe = self._probe(health=self._health())
        record = _classify_never_touch_or_singleton(probe, is_singleton=True)

        assert record is not None
        assert record.cleanup_class == CleanupClass.NEVER_TOUCH
        assert record.skip_reason == SkipReason.is_recorded_singleton
        assert record.is_recorded_singleton is True

    def test_operator_required_missing_pid(self) -> None:
        from specify_cli.sync.classification import (
            CleanupClass,
            ForegroundScope,
            SingletonRef,
            SkipReason,
            _classify_operator_required,
        )

        probe = self._probe(listener_pid=None)
        foreground = ForegroundScope(
            scope_id="/scope", executable_scope="/usr/bin/python3",
            singleton=SingletonRef(pid=None, port=None),
        )
        record = _classify_operator_required(probe, foreground, is_singleton=False)

        assert record is not None
        assert record.cleanup_class == CleanupClass.OPERATOR_REQUIRED
        assert record.skip_reason == SkipReason.missing_pid

    def test_operator_required_cross_root(self) -> None:
        from specify_cli.sync.classification import (
            ForegroundScope,
            SingletonRef,
            SkipReason,
            _classify_operator_required,
        )

        probe = self._probe(singleton_scope_id="/scope-a")
        foreground = ForegroundScope(
            scope_id="/scope-b", executable_scope="/usr/bin/python3",
            singleton=SingletonRef(pid=None, port=None),
        )
        record = _classify_operator_required(probe, foreground, is_singleton=False)

        assert record is not None
        assert record.skip_reason == SkipReason.cross_root

    def test_operator_required_returns_none_when_all_guards_pass(self) -> None:
        """Row 9 (safe_auto) is the caller's fallback, not this helper's concern."""
        from specify_cli.sync.classification import (
            ForegroundScope,
            SingletonRef,
            _classify_operator_required,
        )

        probe = self._probe(health=self._health())
        foreground = ForegroundScope(
            scope_id="/scope", executable_scope="/usr/bin/python3",
            singleton=SingletonRef(pid=None, port=None),
        )
        record = _classify_operator_required(probe, foreground, is_singleton=False)

        assert record is None

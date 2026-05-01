"""Tests for specify_cli.sync.dossier_pipeline module."""

from __future__ import annotations

import pytest
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

from specify_cli.dossier.models import ArtifactRef, MissionDossier
from specify_cli.sync.dossier_pipeline import DossierSyncResult, sync_feature_dossier
from specify_cli.sync.namespace import (
    NamespaceRef,
    UploadOutcome,
    UploadStatus,
)

pytestmark = pytest.mark.fast


def _make_namespace() -> NamespaceRef:
    return NamespaceRef(
        project_uuid="550e8400-e29b-41d4-a716-446655440000",
        mission_slug="047-feat",
        target_branch="main",
        mission_type="software-dev",
        manifest_version="1",
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _make_artifact(
    relative_path: str = "spec.md",
    *,
    is_present: bool = True,
    content: str = "# Spec\n",
) -> ArtifactRef:
    return ArtifactRef(
        artifact_key=f"input.{Path(relative_path).stem}",
        artifact_class="input",
        relative_path=relative_path,
        content_hash_sha256=_sha256(content) if is_present else "",
        size_bytes=len(content.encode("utf-8")) if is_present else 0,
        required_status="required",
        is_present=is_present,
        error_reason=None if is_present else "not_found",
    )


def _make_dossier(
    artifacts: list[ArtifactRef] | None = None,
) -> MissionDossier:
    return MissionDossier(
        mission_type="software-dev",
        mission_run_id="test-run-id",
        mission_slug="047-feat",
        feature_dir="/tmp/feature",
        artifacts=artifacts or [],
    )


def _write_feature_file(feature_dir: Path, relative_path: str, content: str) -> None:
    file_path = feature_dir / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)


# --- DossierSyncResult ---


class TestDossierSyncResult:
    def test_success_true_when_dossier_and_no_errors(self) -> None:
        result = DossierSyncResult(
            dossier=_make_dossier(),
            events_emitted=1,
            body_outcomes=[],
            errors=[],
        )
        assert result.success is True

    def test_success_false_when_no_dossier(self) -> None:
        result = DossierSyncResult(
            dossier=None,
            events_emitted=0,
            body_outcomes=[],
            errors=["failed"],
        )
        assert result.success is False

    def test_success_false_when_errors(self) -> None:
        result = DossierSyncResult(
            dossier=_make_dossier(),
            events_emitted=0,
            body_outcomes=[],
            errors=["body_upload_preparation_failed: boom"],
        )
        assert result.success is False


# --- sync_feature_dossier ---


@patch("specify_cli.sync.body_upload.prepare_body_uploads")
@patch("specify_cli.dossier.events.emit_snapshot_computed")
@patch("specify_cli.dossier.events.emit_artifact_indexed")
@patch("specify_cli.dossier.indexer.Indexer")
@patch("specify_cli.dossier.manifest.ManifestRegistry")
class TestSyncFeatureDossier:
    def test_happy_path(
        self,
        mock_registry_cls: MagicMock,
        mock_indexer_cls: MagicMock,
        mock_emit: MagicMock,
        mock_emit_snapshot: MagicMock,
        mock_prepare: MagicMock,
        tmp_path: Path,
    ) -> None:
        artifact = _make_artifact("spec.md")
        dossier = _make_dossier([artifact])

        mock_indexer = MagicMock()
        mock_indexer.index_feature.return_value = dossier
        mock_indexer_cls.return_value = mock_indexer

        mock_emit.return_value = {"event_type": "MissionDossierArtifactIndexed"}
        mock_emit_snapshot.return_value = {
            "event_type": "MissionDossierSnapshotComputed",
        }
        mock_prepare.return_value = [
            UploadOutcome(
                artifact_path="spec.md",
                status=UploadStatus.QUEUED,
                reason="enqueued",
                content_hash=artifact.content_hash_sha256,
            ),
        ]

        ns = _make_namespace()
        queue = MagicMock()
        result = sync_feature_dossier(tmp_path, ns, queue)

        assert result.success is True
        assert result.dossier is dossier
        assert result.events_emitted == 2
        assert len(result.body_outcomes) == 1
        assert result.body_outcomes[0].status == UploadStatus.QUEUED
        assert result.errors == []

    def test_indexer_failure(
        self,
        mock_registry_cls: MagicMock,
        mock_indexer_cls: MagicMock,
        mock_emit: MagicMock,
        mock_emit_snapshot: MagicMock,
        mock_prepare: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_indexer = MagicMock()
        mock_indexer.index_feature.side_effect = RuntimeError("scan failed")
        mock_indexer_cls.return_value = mock_indexer

        ns = _make_namespace()
        queue = MagicMock()
        result = sync_feature_dossier(tmp_path, ns, queue)

        assert result.success is False
        assert result.dossier is None
        assert result.events_emitted == 0
        assert result.body_outcomes == []
        assert "scan failed" in result.errors[0]

        # Event emission and body prep should not be called
        mock_emit.assert_not_called()
        mock_prepare.assert_not_called()

    def test_event_emission_failure_does_not_abort_pipeline(
        self,
        mock_registry_cls: MagicMock,
        mock_indexer_cls: MagicMock,
        mock_emit: MagicMock,
        mock_emit_snapshot: MagicMock,
        mock_prepare: MagicMock,
        tmp_path: Path,
    ) -> None:
        a1 = _make_artifact("spec.md", content="spec content")
        a2 = _make_artifact("plan.md", content="plan content")
        dossier = _make_dossier([a1, a2])

        mock_indexer = MagicMock()
        mock_indexer.index_feature.return_value = dossier
        mock_indexer_cls.return_value = mock_indexer

        # First emission fails, second succeeds
        mock_emit.side_effect = [
            RuntimeError("emit failed"),
            {"event_type": "MissionDossierArtifactIndexed"},
        ]
        mock_emit_snapshot.return_value = {
            "event_type": "MissionDossierSnapshotComputed",
        }
        mock_prepare.return_value = []

        ns = _make_namespace()
        queue = MagicMock()
        result = sync_feature_dossier(tmp_path, ns, queue)

        # Pipeline still succeeds (partial failure is non-fatal)
        assert result.success is True
        assert result.events_emitted == 2  # Second artifact + snapshot succeeded
        mock_prepare.assert_called_once()  # Body prep still ran

    def test_body_preparation_failure_does_not_abort_events(
        self,
        mock_registry_cls: MagicMock,
        mock_indexer_cls: MagicMock,
        mock_emit: MagicMock,
        mock_emit_snapshot: MagicMock,
        mock_prepare: MagicMock,
        tmp_path: Path,
    ) -> None:
        artifact = _make_artifact("spec.md")
        dossier = _make_dossier([artifact])

        mock_indexer = MagicMock()
        mock_indexer.index_feature.return_value = dossier
        mock_indexer_cls.return_value = mock_indexer

        mock_emit.return_value = {"event_type": "MissionDossierArtifactIndexed"}
        mock_emit_snapshot.return_value = {
            "event_type": "MissionDossierSnapshotComputed",
        }
        mock_prepare.side_effect = RuntimeError("queue failure")

        ns = _make_namespace()
        queue = MagicMock()
        result = sync_feature_dossier(tmp_path, ns, queue)

        assert result.success is False  # Has errors
        assert result.events_emitted == 2  # Artifact + snapshot still emitted
        assert result.body_outcomes == []
        assert any("body_upload_preparation_failed" in e for e in result.errors)

    def test_empty_dossier(
        self,
        mock_registry_cls: MagicMock,
        mock_indexer_cls: MagicMock,
        mock_emit: MagicMock,
        mock_emit_snapshot: MagicMock,
        mock_prepare: MagicMock,
        tmp_path: Path,
    ) -> None:
        dossier = _make_dossier([])

        mock_indexer = MagicMock()
        mock_indexer.index_feature.return_value = dossier
        mock_indexer_cls.return_value = mock_indexer

        mock_emit_snapshot.return_value = {
            "event_type": "MissionDossierSnapshotComputed",
        }
        mock_prepare.return_value = []

        ns = _make_namespace()
        queue = MagicMock()
        result = sync_feature_dossier(tmp_path, ns, queue)

        assert result.success is True
        assert result.events_emitted == 1
        assert result.body_outcomes == []
        assert result.errors == []
        mock_emit.assert_not_called()

    @patch("specify_cli.dossier.events.emit_artifact_missing")
    def test_emits_indexed_for_present_and_missing_for_absent(
        self,
        mock_emit_missing: MagicMock,
        mock_registry_cls: MagicMock,
        mock_indexer_cls: MagicMock,
        mock_emit: MagicMock,
        mock_emit_snapshot: MagicMock,
        mock_prepare: MagicMock,
        tmp_path: Path,
    ) -> None:
        present = _make_artifact("spec.md")
        missing = _make_artifact("plan.md", is_present=False)
        dossier = _make_dossier([present, missing])

        mock_indexer = MagicMock()
        mock_indexer.index_feature.return_value = dossier
        mock_indexer_cls.return_value = mock_indexer

        mock_emit.return_value = {"event_type": "MissionDossierArtifactIndexed"}
        mock_emit_missing.return_value = {"event_type": "MissionDossierArtifactMissing"}
        mock_emit_snapshot.return_value = {
            "event_type": "MissionDossierSnapshotComputed",
        }
        mock_prepare.return_value = []

        ns = _make_namespace()
        queue = MagicMock()
        result = sync_feature_dossier(tmp_path, ns, queue)

        # 3 events: 1 indexed (present) + 1 missing + 1 snapshot
        assert result.events_emitted == 3
        assert mock_emit.call_count == 1
        assert mock_emit.call_args.kwargs["relative_path"] == "spec.md"
        assert mock_emit_missing.call_count == 1
        assert mock_emit_missing.call_args.kwargs["artifact_key"] == "input.plan"

    def test_emit_returns_none_not_counted(
        self,
        mock_registry_cls: MagicMock,
        mock_indexer_cls: MagicMock,
        mock_emit: MagicMock,
        mock_emit_snapshot: MagicMock,
        mock_prepare: MagicMock,
        tmp_path: Path,
    ) -> None:
        artifact = _make_artifact("spec.md")
        dossier = _make_dossier([artifact])

        mock_indexer = MagicMock()
        mock_indexer.index_feature.return_value = dossier
        mock_indexer_cls.return_value = mock_indexer

        # emit returns None (validation failure inside)
        mock_emit.return_value = None
        mock_emit_snapshot.return_value = None
        mock_prepare.return_value = []

        ns = _make_namespace()
        queue = MagicMock()
        result = sync_feature_dossier(tmp_path, ns, queue)

        assert result.events_emitted == 0
        assert result.success is True  # emit returning None is not an error

    def test_mixed_body_outcomes(
        self,
        mock_registry_cls: MagicMock,
        mock_indexer_cls: MagicMock,
        mock_emit: MagicMock,
        mock_emit_snapshot: MagicMock,
        mock_prepare: MagicMock,
        tmp_path: Path,
    ) -> None:
        a1 = _make_artifact("spec.md")
        a2 = _make_artifact("tasks/WP01.md", content="# WP01\n")
        dossier = _make_dossier([a1, a2])

        mock_indexer = MagicMock()
        mock_indexer.index_feature.return_value = dossier
        mock_indexer_cls.return_value = mock_indexer

        mock_emit.return_value = {"event_type": "MissionDossierArtifactIndexed"}
        mock_emit_snapshot.return_value = {
            "event_type": "MissionDossierSnapshotComputed",
        }
        mock_prepare.return_value = [
            UploadOutcome(
                artifact_path="spec.md",
                status=UploadStatus.QUEUED,
                reason="enqueued",
                content_hash=a1.content_hash_sha256,
            ),
            UploadOutcome(
                artifact_path="tasks/WP01.md",
                status=UploadStatus.SKIPPED,
                reason="unsupported_format: .png",
            ),
        ]

        ns = _make_namespace()
        queue = MagicMock()
        result = sync_feature_dossier(tmp_path, ns, queue)

        assert result.success is True
        assert result.events_emitted == 3
        assert len(result.body_outcomes) == 2

        queued = [o for o in result.body_outcomes if o.status == UploadStatus.QUEUED]
        skipped = [o for o in result.body_outcomes if o.status == UploadStatus.SKIPPED]
        assert len(queued) == 1
        assert len(skipped) == 1

    def test_passes_correct_args_to_indexer(
        self,
        mock_registry_cls: MagicMock,
        mock_indexer_cls: MagicMock,
        mock_emit: MagicMock,
        mock_emit_snapshot: MagicMock,
        mock_prepare: MagicMock,
        tmp_path: Path,
    ) -> None:
        dossier = _make_dossier([])
        mock_indexer = MagicMock()
        mock_indexer.index_feature.return_value = dossier
        mock_indexer_cls.return_value = mock_indexer
        mock_prepare.return_value = []

        ns = _make_namespace()
        queue = MagicMock()
        sync_feature_dossier(
            tmp_path,
            ns,
            queue,
            mission_type="documentation",
            step_id="plan",
        )

        mock_indexer.index_feature.assert_called_once_with(
            tmp_path,
            "documentation",
            "plan",
        )

    def test_passes_correct_args_to_prepare(
        self,
        mock_registry_cls: MagicMock,
        mock_indexer_cls: MagicMock,
        mock_emit: MagicMock,
        mock_emit_snapshot: MagicMock,
        mock_prepare: MagicMock,
        tmp_path: Path,
    ) -> None:
        artifact = _make_artifact("spec.md")
        dossier = _make_dossier([artifact])

        mock_indexer = MagicMock()
        mock_indexer.index_feature.return_value = dossier
        mock_indexer_cls.return_value = mock_indexer

        mock_emit.return_value = {"event_type": "MissionDossierArtifactIndexed"}
        mock_emit_snapshot.return_value = {
            "event_type": "MissionDossierSnapshotComputed",
        }
        mock_prepare.return_value = []

        ns = _make_namespace()
        queue = MagicMock()
        sync_feature_dossier(tmp_path, ns, queue)

        mock_prepare.assert_called_once_with(
            artifacts=dossier.artifacts,
            namespace_ref=ns,
            body_queue=queue,
            feature_dir=tmp_path,
        )

    def test_passes_step_id_to_emit(
        self,
        mock_registry_cls: MagicMock,
        mock_indexer_cls: MagicMock,
        mock_emit: MagicMock,
        mock_emit_snapshot: MagicMock,
        mock_prepare: MagicMock,
        tmp_path: Path,
    ) -> None:
        artifact = _make_artifact("spec.md")
        dossier = _make_dossier([artifact])

        mock_indexer = MagicMock()
        mock_indexer.index_feature.return_value = dossier
        mock_indexer_cls.return_value = mock_indexer

        mock_emit.return_value = {"event_type": "MissionDossierArtifactIndexed"}
        mock_emit_snapshot.return_value = {
            "event_type": "MissionDossierSnapshotComputed",
        }
        mock_prepare.return_value = []

        ns = _make_namespace()
        queue = MagicMock()
        sync_feature_dossier(tmp_path, ns, queue, step_id="plan")

        assert mock_emit.call_args.kwargs["step_id"] == "plan"

    @patch("specify_cli.dossier.events.emit_parity_drift_detected")
    @patch("specify_cli.dossier.drift_detector.detect_drift")
    def test_emits_snapshot_and_drift_with_namespace(
        self,
        mock_detect_drift: MagicMock,
        mock_emit_drift: MagicMock,
        mock_registry_cls: MagicMock,
        mock_indexer_cls: MagicMock,
        mock_emit: MagicMock,
        mock_emit_snapshot: MagicMock,
        mock_prepare: MagicMock,
        tmp_path: Path,
    ) -> None:
        from uuid import UUID

        from specify_cli.sync.project_identity import ProjectIdentity

        artifact = _make_artifact("spec.md")
        dossier = _make_dossier([artifact])

        mock_indexer = MagicMock()
        mock_indexer.index_feature.return_value = dossier
        mock_indexer_cls.return_value = mock_indexer

        mock_emit.return_value = {"event_type": "MissionDossierArtifactIndexed"}
        mock_emit_snapshot.return_value = {
            "event_type": "MissionDossierSnapshotComputed",
        }
        mock_detect_drift.return_value = (
            True,
            {
                "local_parity_hash": "a" * 64,
                "baseline_parity_hash": "b" * 64,
                "missing_in_local": [],
                "missing_in_baseline": [],
                "severity": "warning",
            },
        )
        mock_emit_drift.return_value = {
            "event_type": "MissionDossierParityDriftDetected",
        }
        mock_prepare.return_value = []

        ns = _make_namespace()
        queue = MagicMock()
        identity = ProjectIdentity(
            project_uuid=UUID(ns.project_uuid),
            project_slug="test-proj",
            node_id="node-123",
        )

        result = sync_feature_dossier(
            tmp_path,
            ns,
            queue,
            repo_root=tmp_path,
            project_identity=identity,
        )

        assert result.events_emitted == 3
        assert mock_emit_snapshot.call_args.kwargs["namespace"] == ns.to_dict()
        assert mock_emit_drift.call_args.kwargs["namespace"] == ns.to_dict()

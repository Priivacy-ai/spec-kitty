"""Tests for specify_cli.sync.dossier_pipeline module."""

from __future__ import annotations

import pytest
import hashlib
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from specify_cli.dossier.emitter_adapter import (
    register_dossier_emitter,
    reset_dossier_emitter,
)
from specify_cli.dossier.models import ArtifactRef, MissionDossier
from specify_cli.sync.dossier_pipeline import (
    DossierSyncResult,
    _emit_artifact_events,
    sync_feature_dossier,
)
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.namespace import (
    NamespaceRef,
    UploadOutcome,
    UploadStatus,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


def _make_namespace() -> NamespaceRef:
    return NamespaceRef(
        project_uuid="550e8400-e29b-41d4-a716-446655440000",
        mission_slug="047-feat",
        target_branch="main",
        mission_type="software-dev",
        manifest_version="1",
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()  # noqa: TID251 — sync dossier content checksum (protocol-level), not charter freshness hashing


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
        feature_dir="/nonexistent/feature",
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
        monkeypatch: pytest.MonkeyPatch,
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
        queue.project_uuid = ns.project_uuid
        monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
        store = ProjectSyncStore(ns.project_uuid)
        layout = store.layout_generation()
        with store.unit_of_work() as unit:
            context = store.create_context()
            result = sync_feature_dossier(
                tmp_path,
                ns,
                queue,
                project_context=context,
                project_unit=unit,
                project_layout=layout,
            )

        assert result.success is True
        assert result.dossier is dossier
        assert result.events_emitted == 2
        assert len(result.body_outcomes) == 1
        assert result.body_outcomes[0].status == UploadStatus.QUEUED
        assert result.errors == []
        assert mock_emit.call_args.kwargs["project_context"] is context
        assert mock_emit.call_args.kwargs["project_unit"] is unit
        assert mock_emit_snapshot.call_args.kwargs["project_context"] is context

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

    def test_indexer_failure_schema_invalid_manifest_is_actionable(
        self,
        mock_registry_cls: MagicMock,
        mock_indexer_cls: MagicMock,
        mock_emit: MagicMock,
        mock_emit_snapshot: MagicMock,
        mock_prepare: MagicMock,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """#3542-B: a schema-invalid ``expected-artifacts.yaml`` must surface
        as an actionable, file-naming WARNING on the dossier sync path — the
        dominant runtime path (fired on every status transition via
        ``trigger_feature_dossier_sync_if_enabled``, which is fire-and-forget
        and never raises). Before this fix, ``Indexer.index_feature``
        raising ``pydantic.ValidationError`` (per FR-016 /
        ``ManifestRegistry.load_manifest``) fell into the same generic
        ``except Exception`` branch as any other indexer crash:
        ``logger.exception`` (ERROR level, full traceback) plus a bare
        ``str(exc)`` in ``DossierSyncResult.errors`` — which names the bad
        key but not which manifest file, burying an author-actionable typo
        under a stack trace meant for genuine bugs.

        This is a unit-level test of the ``sync_feature_dossier`` branch in
        isolation (``Indexer``/``ManifestRegistry`` are mocked at the class
        level for this whole test class) — it hand-builds the
        ``ManifestSchemaError`` ``Indexer.index_feature`` is documented to
        raise. The REAL, unmocked end-to-end path — a genuine typo'd
        manifest routed through the real ``ManifestRegistry.load_manifest``
        producer, with no hand-crafted exception anywhere — is covered
        separately by
        ``test_real_load_manifest_schema_error_names_origin_through_sync_feature_dossier``
        below (paula rank-3).
        """
        from pydantic import ValidationError

        from specify_cli.dossier.manifest import ExpectedArtifactManifest, ManifestSchemaError

        origin = "doctrine/software-dev/expected-artifacts.yaml"
        try:
            ExpectedArtifactManifest(
                mission_type="software-dev",
                required_alwyas=[],  # type: ignore[call-arg]  # deliberate typo
            )
            raise AssertionError("expected ValidationError")  # pragma: no cover
        except ValidationError as exc:
            schema_error = ManifestSchemaError("software-dev", origin)
            schema_error.__cause__ = exc

        mock_indexer = MagicMock()
        mock_indexer.index_feature.side_effect = schema_error
        mock_indexer_cls.return_value = mock_indexer

        ns = _make_namespace()
        queue = MagicMock()
        with caplog.at_level(logging.WARNING, logger="specify_cli.sync.dossier_pipeline"):
            result = sync_feature_dossier(tmp_path, ns, queue)

        assert result.success is False
        assert result.dossier is None
        assert result.events_emitted == 0
        assert result.body_outcomes == []
        assert len(result.errors) == 1
        error_message = result.errors[0]
        assert "doctrine/software-dev/expected-artifacts.yaml" in error_message, error_message
        assert "required_alwyas" in error_message, error_message
        assert "Fix your expected-artifacts.yaml" in error_message, error_message

        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any(
            "doctrine/software-dev/expected-artifacts.yaml" in r.getMessage()
            for r in warning_records
        ), caplog.text
        # Must NOT also fall through to the generic ERROR-level
        # logger.exception(...) branch meant for genuine indexer bugs.
        assert not any(r.levelno >= logging.ERROR for r in caplog.records), caplog.text

        # Event emission and body prep should not be called
        mock_emit.assert_not_called()
        mock_prepare.assert_not_called()

    def test_artifactref_validation_error_is_not_misattributed_to_manifest_schema(
        self,
        mock_registry_cls: MagicMock,
        mock_indexer_cls: MagicMock,
        mock_emit: MagicMock,
        mock_emit_snapshot: MagicMock,
        mock_prepare: MagicMock,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """M1 pin (adversarial-review MAJOR finding, highest-value fix): a
        ``pydantic.ValidationError`` raised while constructing an
        ``ArtifactRef``/``MissionDossier`` model INSIDE ``index_feature`` —
        e.g. a genuine ``ArtifactRef.validate_artifact_key`` bug — is NOT the
        same failure as a schema-invalid ``expected-artifacts.yaml``, even
        though both are, at the raw-type level, a ``pydantic.ValidationError``.

        Before this fix, ``sync_feature_dossier`` caught
        ``except pydantic.ValidationError`` around the WHOLE
        ``Indexer.index_feature(...)`` call — a proxy for "the manifest is
        broken" that misfires on ANY ``ValidationError``, including one
        raised well after the manifest already loaded successfully. That
        downgraded a genuine indexer bug from ERROR-with-stack-trace to a
        WARNING mislabeled "Fix your expected-artifacts.yaml." — actively
        misleading whoever investigates it.

        This test constructs a REAL ``ArtifactRef`` validation failure (an
        ``artifact_key`` that fails ``validate_artifact_key``'s regex — the
        same failure mode a real filename-derived key could hit, e.g. a file
        containing parentheses) and asserts it reaches the GENERIC
        ``except Exception`` branch (ERROR + stack trace, verbatim
        ``str(exc)``), never the manifest-schema branch.
        """
        from pydantic import ValidationError

        from specify_cli.dossier.models import ArtifactRef

        try:
            ArtifactRef(
                artifact_key="bad key (parens)",  # fails validate_artifact_key's regex
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="",
                size_bytes=0,
                required_status="required",
                is_present=True,
            )
            raise AssertionError("expected ValidationError")  # pragma: no cover
        except ValidationError as exc:
            artifact_ref_error = exc

        mock_indexer = MagicMock()
        mock_indexer.index_feature.side_effect = artifact_ref_error
        mock_indexer_cls.return_value = mock_indexer

        ns = _make_namespace()
        queue = MagicMock()
        with caplog.at_level(logging.WARNING, logger="specify_cli.sync.dossier_pipeline"):
            result = sync_feature_dossier(tmp_path, ns, queue)

        assert result.success is False
        assert result.dossier is None
        assert len(result.errors) == 1
        error_message = result.errors[0]
        # The GENERIC branch's contract: a bare `str(exc)`, never the
        # manifest-schema template's "Fix your expected-artifacts.yaml."
        # suffix or an `expected-artifacts.yaml is schema-invalid` framing --
        # this is a real indexer bug, not an author-fixable manifest typo.
        assert error_message == str(artifact_ref_error)
        assert "expected-artifacts.yaml" not in error_message, error_message
        assert "Fix your expected-artifacts.yaml" not in error_message, error_message

        # Must hit the generic ERROR-level `logger.exception(...)` branch --
        # the whole point of NOT catching this as a manifest-schema failure.
        error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert error_records, caplog.text
        assert any("Indexer failed" in r.getMessage() for r in error_records), caplog.text
        # Must NOT also emit the manifest-schema WARNING path.
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert not any(
            "expected-artifacts.yaml" in r.getMessage() for r in warning_records
        ), caplog.text

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

    @patch("specify_cli.sync.lint_report_staging.stage_charter_lint_report")
    def test_stages_lint_report_with_mission_slug(
        self,
        mock_stage: MagicMock,
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
        mock_emit_snapshot.return_value = None
        mock_prepare.return_value = []
        mock_stage.return_value = True

        ns = _make_namespace()
        queue = MagicMock()
        result = sync_feature_dossier(tmp_path, ns, queue)

        # Staging runs with this mission's feature_dir + slug, before indexing.
        mock_stage.assert_called_once_with(tmp_path, ns.mission_slug)
        assert result.success is True

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


# --- Real end-to-end: no mocked Indexer/ManifestRegistry (paula rank-3) ---


def test_real_load_manifest_schema_error_names_origin_through_sync_feature_dossier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """paula rank-3 (end-to-end, no hand-crafted exception): a REAL
    schema-invalid ``expected-artifacts.yaml``, routed through the REAL
    ``ManifestRegistry.load_manifest`` producer -- via the same
    ``_doctrine_repository`` fake-seam ``tests/dossier/test_manifest.py``
    uses to route a typo'd fixture in, not through any mocked
    ``Indexer``/``ManifestRegistry`` class (unlike
    ``TestSyncFeatureDossier``, this test function is NOT decorated with
    those class-level patches) -- must surface its origin file through
    ``sync_feature_dossier``'s ``DossierSyncResult.errors``.

    The CLI-side counterpart of this same real-producer path is
    ``tests/cli/commands/test_reconcile.py::TestLibraryApi::test_reconcile_reports_error_on_malformed_manifest``,
    which pins the equivalent ``reconcile_mission_dossier`` behavior with its
    own distinctive origin ("test-fixture") -- together the two tests prove
    BOTH consumers surface the origin from the one real producer, not just
    one of them.
    """
    import ruamel.yaml
    from charter.offering.missions.repository import ConfigResult

    import specify_cli.dossier.manifest as manifest_module
    from specify_cli.dossier.manifest import ManifestRegistry

    feature_dir = tmp_path / "047-real-e2e"
    feature_dir.mkdir()
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")

    content = "mission_type: software-dev\nrequired_alwyas: []\n"
    yaml = ruamel.yaml.YAML(typ="safe")
    parsed = yaml.load(content)
    distinctive_origin = "doctrine/software-dev/expected-artifacts.yaml (real-e2e)"

    class _FakeRepository:
        def get_expected_artifacts(self, mission: str) -> ConfigResult | None:
            return ConfigResult(content=content, origin=distinctive_origin, parsed=parsed)

    monkeypatch.setattr(manifest_module, "_doctrine_repository", lambda: _FakeRepository())
    ManifestRegistry.clear_cache()

    ns = _make_namespace()
    queue = MagicMock()
    queue.project_uuid = ns.project_uuid

    try:
        result = sync_feature_dossier(feature_dir, ns, queue)
    finally:
        ManifestRegistry.clear_cache()

    assert result.success is False
    assert result.dossier is None
    assert result.events_emitted == 0
    assert len(result.errors) == 1
    error_message = result.errors[0]
    assert distinctive_origin in error_message, error_message
    assert "required_alwyas" in error_message, error_message


# --- FR-004 binding regression: real, unmocked emitter calls (WP01 T006) ---
#
# These two tests deliberately do NOT rely on the class-level
# @patch("specify_cli.dossier.events.emit_artifact_indexed"/"emit_artifact_missing")
# decorators used elsewhere in this file: those patch in a plain MagicMock
# (no autospec=True / spec=), which accepts any keyword argument silently and
# would NOT go red if T004/T005's *args/**kwargs-bridge-removal parameter
# promotion were reverted. Instead, these call the REAL emit_artifact_indexed
# / emit_artifact_missing end-to-end via _emit_artifact_events (the same
# helper sync_feature_dossier uses), with only a fake dossier-emitter
# callable registered (mirrors tests/dossier/test_emitter_adapter.py's
# pattern) so no network/SaaS call is made. _emit_artifact_events wraps each
# emitter call in its own `except Exception` -- reverting the kwarg promotion
# makes dossier_pipeline.py's step_id=/required_status=/blocking= keyword
# calls raise TypeError at the real call boundary, which that broad except
# silently swallows as a logged warning. Only asserting on the captured
# payload content / events_emitted count (not merely "no exception raised")
# can observe that regression -- see plan.md's "FR-004 raise/report/refuse
# contract" section.


def test_emit_artifact_indexed_keyword_promotion_preserves_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1: dossier_pipeline.py's ``step_id=``/``required_status=`` keyword
    call to ``emit_artifact_indexed`` still binds to real parameters (not
    ``**kwargs``) after the legacy bridge's removal, and the values still
    land in the fired payload's ``context_diagnostics``/``step_id`` fields.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    captured: list[dict] = []

    def fake_emitter(**kwargs: object) -> dict:
        captured.append(dict(kwargs))
        return {"event_id": "e-1", **kwargs}

    reset_dossier_emitter()
    register_dossier_emitter(fake_emitter)
    try:
        artifact = _make_artifact("spec.md")
        dossier = _make_dossier([artifact])
        ns = _make_namespace()

        store = ProjectSyncStore(ns.project_uuid)
        layout = store.layout_generation()
        with store.unit_of_work() as unit:
            context = store.create_context()
            events_emitted = _emit_artifact_events(
                dossier,
                ns,
                "plan",
                ns.to_dict(),
                project_context=context,
                project_unit=unit,
                project_layout=layout,
            )
    finally:
        reset_dossier_emitter()

    assert events_emitted == 1
    assert len(captured) == 1
    payload = captured[0]["payload"]
    diagnostics = payload["context_diagnostics"]
    assert diagnostics["artifact_key"] == artifact.artifact_key
    assert diagnostics["required_status"] == artifact.required_status
    assert payload["step_id"] == "plan"


def test_emit_artifact_missing_blocking_short_circuit_survives_bridge_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC2: dossier_pipeline.py's ``blocking=artifact.required_status ==
    "required"`` keyword call to ``emit_artifact_missing`` still binds to a
    real parameter after the legacy bridge's removal -- a required (blocking)
    missing artifact fires and is counted in ``events_emitted``; an optional
    (non-blocking) one short-circuits (``emit_artifact_missing`` returns
    ``None``) and is NOT counted.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    captured: list[dict] = []

    def fake_emitter(**kwargs: object) -> dict:
        captured.append(dict(kwargs))
        return {"event_id": "e-1", **kwargs}

    reset_dossier_emitter()
    register_dossier_emitter(fake_emitter)
    try:
        required_missing = ArtifactRef(
            artifact_key="input.plan",
            artifact_class="input",
            relative_path="plan.md",
            content_hash_sha256="",
            size_bytes=0,
            required_status="required",
            is_present=False,
            error_reason="not_found",
        )
        optional_missing = ArtifactRef(
            artifact_key="input.notes",
            artifact_class="input",
            relative_path="notes.md",
            content_hash_sha256="",
            size_bytes=0,
            required_status="optional",
            is_present=False,
            error_reason="not_found",
        )
        dossier = _make_dossier([required_missing, optional_missing])
        ns = _make_namespace()

        store = ProjectSyncStore(ns.project_uuid)
        layout = store.layout_generation()
        with store.unit_of_work() as unit:
            context = store.create_context()
            events_emitted = _emit_artifact_events(
                dossier,
                ns,
                None,
                ns.to_dict(),
                project_context=context,
                project_unit=unit,
                project_layout=layout,
            )
    finally:
        reset_dossier_emitter()

    # Only the required (blocking=True) missing artifact fires an event;
    # the optional (blocking=False) one short-circuits inside
    # emit_artifact_missing and returns None, uncounted.
    assert events_emitted == 1
    assert len(captured) == 1
    assert captured[0]["aggregate_id"] == f"{ns.mission_slug}:plan.md"

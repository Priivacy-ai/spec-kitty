"""Tests for specify_cli.sync.body_upload module."""

from __future__ import annotations

import pytest
import hashlib
from pathlib import Path
from specify_cli.dossier.models import ArtifactRef
from specify_cli.sync.body_queue import OfflineBodyUploadQueue
from specify_cli.sync.body_upload import (
    MAX_INLINE_SIZE_BYTES,
    _check_format,
    _check_size_limit,
    _is_supported_surface,
    _read_and_rehash,
    prepare_body_uploads,
)
from specify_cli.sync.namespace import NamespaceRef, UploadOutcome, UploadStatus

pytestmark = pytest.mark.fast

def _ns() -> NamespaceRef:
    return NamespaceRef(
        project_uuid="uuid-1",
        mission_slug="047-feat",
        target_branch="main",
        mission_type="software-dev",
        manifest_version="1",
    )


_DUMMY_HASH = "a" * 64  # Valid 64-char hex string for ArtifactRef validation


def _artifact(
    relative_path: str = "spec.md",
    content_hash: str = _DUMMY_HASH,
    size_bytes: int = 100,
    is_present: bool = True,
    error_reason: str | None = None,
    artifact_key: str | None = None,
) -> ArtifactRef:
    # Generate a safe artifact_key (no slashes allowed by validator)
    if artifact_key is None:
        safe_key = relative_path.replace("/", ".").replace("-", "_")
        artifact_key = f"input.{safe_key}"
    return ArtifactRef(
        artifact_key=artifact_key,
        artifact_class="input",
        relative_path=relative_path,
        content_hash_sha256=content_hash,
        size_bytes=size_bytes,
        is_present=is_present,
        error_reason=error_reason,
    )


# --- Surface Filtering (T013) ---


class TestSurfaceFiltering:
    def test_spec_md_accepted(self) -> None:
        assert _is_supported_surface("spec.md") is True

    def test_plan_md_accepted(self) -> None:
        assert _is_supported_surface("plan.md") is True

    def test_tasks_md_accepted(self) -> None:
        assert _is_supported_surface("tasks.md") is True

    def test_research_md_accepted(self) -> None:
        assert _is_supported_surface("research.md") is True

    def test_quickstart_md_accepted(self) -> None:
        assert _is_supported_surface("quickstart.md") is True

    def test_data_model_md_accepted(self) -> None:
        assert _is_supported_surface("data-model.md") is True

    def test_wp_task_file_accepted(self) -> None:
        assert _is_supported_surface("tasks/WP01-setup.md") is True

    def test_wp_task_bare_accepted(self) -> None:
        assert _is_supported_surface("tasks/WP02.md") is True

    def test_wp_task_long_name_accepted(self) -> None:
        assert _is_supported_surface("tasks/WP16-very-long-name-here.md") is True

    def test_research_subdir_accepted(self) -> None:
        assert _is_supported_surface("research/deep/analysis.md") is True

    def test_contracts_accepted(self) -> None:
        assert _is_supported_surface("contracts/api.yaml") is True

    def test_checklists_accepted(self) -> None:
        assert _is_supported_surface("checklists/req.md") is True

    def test_meta_json_rejected(self) -> None:
        assert _is_supported_surface("meta.json") is False

    def test_unknown_file_rejected(self) -> None:
        assert _is_supported_surface("unknown.txt") is False

    def test_random_subdir_rejected(self) -> None:
        assert _is_supported_surface("other/file.md") is False

    def test_tasks_non_wp_rejected(self) -> None:
        assert _is_supported_surface("tasks/README.md") is False


# --- Format Filtering (T014) ---


class TestFormatFiltering:
    def test_md_accepted(self) -> None:
        assert _check_format("spec.md") is None

    def test_json_accepted(self) -> None:
        assert _check_format("data.json") is None

    def test_yaml_accepted(self) -> None:
        assert _check_format("config.yaml") is None

    def test_yml_accepted(self) -> None:
        assert _check_format("config.yml") is None

    def test_csv_accepted(self) -> None:
        assert _check_format("data.csv") is None

    def test_png_rejected(self) -> None:
        result = _check_format("image.png")
        assert result is not None
        assert result.status == UploadStatus.SKIPPED
        assert "unsupported_format" in result.reason

    def test_pdf_rejected(self) -> None:
        result = _check_format("doc.pdf")
        assert result is not None
        assert result.status == UploadStatus.SKIPPED

    def test_no_extension_rejected(self) -> None:
        result = _check_format("Makefile")
        assert result is not None
        assert result.status == UploadStatus.SKIPPED


# --- Size Limit (T015) ---


class TestSizeLimit:
    def test_under_limit_accepted(self) -> None:
        assert _check_size_limit("spec.md", 1000) is None

    def test_at_limit_accepted(self) -> None:
        assert _check_size_limit("spec.md", MAX_INLINE_SIZE_BYTES) is None

    def test_over_limit_rejected(self) -> None:
        result = _check_size_limit("spec.md", MAX_INLINE_SIZE_BYTES + 1)
        assert result is not None
        assert result.status == UploadStatus.SKIPPED
        assert "oversized" in result.reason


# --- Re-Hash Guard (T016) ---


class TestReHashGuard:
    def test_matching_hash_returns_content(self, tmp_path: Path) -> None:
        content = "# Hello World\n"
        file_path = tmp_path / "spec.md"
        file_path.write_text(content, encoding="utf-8")
        expected_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

        result = _read_and_rehash(tmp_path, "spec.md", expected_hash)
        assert isinstance(result, tuple)
        body, actual_hash = result
        assert body == content
        assert actual_hash == expected_hash

    def test_mismatched_hash_skipped(self, tmp_path: Path) -> None:
        file_path = tmp_path / "spec.md"
        file_path.write_text("original content", encoding="utf-8")

        result = _read_and_rehash(tmp_path, "spec.md", "wrong_hash")
        assert isinstance(result, UploadOutcome)
        assert result.status == UploadStatus.SKIPPED
        assert "content_hash_mismatch" in result.reason

    def test_deleted_file_skipped(self, tmp_path: Path) -> None:
        result = _read_and_rehash(tmp_path, "gone.md", "anyhash")
        assert isinstance(result, UploadOutcome)
        assert result.status == UploadStatus.SKIPPED
        assert "deleted_after_scan" in result.reason

    def test_binary_file_skipped(self, tmp_path: Path) -> None:
        file_path = tmp_path / "binary.md"
        binary_content = b"\x80\x81\x82\xff\xfe"
        file_path.write_bytes(binary_content)
        # Use the actual hash of the binary bytes so hash check passes
        # and we reach the UTF-8 decode check
        actual_hash = hashlib.sha256(binary_content).hexdigest()

        result = _read_and_rehash(tmp_path, "binary.md", actual_hash)
        assert isinstance(result, UploadOutcome)
        assert result.status == UploadStatus.SKIPPED
        assert "not_valid_utf8" in result.reason

    def test_permission_error_skipped(self, tmp_path: Path) -> None:
        file_path = tmp_path / "locked.md"
        file_path.write_text("content", encoding="utf-8")
        file_path.chmod(0o000)
        try:
            result = _read_and_rehash(tmp_path, "locked.md", "anyhash")
            assert isinstance(result, UploadOutcome)
            assert result.status == UploadStatus.SKIPPED
            assert "read_error" in result.reason
        finally:
            file_path.chmod(0o644)


# --- prepare_body_uploads() Orchestration (T017) ---


class TestPrepareBodyUploads:
    def test_full_pipeline_with_valid_artifact(self, tmp_path: Path) -> None:
        content = "# Spec\n"
        file_path = tmp_path / "spec.md"
        file_path.write_text(content, encoding="utf-8")
        content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

        artifact = _artifact(
            relative_path="spec.md",
            content_hash=content_hash,
            size_bytes=len(file_path.read_bytes()),
        )

        db = tmp_path / "queue.db"
        queue = OfflineBodyUploadQueue(db_path=db)

        outcomes = prepare_body_uploads(
            artifacts=[artifact],
            namespace_ref=_ns(),
            body_queue=queue,
            feature_dir=tmp_path,
        )

        assert len(outcomes) == 1
        assert outcomes[0].status == UploadStatus.QUEUED
        assert outcomes[0].artifact_path == "spec.md"

    def test_non_present_artifact_skipped(self, tmp_path: Path) -> None:
        artifact = _artifact(is_present=False, error_reason="not_found")

        db = tmp_path / "queue.db"
        queue = OfflineBodyUploadQueue(db_path=db)

        outcomes = prepare_body_uploads(
            artifacts=[artifact],
            namespace_ref=_ns(),
            body_queue=queue,
            feature_dir=tmp_path,
        )

        assert len(outcomes) == 1
        assert outcomes[0].status == UploadStatus.SKIPPED
        assert "not_present" in outcomes[0].reason

    def test_unsupported_surface_skipped(self, tmp_path: Path) -> None:
        artifact = _artifact(relative_path="meta.json")

        db = tmp_path / "queue.db"
        queue = OfflineBodyUploadQueue(db_path=db)

        outcomes = prepare_body_uploads(
            artifacts=[artifact],
            namespace_ref=_ns(),
            body_queue=queue,
            feature_dir=tmp_path,
        )

        assert len(outcomes) == 1
        assert outcomes[0].status == UploadStatus.SKIPPED
        assert "unsupported_surface" in outcomes[0].reason

    def test_unsupported_format_skipped(self, tmp_path: Path) -> None:
        artifact = _artifact(relative_path="research/image.png")

        db = tmp_path / "queue.db"
        queue = OfflineBodyUploadQueue(db_path=db)

        outcomes = prepare_body_uploads(
            artifacts=[artifact],
            namespace_ref=_ns(),
            body_queue=queue,
            feature_dir=tmp_path,
        )

        assert len(outcomes) == 1
        assert outcomes[0].status == UploadStatus.SKIPPED
        assert "unsupported_format" in outcomes[0].reason

    def test_oversized_skipped(self, tmp_path: Path) -> None:
        artifact = _artifact(
            relative_path="spec.md",
            size_bytes=MAX_INLINE_SIZE_BYTES + 1,
        )

        db = tmp_path / "queue.db"
        queue = OfflineBodyUploadQueue(db_path=db)

        outcomes = prepare_body_uploads(
            artifacts=[artifact],
            namespace_ref=_ns(),
            body_queue=queue,
            feature_dir=tmp_path,
        )

        assert len(outcomes) == 1
        assert outcomes[0].status == UploadStatus.SKIPPED
        assert "oversized" in outcomes[0].reason

    def test_outcome_count_matches_artifact_count(self, tmp_path: Path) -> None:
        content = "# Spec\n"
        file_path = tmp_path / "spec.md"
        file_path.write_text(content, encoding="utf-8")
        content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

        artifacts = [
            _artifact(
                relative_path="spec.md",
                content_hash=content_hash,
                size_bytes=len(file_path.read_bytes()),
            ),
            _artifact(relative_path="meta.json"),  # unsupported surface
            _artifact(is_present=False),  # not present
        ]

        db = tmp_path / "queue.db"
        queue = OfflineBodyUploadQueue(db_path=db)

        outcomes = prepare_body_uploads(
            artifacts=artifacts,
            namespace_ref=_ns(),
            body_queue=queue,
            feature_dir=tmp_path,
        )

        assert len(outcomes) == len(artifacts)

    def test_duplicate_enqueue_returns_already_exists(self, tmp_path: Path) -> None:
        content = "# Spec\n"
        file_path = tmp_path / "spec.md"
        file_path.write_text(content, encoding="utf-8")
        content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

        artifact = _artifact(
            relative_path="spec.md",
            content_hash=content_hash,
            size_bytes=len(file_path.read_bytes()),
        )

        db = tmp_path / "queue.db"
        queue = OfflineBodyUploadQueue(db_path=db)
        ns = _ns()

        # First call enqueues
        outcomes1 = prepare_body_uploads([artifact], ns, queue, tmp_path)
        assert outcomes1[0].status == UploadStatus.QUEUED

        # Second call detects duplicate
        outcomes2 = prepare_body_uploads([artifact], ns, queue, tmp_path)
        assert outcomes2[0].status == UploadStatus.ALREADY_EXISTS

    def test_queue_full_returns_failed(self, tmp_path: Path) -> None:
        spec_path = tmp_path / "spec.md"
        spec_path.write_text("# Spec\n", encoding="utf-8")
        spec_hash = hashlib.sha256(spec_path.read_bytes()).hexdigest()

        plan_path = tmp_path / "plan.md"
        plan_path.write_text("# Plan\n", encoding="utf-8")
        plan_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()

        queue = OfflineBodyUploadQueue(
            db_path=tmp_path / "queue.db",
            max_queue_size=1,
        )

        first = prepare_body_uploads(
            [
                _artifact(
                    relative_path="spec.md",
                    content_hash=spec_hash,
                    size_bytes=len(spec_path.read_bytes()),
                )
            ],
            _ns(),
            queue,
            tmp_path,
        )
        assert first[0].status == UploadStatus.QUEUED

        second = prepare_body_uploads(
            [
                _artifact(
                    relative_path="plan.md",
                    content_hash=plan_hash,
                    size_bytes=len(plan_path.read_bytes()),
                )
            ],
            _ns(),
            queue,
            tmp_path,
        )
        assert second[0].status == UploadStatus.FAILED
        assert second[0].reason == "queue_full"

    def test_hash_mismatch_skipped(self, tmp_path: Path) -> None:
        file_path = tmp_path / "spec.md"
        file_path.write_text("original", encoding="utf-8")

        artifact = _artifact(
            relative_path="spec.md",
            content_hash="b" * 64,  # Valid hex but won't match file content
            size_bytes=8,
        )

        db = tmp_path / "queue.db"
        queue = OfflineBodyUploadQueue(db_path=db)

        outcomes = prepare_body_uploads([artifact], _ns(), queue, tmp_path)
        assert outcomes[0].status == UploadStatus.SKIPPED
        assert "content_hash_mismatch" in outcomes[0].reason

    def test_zero_byte_artifact_skipped(self, tmp_path: Path) -> None:
        file_path = tmp_path / "research.md"
        file_path.write_text("", encoding="utf-8")
        content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

        artifact = _artifact(
            relative_path="research.md",
            content_hash=content_hash,
            size_bytes=0,
        )

        queue = OfflineBodyUploadQueue(db_path=tmp_path / "queue.db")
        outcomes = prepare_body_uploads([artifact], _ns(), queue, tmp_path)

        assert outcomes[0].status == UploadStatus.SKIPPED
        assert outcomes[0].reason == "empty_content"
        assert queue.size() == 0

    def test_wp_task_file_accepted_in_pipeline(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        content = "# WP01\n"
        file_path = tasks_dir / "WP01-setup.md"
        file_path.write_text(content, encoding="utf-8")
        content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

        artifact = _artifact(
            relative_path="tasks/WP01-setup.md",
            content_hash=content_hash,
            size_bytes=len(file_path.read_bytes()),
        )

        db = tmp_path / "queue.db"
        queue = OfflineBodyUploadQueue(db_path=db)

        outcomes = prepare_body_uploads([artifact], _ns(), queue, tmp_path)
        assert outcomes[0].status == UploadStatus.QUEUED

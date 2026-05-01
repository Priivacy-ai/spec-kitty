"""End-to-end integration tests for body upload pipeline.

Covers success criteria SC-001 through SC-006 from the spec:
- SC-001: Online sync delivers supported bodies
- SC-002: Namespace isolation across features
- SC-003: Offline replay survives restart
- SC-004: Idempotent sync (no duplicates)
- SC-005: 404 index_entry_not_found retry/recovery
- SC-006: Non-UTF-8 and binary files skip safely
"""

from __future__ import annotations

import pytest
import hashlib
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch


from specify_cli.sync.body_queue import OfflineBodyUploadQueue
from specify_cli.sync.body_upload import prepare_body_uploads
from specify_cli.sync.namespace import NamespaceRef, UploadOutcome, UploadStatus

pytestmark = pytest.mark.fast


def _ns(
    mission_slug: str = "047-feat",
    target_branch: str = "main",
    project_uuid: str = "uuid-1",
) -> NamespaceRef:
    return NamespaceRef(
        project_uuid=project_uuid,
        mission_slug=mission_slug,
        target_branch=target_branch,
        mission_type="software-dev",
        manifest_version="1",
    )


_DUMMY_HASH = "a" * 64


def _artifact(
    relative_path: str = "spec.md",
    content_hash: str = _DUMMY_HASH,
    size_bytes: int = 100,
    is_present: bool = True,
    error_reason: str | None = None,
):
    from specify_cli.dossier.models import ArtifactRef

    safe_key = relative_path.replace("/", ".").replace("-", "_")
    return ArtifactRef(
        artifact_key=f"input.{safe_key}",
        artifact_class="input",
        relative_path=relative_path,
        content_hash_sha256=content_hash,
        size_bytes=size_bytes,
        is_present=is_present,
        error_reason=error_reason,
    )


def _write_file(feature_dir: Path, relative_path: str, content: str) -> str:
    """Write file and return its SHA-256 hash."""
    file_path = feature_dir / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def _make_service(
    tmp_path: Path,
    auth_token: str | None = "test-token",
):
    """Create a BackgroundSyncService with real body queue and mocked dependencies.

    The sync→async auth bridge (``_fetch_access_token_sync``) is patched at the
    module level so tests can control what the service sees without needing a
    real ``TokenManager``.
    """
    from specify_cli.sync import background as bg_mod
    from specify_cli.sync.background import BackgroundSyncService
    from specify_cli.sync.queue import OfflineQueue

    db_path = tmp_path / "queue.db"
    event_queue = OfflineQueue(db_path=db_path)
    body_queue = OfflineBodyUploadQueue(db_path=db_path)

    mock_config = MagicMock()
    mock_config.get_server_url.return_value = "https://test.example.com"

    # Patch the token-fetch bridge at the module level. Tests that want to
    # simulate the unauthenticated state pass ``auth_token=None``.
    bg_mod._fetch_access_token_sync = MagicMock(return_value=auth_token)

    service = BackgroundSyncService(
        queue=event_queue,
        config=mock_config,
    )
    service._body_queue = body_queue
    return service


# --- SC-001: Online sync delivers supported bodies ---


class TestSC001OnlineSync:
    def test_all_supported_text_artifacts_queued(self, tmp_path: Path) -> None:
        """After prepare_body_uploads, all supported text artifacts are queued."""
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()

        hash_spec = _write_file(feature_dir, "spec.md", "# Spec\nContent")
        hash_plan = _write_file(feature_dir, "plan.md", "# Plan\nArch")
        hash_tasks = _write_file(feature_dir, "tasks.md", "# Tasks\nWP list")
        hash_wp = _write_file(feature_dir, "tasks/WP01-setup.md", "# WP01")
        hash_research = _write_file(feature_dir, "research/analysis.md", "# Analysis")
        hash_contract = _write_file(feature_dir, "contracts/api.yaml", "openapi: '3.0'")

        artifacts = [
            _artifact("spec.md", hash_spec, len(b"# Spec\nContent")),
            _artifact("plan.md", hash_plan, len(b"# Plan\nArch")),
            _artifact("tasks.md", hash_tasks, len(b"# Tasks\nWP list")),
            _artifact("tasks/WP01-setup.md", hash_wp, len(b"# WP01")),
            _artifact("research/analysis.md", hash_research, len(b"# Analysis")),
            _artifact("contracts/api.yaml", hash_contract, len(b"openapi: '3.0'")),
        ]

        queue = OfflineBodyUploadQueue(db_path=tmp_path / "q.db")
        outcomes = prepare_body_uploads(artifacts, _ns(), queue, feature_dir)

        queued = [o for o in outcomes if o.status == UploadStatus.QUEUED]
        assert len(queued) == 6

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_drain_delivers_to_saas(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Queued bodies are delivered via push_content during drain."""
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()
        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc",
        )

        service = _make_service(tmp_path)
        assert service._body_queue is not None

        # Enqueue a task
        service._body_queue.enqueue(
            namespace=_ns(),
            artifact_path="spec.md",
            content_hash="abc123",
            content_body="# Spec\n",
            size_bytes=8,
        )

        service._sync_once()

        mock_push.assert_called_once()
        stats = service._body_queue.get_stats()
        assert stats.total_count == 0  # Drained


# --- SC-002: Namespace isolation ---


class TestSC002NamespaceIsolation:
    def test_different_features_isolated(self, tmp_path: Path) -> None:
        """Two features with same artifact names produce separate queue entries."""
        queue = OfflineBodyUploadQueue(db_path=tmp_path / "q.db")

        feature_a = tmp_path / "feat_a"
        feature_a.mkdir()
        hash_a = _write_file(feature_a, "spec.md", "# Feature A")

        feature_b = tmp_path / "feat_b"
        feature_b.mkdir()
        hash_b = _write_file(feature_b, "spec.md", "# Feature B")

        ns_a = _ns(mission_slug="feat-a")
        ns_b = _ns(mission_slug="feat-b")

        art_a = _artifact("spec.md", hash_a, len(b"# Feature A"))
        art_b = _artifact("spec.md", hash_b, len(b"# Feature B"))

        outcomes_a = prepare_body_uploads([art_a], ns_a, queue, feature_a)
        outcomes_b = prepare_body_uploads([art_b], ns_b, queue, feature_b)

        assert outcomes_a[0].status == UploadStatus.QUEUED
        assert outcomes_b[0].status == UploadStatus.QUEUED

        stats = queue.get_stats()
        assert stats.total_count == 2

    def test_different_branches_isolated(self, tmp_path: Path) -> None:
        """Same feature, different branches produce separate queue entries."""
        queue = OfflineBodyUploadQueue(db_path=tmp_path / "q.db")

        feature_dir = tmp_path / "feat"
        feature_dir.mkdir()
        content_hash = _write_file(feature_dir, "spec.md", "# Spec")

        ns_main = _ns(target_branch="main")
        ns_dev = _ns(target_branch="develop")

        art = _artifact("spec.md", content_hash, len(b"# Spec"))

        o1 = prepare_body_uploads([art], ns_main, queue, feature_dir)
        o2 = prepare_body_uploads([art], ns_dev, queue, feature_dir)

        assert o1[0].status == UploadStatus.QUEUED
        assert o2[0].status == UploadStatus.QUEUED
        assert queue.get_stats().total_count == 2


# --- SC-003: Offline replay survives restart ---


class TestSC003OfflineReplay:
    def test_queued_uploads_persist_across_reopen(self, tmp_path: Path) -> None:
        """Tasks survive queue close and reopen (process restart simulation)."""
        db_path = tmp_path / "q.db"

        # Enqueue with first queue instance
        queue1 = OfflineBodyUploadQueue(db_path=db_path)
        queue1.enqueue(
            namespace=_ns(),
            artifact_path="spec.md",
            content_hash="abc123",
            content_body="# Spec\n",
            size_bytes=8,
        )
        del queue1

        # Reopen with fresh instance (simulates restart)
        queue2 = OfflineBodyUploadQueue(db_path=db_path)
        tasks = queue2.drain(limit=10)
        assert len(tasks) == 1
        assert tasks[0].artifact_path == "spec.md"
        assert tasks[0].content_body == "# Spec\n"

    def test_retry_state_persists(self, tmp_path: Path) -> None:
        """Retry count and backoff survive restart."""
        db_path = tmp_path / "q.db"

        queue1 = OfflineBodyUploadQueue(db_path=db_path)
        queue1.enqueue(
            namespace=_ns(),
            artifact_path="spec.md",
            content_hash="abc123",
            content_body="# Spec\n",
            size_bytes=8,
        )
        tasks = queue1.drain(limit=10)
        queue1.mark_failed_retryable(tasks[0].row_id, "timeout")
        del queue1

        # Reopen
        queue2 = OfflineBodyUploadQueue(db_path=db_path)
        stats = queue2.get_stats()
        assert stats.total_count == 1
        assert stats.max_retry_count == 1
        assert stats.backoff_count == 1


# --- SC-004: Idempotent sync ---


class TestSC004Idempotent:
    def test_duplicate_enqueue_returns_already_exists(self, tmp_path: Path) -> None:
        """Second enqueue of same namespace+path+hash is deduplicated."""
        queue = OfflineBodyUploadQueue(db_path=tmp_path / "q.db")

        feature_dir = tmp_path / "feat"
        feature_dir.mkdir()
        content_hash = _write_file(feature_dir, "spec.md", "# Spec")

        ns = _ns()
        art = _artifact("spec.md", content_hash, len(b"# Spec"))

        o1 = prepare_body_uploads([art], ns, queue, feature_dir)
        o2 = prepare_body_uploads([art], ns, queue, feature_dir)

        assert o1[0].status == UploadStatus.QUEUED
        assert o2[0].status == UploadStatus.ALREADY_EXISTS
        assert queue.get_stats().total_count == 1

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_already_exists_from_server_removes_task(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Server returning 200 (already_exists) removes task from queue."""
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()
        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.ALREADY_EXISTS,
            reason="already_exists",
            content_hash="abc",
        )

        service = _make_service(tmp_path)
        assert service._body_queue is not None
        service._body_queue.enqueue(
            namespace=_ns(),
            artifact_path="spec.md",
            content_hash="abc",
            content_body="# Spec\n",
            size_bytes=8,
        )

        service._sync_once()

        assert service._body_queue.get_stats().total_count == 0


# --- SC-005: 404 index_entry_not_found recovery ---


class TestSC005RetryRecovery:
    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_retryable_failure_keeps_task_for_next_cycle(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """404 index_entry_not_found (retryable) keeps task queued for retry."""
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()
        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.FAILED,
            reason="index_entry_not_found",
            content_hash="abc",
            retryable=True,
        )

        service = _make_service(tmp_path)
        assert service._body_queue is not None
        service._body_queue.enqueue(
            namespace=_ns(),
            artifact_path="spec.md",
            content_hash="abc",
            content_body="# Spec\n",
            size_bytes=8,
        )

        service._sync_once()

        stats = service._body_queue.get_stats()
        assert stats.total_count == 1
        assert stats.max_retry_count == 1

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_retry_then_success(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Task fails on first attempt, succeeds on second."""
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()

        service = _make_service(tmp_path)
        assert service._body_queue is not None
        service._body_queue.enqueue(
            namespace=_ns(),
            artifact_path="spec.md",
            content_hash="abc",
            content_body="# Spec\n",
            size_bytes=8,
        )

        # First call: retryable failure
        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.FAILED,
            reason="index_entry_not_found",
            content_hash="abc",
            retryable=True,
        )
        service._sync_once()
        assert service._body_queue.get_stats().total_count == 1

        # Reset backoff so task is drainable
        conn = sqlite3.connect(service._body_queue.db_path)
        try:
            conn.execute("UPDATE body_upload_queue SET next_attempt_at = 0")
            conn.commit()
        finally:
            conn.close()

        # Second call: success
        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc",
        )
        service._sync_once()
        assert service._body_queue.get_stats().total_count == 0

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_auth_expiry_then_success(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """401 (retryable) → auth refresh → 201."""
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()

        service = _make_service(tmp_path)
        assert service._body_queue is not None
        service._body_queue.enqueue(
            namespace=_ns(),
            artifact_path="spec.md",
            content_hash="abc",
            content_body="# Spec\n",
            size_bytes=8,
        )

        # First: 401
        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.FAILED,
            reason="unauthorized",
            content_hash="abc",
            retryable=True,
        )
        service._sync_once()
        assert service._body_queue.get_stats().total_count == 1

        # Clear backoff
        conn = sqlite3.connect(service._body_queue.db_path)
        try:
            conn.execute("UPDATE body_upload_queue SET next_attempt_at = 0")
            conn.commit()
        finally:
            conn.close()

        # Second: success (auth refreshed)
        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc",
        )
        service._sync_once()
        assert service._body_queue.get_stats().total_count == 0

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_rate_limit_then_success(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """429 (retryable) → backoff → 201."""
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()

        service = _make_service(tmp_path)
        assert service._body_queue is not None
        service._body_queue.enqueue(
            namespace=_ns(),
            artifact_path="spec.md",
            content_hash="abc",
            content_body="# Spec\n",
            size_bytes=8,
        )

        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.FAILED,
            reason="rate_limited",
            content_hash="abc",
            retryable=True,
        )
        service._sync_once()
        assert service._body_queue.get_stats().total_count == 1

        conn = sqlite3.connect(service._body_queue.db_path)
        try:
            conn.execute("UPDATE body_upload_queue SET next_attempt_at = 0")
            conn.commit()
        finally:
            conn.close()

        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc",
        )
        service._sync_once()
        assert service._body_queue.get_stats().total_count == 0

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_server_error_then_success(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """500 (retryable) → backoff → 201."""
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()

        service = _make_service(tmp_path)
        assert service._body_queue is not None
        service._body_queue.enqueue(
            namespace=_ns(),
            artifact_path="spec.md",
            content_hash="abc",
            content_body="# Spec\n",
            size_bytes=8,
        )

        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.FAILED,
            reason="server_error: 500",
            content_hash="abc",
            retryable=True,
        )
        service._sync_once()
        assert service._body_queue.get_stats().total_count == 1

        conn = sqlite3.connect(service._body_queue.db_path)
        try:
            conn.execute("UPDATE body_upload_queue SET next_attempt_at = 0")
            conn.commit()
        finally:
            conn.close()

        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc",
        )
        service._sync_once()
        assert service._body_queue.get_stats().total_count == 0


# --- SC-006: Non-UTF-8 and binary files skip safely ---


class TestSC006UnsupportedFilesSkip:
    def test_binary_png_skipped(self, tmp_path: Path) -> None:
        """Binary .png file in supported surface is skipped (format filter)."""
        feature_dir = tmp_path / "feat"
        feature_dir.mkdir()
        (feature_dir / "research").mkdir()
        (feature_dir / "research" / "image.png").write_bytes(b"\x89PNG\r\n")

        art = _artifact("research/image.png", _DUMMY_HASH, 6)
        queue = OfflineBodyUploadQueue(db_path=tmp_path / "q.db")
        outcomes = prepare_body_uploads([art], _ns(), queue, feature_dir)

        assert len(outcomes) == 1
        assert outcomes[0].status == UploadStatus.SKIPPED
        assert "unsupported_format" in outcomes[0].reason

    def test_non_utf8_md_skipped(self, tmp_path: Path) -> None:
        """Markdown file with non-UTF-8 bytes is skipped (re-hash guard)."""
        feature_dir = tmp_path / "feat"
        feature_dir.mkdir()
        binary_content = b"\x80\x81\x82\xff\xfe"
        (feature_dir / "spec.md").write_bytes(binary_content)
        actual_hash = hashlib.sha256(binary_content).hexdigest()

        art = _artifact("spec.md", actual_hash, len(binary_content))
        queue = OfflineBodyUploadQueue(db_path=tmp_path / "q.db")
        outcomes = prepare_body_uploads([art], _ns(), queue, feature_dir)

        assert len(outcomes) == 1
        assert outcomes[0].status == UploadStatus.SKIPPED
        assert "not_valid_utf8" in outcomes[0].reason

    def test_oversized_md_skipped_with_reason(self, tmp_path: Path) -> None:
        """Oversized .md file is skipped with explicit reason."""
        from specify_cli.sync.body_upload import MAX_INLINE_SIZE_BYTES

        feature_dir = tmp_path / "feat"
        feature_dir.mkdir()

        art = _artifact("spec.md", _DUMMY_HASH, MAX_INLINE_SIZE_BYTES + 1)
        queue = OfflineBodyUploadQueue(db_path=tmp_path / "q.db")
        outcomes = prepare_body_uploads([art], _ns(), queue, feature_dir)

        assert len(outcomes) == 1
        assert outcomes[0].status == UploadStatus.SKIPPED
        assert "oversized" in outcomes[0].reason

    def test_unsupported_surface_skipped(self, tmp_path: Path) -> None:
        """File not in supported surfaces list is skipped."""
        feature_dir = tmp_path / "feat"
        feature_dir.mkdir()

        art = _artifact("meta.json", _DUMMY_HASH, 50)
        queue = OfflineBodyUploadQueue(db_path=tmp_path / "q.db")
        outcomes = prepare_body_uploads([art], _ns(), queue, feature_dir)

        assert len(outcomes) == 1
        assert outcomes[0].status == UploadStatus.SKIPPED
        assert "unsupported_surface" in outcomes[0].reason

    def test_mixed_supported_and_unsupported(self, tmp_path: Path) -> None:
        """Pipeline handles mix of supported and unsupported artifacts."""
        feature_dir = tmp_path / "feat"
        feature_dir.mkdir()
        (feature_dir / "research").mkdir()

        hash_spec = _write_file(feature_dir, "spec.md", "# Spec")
        (feature_dir / "research" / "image.png").write_bytes(b"\x89PNG\r\n")

        artifacts = [
            _artifact("spec.md", hash_spec, len(b"# Spec")),
            _artifact("research/image.png", _DUMMY_HASH, 6),
            _artifact("meta.json", _DUMMY_HASH, 50),
        ]

        queue = OfflineBodyUploadQueue(db_path=tmp_path / "q.db")
        outcomes = prepare_body_uploads(artifacts, _ns(), queue, feature_dir)

        assert len(outcomes) == 3
        statuses = {o.artifact_path: o.status for o in outcomes}
        assert statuses["spec.md"] == UploadStatus.QUEUED
        assert statuses["research/image.png"] == UploadStatus.SKIPPED
        assert statuses["meta.json"] == UploadStatus.SKIPPED


# --- Full pipeline: dossier_pipeline → background drain ---


class TestFullPipeline:
    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_enqueue_then_drain(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Full pipeline: prepare_body_uploads enqueues, _sync_once drains."""
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()

        feature_dir = tmp_path / "feat"
        feature_dir.mkdir()
        hash_spec = _write_file(feature_dir, "spec.md", "# Spec content")
        hash_plan = _write_file(feature_dir, "plan.md", "# Plan content")

        artifacts = [
            _artifact("spec.md", hash_spec, len(b"# Spec content")),
            _artifact("plan.md", hash_plan, len(b"# Plan content")),
        ]

        service = _make_service(tmp_path)
        assert service._body_queue is not None

        # Enqueue via pipeline
        outcomes = prepare_body_uploads(
            artifacts,
            _ns(),
            service._body_queue,
            feature_dir,
        )
        assert sum(1 for o in outcomes if o.status == UploadStatus.QUEUED) == 2

        # Drain via background sync
        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc",
        )
        service._sync_once()

        assert mock_push.call_count == 2
        assert service._body_queue.get_stats().total_count == 0

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_permanent_failure_removed(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Non-retryable failure (400 bad_request) permanently removes task."""
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()

        service = _make_service(tmp_path)
        assert service._body_queue is not None
        service._body_queue.enqueue(
            namespace=_ns(),
            artifact_path="spec.md",
            content_hash="abc",
            content_body="# Spec\n",
            size_bytes=8,
        )

        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.FAILED,
            reason="bad_request: invalid payload",
            content_hash="abc",
            retryable=False,
        )
        service._sync_once()

        assert service._body_queue.get_stats().total_count == 0

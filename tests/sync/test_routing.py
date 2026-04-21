"""Tests for checkout-level sync routing and opt-out behavior."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from specify_cli.sync.body_queue import OfflineBodyUploadQueue
from specify_cli.sync.namespace import NamespaceRef
from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.routing import (
    disable_checkout_sync,
    resolve_checkout_sync_routing,
    write_local_sync_enabled,
)

pytestmark = pytest.mark.fast


def _write_repo_config(repo_root: Path, *, project_uuid: str | None = None, repo_slug: str = "acme/spec-kitty") -> None:
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    if project_uuid is None:
        project_uuid = str(uuid4())
    (config_dir / "config.yaml").write_text(
        "\n".join(
            [
                "project:",
                f"  uuid: {project_uuid}",
                "  slug: spec-kitty-local",
                "  node_id: node12345678",
                f"  repo_slug: {repo_slug}",
                "  build_id: build-123",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_resolve_checkout_sync_routing_uses_global_repo_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    _write_repo_config(repo_root)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(repo_root)

    config_file = home / ".spec-kitty" / "config.toml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        '[sync.repo_defaults."acme/spec-kitty"]\nenabled = false\n',
        encoding="utf-8",
    )

    routing = resolve_checkout_sync_routing()

    assert routing is not None
    assert routing.repo_slug == "acme/spec-kitty"
    assert routing.local_sync_enabled is None
    assert routing.repo_default_sync_enabled is False
    assert routing.effective_sync_enabled is False


def test_local_override_beats_global_repo_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    _write_repo_config(repo_root)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(repo_root)

    config_file = home / ".spec-kitty" / "config.toml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        '[sync.repo_defaults."acme/spec-kitty"]\nenabled = false\n',
        encoding="utf-8",
    )
    write_local_sync_enabled(repo_root, True)

    routing = resolve_checkout_sync_routing()

    assert routing is not None
    assert routing.local_sync_enabled is True
    assert routing.repo_default_sync_enabled is False
    assert routing.effective_sync_enabled is True


def test_disable_checkout_sync_purges_only_matching_project_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    project_uuid = str(uuid4())
    _write_repo_config(repo_root, project_uuid=project_uuid)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(repo_root)

    queue = OfflineQueue()
    queue.queue_event(
        {
            "event_id": "evt-1",
            "event_type": "BuildRegistered",
            "project_uuid": project_uuid,
            "payload": {"project_uuid": project_uuid},
        }
    )
    queue.queue_event(
        {
            "event_id": "evt-2",
            "event_type": "BuildRegistered",
            "project_uuid": str(uuid4()),
            "payload": {"project_uuid": str(uuid4())},
        }
    )

    body_queue = OfflineBodyUploadQueue(db_path=queue.db_path)
    body_queue.enqueue(
        NamespaceRef(
            project_uuid=project_uuid,
            mission_slug="001-test",
            target_branch="main",
            mission_type="software-dev",
            manifest_version="1",
        ),
        artifact_path="spec.md",
        content_hash="abc123",
        content_body="# Spec\n",
        size_bytes=7,
    )
    body_queue.enqueue(
        NamespaceRef(
            project_uuid=str(uuid4()),
            mission_slug="001-test",
            target_branch="main",
            mission_type="software-dev",
            manifest_version="1",
        ),
        artifact_path="plan.md",
        content_hash="def456",
        content_body="# Plan\n",
        size_bytes=7,
    )

    result = disable_checkout_sync(repo_root)

    assert result.routing.effective_sync_enabled is False
    assert result.removed_events == 1
    assert result.removed_body_uploads == 1
    assert queue.size() == 1
    assert body_queue.size() == 1
    config_toml = (home / ".spec-kitty" / "config.toml").read_text(encoding="utf-8")
    assert "acme/spec-kitty" in config_toml
    assert "enabled = false" in config_toml

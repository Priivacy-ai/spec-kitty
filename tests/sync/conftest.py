"""Shared fixtures for sync module tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.clock import LamportClock
from specify_cli.sync.config import SyncConfig
from specify_cli.sync.git_metadata import GitMetadata, GitMetadataResolver
from specify_cli.sync.project_identity import ProjectIdentity


@pytest.fixture
def temp_queue(tmp_path: Path) -> OfflineQueue:
    """Temporary SQLite queue for testing."""
    db_path = tmp_path / "test_queue.db"
    return OfflineQueue(db_path=db_path)


@pytest.fixture
def mock_auth() -> MagicMock:
    """Mock AuthClient for testing."""
    auth = MagicMock()
    auth.is_authenticated.return_value = True
    auth.get_access_token.return_value = "test_token"
    auth.get_team_slug.return_value = "test-team"
    return auth


@pytest.fixture
def temp_clock(tmp_path: Path) -> LamportClock:
    """LamportClock persisted to tmp_path (avoids touching ~/.spec-kitty/)."""
    clock_path = tmp_path / "clock.json"
    return LamportClock(value=0, node_id="test-node-id", _storage_path=clock_path)


@pytest.fixture
def mock_config() -> MagicMock:
    """Mock SyncConfig that returns a local server URL."""
    config = MagicMock(spec=SyncConfig)
    config.get_server_url.return_value = "https://test.spec-kitty.dev"
    return config


@pytest.fixture
def mock_identity() -> ProjectIdentity:
    """Mock project identity with all fields populated."""
    return ProjectIdentity(
        project_uuid=uuid4(),
        project_slug="test-project",
        node_id="test-node-123",
    )


@pytest.fixture
def empty_identity() -> ProjectIdentity:
    """Empty project identity (no fields populated)."""
    return ProjectIdentity()


@pytest.fixture
def mock_git_metadata() -> GitMetadata:
    """Mock git metadata for testing."""
    return GitMetadata(
        git_branch="test-branch",
        head_commit_sha="a" * 40,
        repo_slug="test-org/test-repo",
    )


@pytest.fixture
def mock_git_resolver(mock_git_metadata: GitMetadata) -> MagicMock:
    """Mock GitMetadataResolver that returns fixed metadata."""
    resolver = MagicMock(spec=GitMetadataResolver)
    resolver.resolve.return_value = mock_git_metadata
    return resolver


@pytest.fixture
def emitter(
    temp_queue: OfflineQueue,
    mock_auth: MagicMock,
    temp_clock: LamportClock,
    mock_config: MagicMock,
    mock_identity: ProjectIdentity,
    mock_git_resolver: MagicMock,
) -> EventEmitter:
    """EventEmitter wired to temp queue, mock auth, isolated clock, mock identity, and mock git resolver."""
    em = EventEmitter(
        clock=temp_clock,
        config=mock_config,
        queue=temp_queue,
        _auth=mock_auth,
        ws_client=None,
        _identity=mock_identity,  # Pre-populate with mock identity
        _git_resolver=mock_git_resolver,  # Pre-populate with mock git resolver
    )
    return em


@pytest.fixture
def emitter_without_identity(
    temp_queue: OfflineQueue,
    mock_auth: MagicMock,
    temp_clock: LamportClock,
    mock_config: MagicMock,
    empty_identity: ProjectIdentity,
    mock_git_resolver: MagicMock,
) -> EventEmitter:
    """EventEmitter with empty identity (simulates non-project context)."""
    em = EventEmitter(
        clock=temp_clock,
        config=mock_config,
        queue=temp_queue,
        _auth=mock_auth,
        ws_client=None,
        _identity=empty_identity,  # Pre-populate with empty identity
        _git_resolver=mock_git_resolver,  # Pre-populate with mock git resolver
    )
    return em

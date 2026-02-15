"""Shared fixtures for integration tests."""

import pytest


@pytest.fixture
def clean_queue_and_session(tmp_path, monkeypatch):
    """Ensure clean queue and session for each test.

    This fixture redirects all file operations to tmp_path to prevent
    writing to ~/.spec-kitty during tests.
    """
    queue_dir = tmp_path / ".spec-kitty"
    queue_dir.mkdir(parents=True, exist_ok=True)

    # Monkey-patch get_queue_path
    def mock_get_queue_path(mission_id: str):
        return queue_dir / f"{mission_id}-queue.db"

    from specify_cli.events import store
    from specify_cli.events import replay as replay_module
    monkeypatch.setattr(store, "get_queue_path", mock_get_queue_path)
    monkeypatch.setattr(replay_module, "get_queue_path", mock_get_queue_path)

    # Monkey-patch session path
    def mock_get_session_path(mission_id: str):
        session_path = tmp_path / "sessions" / mission_id / "session.json"
        session_path.parent.mkdir(parents=True, exist_ok=True)
        return session_path

    from specify_cli.collaboration import session
    monkeypatch.setattr(session, "get_session_path", mock_get_session_path)

    yield tmp_path


@pytest.fixture
def clean_queue(tmp_path, monkeypatch):
    """Ensure clean queue for each test (session-agnostic)."""
    queue_dir = tmp_path / ".spec-kitty"
    queue_dir.mkdir(parents=True, exist_ok=True)

    # Monkey-patch get_queue_path to use temp directory
    def mock_get_queue_path(mission_id: str):
        queue_file = queue_dir / f"{mission_id}-queue.db"
        return queue_file

    from specify_cli.events import store
    from specify_cli.events import replay as replay_module
    monkeypatch.setattr(store, "get_queue_path", mock_get_queue_path)
    monkeypatch.setattr(replay_module, "get_queue_path", mock_get_queue_path)

    yield queue_dir

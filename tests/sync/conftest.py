"""Shared fixtures for sync module tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from specify_cli.core.env import SYNC_DISABLE_ENV_VARS
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
def mock_auth(monkeypatch) -> MagicMock:
    """Patched TokenManager accessor used by the sync layer.

    Post-WP08 the sync layer reaches for ``specify_cli.auth.get_token_manager``
    instead of the legacy ``AuthClient``. This fixture installs a MagicMock
    so tests that previously depended on ``is_authenticated`` / team slug
    lookups continue to see an authenticated state without needing a real
    ``StoredSession`` on disk.
    """
    # Build a session-like mock with a single default team.
    team = MagicMock()
    team.id = "test-team"
    team.slug = "test-team"

    session = MagicMock()
    session.default_team_id = "test-team"
    session.teams = [team]
    session.email = "tester@example.com"
    session.name = "Test User"

    tm = MagicMock()
    tm.is_authenticated = True
    tm.get_current_session.return_value = session

    def _get_tm():
        return tm

    # Patch the process-wide factory at its canonical location. This covers
    # every call site because all sync-layer modules call it via
    # ``from specify_cli.auth import get_token_manager`` rebinding each time.
    monkeypatch.setattr("specify_cli.auth.get_token_manager", _get_tm)
    return tm


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
        build_id="test-build-id-0000-0000-000000000001",
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
    resolver.repo_root = Path("/nonexistent/test-repo")
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
    """EventEmitter wired to temp queue, isolated clock, mock identity, and mock git resolver.

    ``mock_auth`` is included for its monkeypatch side-effect (installs a
    fake ``get_token_manager``); the emitter itself reaches for that
    accessor internally so no ``auth`` kwarg is needed post-WP08.
    """
    del mock_auth  # side-effect-only dependency
    em = EventEmitter(
        clock=temp_clock,
        config=mock_config,
        queue=temp_queue,
        ws_client=None,
        _identity=mock_identity,  # Pre-populate with mock identity
        _git_resolver=mock_git_resolver,  # Pre-populate with mock git resolver
    )
    return em


@pytest.fixture(autouse=True)
def _isolate_pre_review_gate_sync_toggles(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset the sync-disable toggles the pre-review gate reuses, per test (#2794/#2809).

    Mirrors the fixture at
    ``tests/specify_cli/cli/commands/agent/conftest.py`` (added under #2794).
    The pre-review regression gate reuses the sync layer's process-wide
    opt-outs ``SPEC_KITTY_SYNC_MINIMAL_IMPORT`` / ``SPEC_KITTY_SYNC_DISABLE``
    (the canonical ``core.env.SYNC_DISABLE_ENV_VARS``). In the
    whole-tree parallel run (``-n auto --dist loadfile``) one of those vars
    can be present in the xdist worker -- leaked mid-run from a sibling test
    or daemon path -- which silently *skips* sync-dependent assertions in
    ``tests/sync/`` and reds tests that assert a live sync diagnostic fired
    (issue #2809). Unsetting both toggles before every test in this package
    makes those tests worker- and order-independent, and neutralises the
    ``monkeypatch.setenv`` "restore-to-a-leaked-value" perpetuation.

    Tests that need a toggle set set it themselves inside the test body
    (after this fixture runs), so they are unaffected. No production
    behaviour changes -- this only isolates the test env.

    Note (#2782): this fixture only guards against a *leaked toggle*
    silently disabling sync. It does not -- and cannot -- paper over a
    genuine live-connection failure in the sync layer (e.g. a real
    ``Connection refused`` from the ``final_sync`` phase); that failure
    mode is tracked separately under #2782 and is orthogonal to what this
    fixture isolates.
    """
    for _name in SYNC_DISABLE_ENV_VARS:
        monkeypatch.delenv(_name, raising=False)


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
    del mock_auth  # side-effect-only dependency
    em = EventEmitter(
        clock=temp_clock,
        config=mock_config,
        queue=temp_queue,
        ws_client=None,
        _identity=empty_identity,  # Pre-populate with empty identity
        _git_resolver=mock_git_resolver,  # Pre-populate with mock git resolver
    )
    return em


@pytest.fixture(autouse=True)
def _consented_checkout_by_default(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Treat the checkout under test as consented, unless the test says otherwise.

    Consent became **opt-in** in spec-kitty#3030 (absorbing #3031): an
    unconfigured checkout now resolves ``effective_sync_enabled = False``, which
    is the fix for the 2026-07-27 breach where five never-opted-in projects were
    delivered to a hosted instance.

    Almost every test in this package exercises *transport* behaviour — batching,
    retry hygiene, error surfacing, offline replay — in a throwaway tmp repo that
    has no consent record and never had one. Under opt-in consent those tests
    short-circuit with ``sync_disabled`` before reaching the behaviour they
    assert, which is a fixture artefact, not a finding.

    This fixture restores their premise explicitly rather than weakening the
    production default. It patches only the batch/emit consent read, so:

    * consent itself is still covered, by suites that assert on the real
      resolver — ``tests/sync/test_routing.py`` and the upstream pins in
      ``tests/sync/test_sync_consent_default_deny.py``, neither of which calls
      the patched seam; and
    * a test that *wants* the denial can still opt out with
      ``monkeypatch.setattr(..., lambda *a, **k: False)``.

    Named rather than implicit so a future reader can tell that these suites
    assume consent, instead of inferring it from a green run.

    **Extended for #3030 M1/M1-1.** The emitter no longer reads
    ``is_sync_enabled_for_checkout`` at all: the capture gate, the drain-blocked
    classification and the WebSocket publish decision all resolve consent per project
    through ``EventEmitter._project_consents_to_capture``. Patching only the old seam
    would leave this fixture patching a name production never consults — green for the
    wrong reason — so the per-project predicate is patched too. The old seams stay
    listed with ``raising=False`` because ``sync/batch.py`` and ``sync/runtime.py``
    still have them.

    Most emitters in this package are built with no ``_identity``, so they resolve the
    *ambient* repo's uuid, for which a throwaway home has no record. That is what
    makes the premise a fixture concern rather than a per-test one.
    """
    # Never touch the suites that assert on the real predicate. Without this guard the
    # fixture would mask the very pins it must not weaken the moment they go green —
    # and a blanket grant is exactly the mutant those pins exist to catch.
    #
    # ``capture_gate`` is listed alongside ``consent`` because
    # ``test_capture_gate_project_identity_3030.py`` pins the per-project capture gate
    # bidirectionally without the word "consent" in its filename.
    protected = ("consent", "capture_gate")
    name = Path(str(request.node.fspath)).name
    if any(token in name for token in protected):
        return

    # ``sync/emitter.py`` is deliberately absent from this list: #3030 M1-1 removed the
    # import, so patching the name there would only *create* an attribute nothing
    # reads and imply the emitter still consults cwd.
    for seam in (
        "specify_cli.sync.batch.is_sync_enabled_for_checkout",
        "specify_cli.sync.runtime.is_sync_enabled_for_checkout",
    ):
        monkeypatch.setattr(seam, lambda *args, **kwargs: True, raising=False)

    monkeypatch.setattr(
        "specify_cli.sync.emitter.EventEmitter._project_consents_to_capture",
        lambda *args, **kwargs: True,
    )

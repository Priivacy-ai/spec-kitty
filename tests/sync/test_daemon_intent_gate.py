"""Tests for intent-gated daemon startup and caller audit guard.

Covers:
- Decision matrix (5 rows): every combination of rollout / intent / policy
- TypeError regression: ensure_sync_daemon_running() without intent= raises TypeError
- Audit-grep guard: no file outside the allowlist calls ensure_sync_daemon_running()
"""

from __future__ import annotations

from pathlib import Path
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.dashboard.handlers.api import APIHandler
from specify_cli.sync.config import BackgroundDaemonPolicy, SyncConfig
from specify_cli.sync.daemon import DaemonIntent, DaemonStartOutcome, ensure_sync_daemon_running

# ---------------------------------------------------------------------------
# Rollout fixtures (local copies — tests/saas/conftest.py is out of scope
# for the tests/sync/ package boundary without cross-package import gymnastics)
# ---------------------------------------------------------------------------


@pytest.fixture()
def rollout_disabled(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Override the global autouse flag — rollout is OFF for this test."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    yield


@pytest.fixture()
def rollout_enabled(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Ensure the rollout flag is ON for this test (idempotent with autouse)."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    yield


# ---------------------------------------------------------------------------
# Helper: build a SyncConfig stub with a fixed policy (no disk I/O)
# ---------------------------------------------------------------------------


def _config(policy: BackgroundDaemonPolicy) -> SyncConfig:
    cfg = MagicMock(spec=SyncConfig)
    cfg.get_background_daemon.return_value = policy
    return cfg  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Decision matrix tests
# ---------------------------------------------------------------------------


class TestDecisionMatrix:
    """One test per row in the decision matrix from contracts/background_daemon_policy.md."""

    # Row 1: rollout disabled → skipped_reason="rollout_disabled" regardless of intent/policy
    def test_row1_rollout_disabled(self, rollout_disabled: None) -> None:
        outcome = ensure_sync_daemon_running(
            intent=DaemonIntent.REMOTE_REQUIRED,
            config=_config(BackgroundDaemonPolicy.AUTO),
        )
        assert outcome.started is False
        assert outcome.skipped_reason == "rollout_disabled"
        assert outcome.pid is None

    # Row 2: rollout on + LOCAL_ONLY → skipped_reason="intent_local_only"
    def test_row2_local_only_intent(self, rollout_enabled: None) -> None:
        outcome = ensure_sync_daemon_running(
            intent=DaemonIntent.LOCAL_ONLY,
            config=_config(BackgroundDaemonPolicy.AUTO),
        )
        assert outcome.started is False
        assert outcome.skipped_reason == "intent_local_only"
        assert outcome.pid is None

    # Row 3: rollout on + REMOTE_REQUIRED + MANUAL → skipped_reason="policy_manual"
    def test_row3_policy_manual(self, rollout_enabled: None) -> None:
        outcome = ensure_sync_daemon_running(
            intent=DaemonIntent.REMOTE_REQUIRED,
            config=_config(BackgroundDaemonPolicy.MANUAL),
        )
        assert outcome.started is False
        assert outcome.skipped_reason == "policy_manual"
        assert outcome.pid is None

    # Row 4: rollout on + REMOTE_REQUIRED + AUTO → outcome.started=True (mocked inner start)
    def test_row4_auto_success(self, rollout_enabled: None, tmp_path: Path) -> None:
        fake_pid = 99999
        fake_url = "http://127.0.0.1:9400"
        fake_port = 9400
        fake_state_file = tmp_path / "sync-daemon"
        # Write a synthetic state file so _parse_daemon_file returns the fake PID
        fake_state_file.write_text(f"{fake_url}\n{fake_port}\ntok\n{fake_pid}\n", encoding="utf-8")

        # Stub the inner locked start call; let the real _parse_daemon_file read the state file
        with (
            patch(
                "specify_cli.sync.daemon._ensure_sync_daemon_running_locked",
                return_value=(fake_url, fake_port, True),
            ),
            patch("specify_cli.sync.daemon.DAEMON_STATE_FILE", fake_state_file),
            patch("specify_cli.sync.daemon.DAEMON_LOCK_FILE", tmp_path / "sync-daemon.lock"),
            patch("specify_cli.sync.daemon.SPEC_KITTY_DIR", tmp_path),
        ):
            outcome = ensure_sync_daemon_running(
                intent=DaemonIntent.REMOTE_REQUIRED,
                config=_config(BackgroundDaemonPolicy.AUTO),
            )

        assert outcome.started is True
        assert outcome.skipped_reason is None
        assert outcome.pid == fake_pid

    # Row 5: rollout on + REMOTE_REQUIRED + AUTO + inner start raises → start_failed
    def test_row5_auto_start_fails(self, rollout_enabled: None, tmp_path: Path) -> None:
        with (
            patch(
                "specify_cli.sync.daemon._ensure_sync_daemon_running_locked",
                side_effect=RuntimeError("port unavailable"),
            ),
            patch("specify_cli.sync.daemon.DAEMON_LOCK_FILE", tmp_path / "sync-daemon.lock"),
            patch("specify_cli.sync.daemon.SPEC_KITTY_DIR", tmp_path),
        ):
            outcome = ensure_sync_daemon_running(
                intent=DaemonIntent.REMOTE_REQUIRED,
                config=_config(BackgroundDaemonPolicy.AUTO),
            )

        assert outcome.started is False
        assert outcome.skipped_reason is not None
        assert outcome.skipped_reason.startswith("start_failed:")
        assert "port unavailable" in outcome.skipped_reason
        assert outcome.pid is None


# ---------------------------------------------------------------------------
# TypeError regression: intent is mandatory keyword-only
# ---------------------------------------------------------------------------


class TestIntentMandatory:
    def test_missing_intent_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            ensure_sync_daemon_running()  # type: ignore[call-arg]

    def test_positional_intent_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            ensure_sync_daemon_running(DaemonIntent.LOCAL_ONLY)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# DaemonStartOutcome dataclass contract
# ---------------------------------------------------------------------------


class TestDaemonStartOutcome:
    def test_is_frozen(self) -> None:
        outcome = DaemonStartOutcome(started=False, skipped_reason="rollout_disabled", pid=None)
        with pytest.raises(Exception):  # frozen dataclass raises on setattr
            outcome.started = True  # type: ignore[misc]

    def test_importable(self) -> None:
        from specify_cli.sync.daemon import DaemonIntent, DaemonStartOutcome  # noqa: F401

        assert DaemonIntent.LOCAL_ONLY.value == "local_only"
        assert DaemonIntent.REMOTE_REQUIRED.value == "remote_required"


# ---------------------------------------------------------------------------
# Dashboard sync-trigger response branches (diff-cover enforced)
# ---------------------------------------------------------------------------


def _api_handler(path: str, *, project_token: str | None = "tok") -> APIHandler:
    handler = APIHandler.__new__(APIHandler)
    handler.path = path
    handler.project_token = project_token
    handler._send_json = MagicMock()
    return handler


def test_dashboard_sync_trigger_manual_mode_returns_202() -> None:
    handler = _api_handler("/api/sync/trigger?token=tok")

    with patch(
        "specify_cli.dashboard.handlers.api.ensure_sync_daemon_running",
        return_value=DaemonStartOutcome(started=False, skipped_reason="policy_manual", pid=None),
    ):
        handler.handle_sync_trigger()

    handler._send_json.assert_called_once_with(
        202,
        {"status": "skipped", "manual_mode": True, "reason": "policy_manual"},
    )


def test_dashboard_sync_trigger_unavailable_reason_returns_503() -> None:
    handler = _api_handler("/api/sync/trigger?token=tok")

    with patch(
        "specify_cli.dashboard.handlers.api.ensure_sync_daemon_running",
        return_value=DaemonStartOutcome(started=False, skipped_reason="start_failed:port busy", pid=None),
    ):
        handler.handle_sync_trigger()

    handler._send_json.assert_called_once_with(
        503,
        {"error": "sync_daemon_unavailable", "reason": "start_failed:port busy"},
    )


# ---------------------------------------------------------------------------
# Audit-grep guard: no unauthorized callers of ensure_sync_daemon_running()
# ---------------------------------------------------------------------------

# Resolve repo root from this test file's location:
# tests/sync/test_daemon_intent_gate.py -> tests/sync -> tests -> repo_root
_THIS_FILE = Path(__file__).resolve()
REPO_ROOT = _THIS_FILE.parents[2]
SRC_ROOT = REPO_ROOT / "src" / "specify_cli"

# Authoritative allowlist — every file permitted to call ensure_sync_daemon_running().
# Pre-declares tracker.py for WP05 so WP04 and WP05 can merge in either order.
ALLOWED_CALL_SITES: set[str] = {
    "src/specify_cli/dashboard/server.py",
    "src/specify_cli/dashboard/handlers/api.py",
    "src/specify_cli/sync/events.py",
    "src/specify_cli/sync/daemon.py",  # the definition itself
    "src/specify_cli/cli/commands/tracker.py",  # added by WP05
}


def test_no_unauthorized_daemon_call_sites() -> None:
    """Walk src/specify_cli/ and assert no file outside the allowlist calls ensure_sync_daemon_running()."""
    hits: set[str] = set()
    for path in SRC_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "ensure_sync_daemon_running(" in text:
            rel = str(path.relative_to(REPO_ROOT))
            hits.add(rel)

    unauthorized = hits - ALLOWED_CALL_SITES
    assert not unauthorized, (
        f"Unauthorized callers of ensure_sync_daemon_running: {unauthorized!r}. "
        "Add to ALLOWED_CALL_SITES in tests/sync/test_daemon_intent_gate.py "
        "and to tasks/WP04 caller audit table if this new call site is intentional."
    )

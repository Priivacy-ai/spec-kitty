"""RED-first P0 reproduction of the sync-daemon escape-hatch gap in #2573.

The ``move-task --to for_review`` path has two synchronous latency sources
(issue #2573): the pre-review regression gate and the sync-daemon spawn
(``ensure_sync_daemon_running``). Ask (a) — a skip flag / disable env for the
pre-review gate — has landed (see ``tasks_move_task.py::_mt_pre_review_gate_skip_reason``).

Ask (b) — FR-006 in ``docs/plans/loop-friction-fastfollow-spec.md``, status
*Open* — has NOT: the sync daemon is still deaf to ``SPEC_KITTY_SYNC_DISABLE``.
``move-task`` even advertises the env var as a process-wide disable
(``tasks.py`` help: "also honored via the SPEC_KITTY_SYNC_DISABLE / ..."),
and ``tasks_move_task.py`` documents it as "also consumed by the sync daemon" —
but ``_daemon_start_skip_reason`` only checks rollout / intent / policy and
never the disable env. The daemon therefore still spawns synchronously despite
the operator explicitly disabling sync, which is the second half of the
witnessed multi-minute "hang".
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.sync.config import BackgroundDaemonPolicy, SyncConfig
from specify_cli.sync.daemon import DaemonIntent, ensure_sync_daemon_running

# Module-level marker (pytest-marker-convention gate): pre-existing file that
# declared its markers only as per-function decorators. Hoisted to module scope
# (behaviour-identical — single test in the file). NOT part of the
# doctrine-activation-freshness mission; folded in the landing pass to green CI.
pytestmark = [pytest.mark.unit, pytest.mark.regression]


def _config(policy: BackgroundDaemonPolicy) -> SyncConfig:
    """Build a SyncConfig stub with a fixed background-daemon policy (no disk I/O)."""
    cfg = MagicMock(spec=SyncConfig)
    cfg.get_background_daemon.return_value = policy
    return cfg


def test_sync_disable_env_skips_daemon_spawn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """NOTE:
    RED-FIRST P0 reproduction of #2573 per ADR 2026-07-17-1
    (docs/adr/3.x/2026-07-17-1-red-main-is-honest-ci-is-release-authority.md).
    Intentionally FAILS until the product bug is fixed — a red mainline is the honest
    signal of this release-blocking P0. Do NOT xfail/skip/quarantine to green; fix the
    product. Tracking issue: #2573.

    Contract: with the SaaS-sync rollout ON, AUTO policy, and a REMOTE_REQUIRED
    intent, an operator who sets ``SPEC_KITTY_SYNC_DISABLE=1`` must NOT have the
    background sync daemon spawned — the disable env is documented as honored by
    the sync layer (move-task help + ``tasks_move_task.py`` comments) and by
    ``docs/plans/loop-friction-fastfollow-spec.md`` FR-006. On current
    ``upstream/main`` the daemon spawn is attempted anyway (``_daemon_start_skip_reason``
    ignores the env), so ``_ensure_sync_daemon_running_locked`` is invoked and the
    outcome reports ``started=True`` — the failure this test witnesses.
    """
    # Rollout ON (also autouse-set in tests/conftest.py) and REMOTE_REQUIRED +
    # AUTO would normally proceed to spawn — the operator disable must veto that.
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setenv("SPEC_KITTY_SYNC_DISABLE", "1")

    # If the (buggy) code proceeds past the skip decision, this mock stands in for
    # the real daemon spawn so the test never launches a subprocess — its call is
    # itself the witnessed defect.
    inner = MagicMock(return_value=("http://127.0.0.1:9400", 9400, True))

    with (
        patch("specify_cli.sync.daemon._ensure_sync_daemon_running_locked", inner),
        patch("specify_cli.sync.daemon.DAEMON_LOCK_FILE", tmp_path / "sync-daemon.lock"),
        patch("specify_cli.sync.daemon.SPEC_KITTY_DIR", tmp_path),
    ):
        outcome = ensure_sync_daemon_running(
            intent=DaemonIntent.REMOTE_REQUIRED,
            config=_config(BackgroundDaemonPolicy.AUTO),
        )

    assert outcome.started is False, (
        "SPEC_KITTY_SYNC_DISABLE=1 must skip the background sync-daemon spawn "
        f"(#2573 FR-006), but the daemon was started: {outcome!r}"
    )
    inner.assert_not_called()
    assert outcome.skipped_reason is not None

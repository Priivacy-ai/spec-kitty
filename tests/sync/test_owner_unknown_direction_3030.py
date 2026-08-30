"""#3030 fold-in: which direction is fail-closed for the owner-record probes?

``owner.is_orphan`` answers **True** when it cannot stat the recorded
executable path (``except OSError`` at the ``executable_path`` check).  The
FR-025 pattern census flagged that as "unknown ⇒ permit a cleanup action" — the
same shape as the mission's egress defects.  It is not, and this module is the
evidence for leaving the behaviour alone rather than flipping a default because
its shape matched a pattern.

What ``True`` actually buys, measured below:

1. ``BoundaryFailureSet.ok`` goes **False** and ``daemon_status`` becomes
   ``"orphan"`` — every sync mutating command that runs the preflight
   **refuses**.  ``True`` is therefore the *refusing* answer, structurally
   identical to ``core/process_liveness.is_process_alive`` returning ``True``
   ("cannot prove it is dead") to keep a lock from being seized.
2. ``is_orphan`` is a pure predicate: it signals nothing and removes nothing
   (C-002).  The record's own docstring forbids callers from killing the
   recorded PID, and the canonical reaper states that ``owner.json`` is never
   consulted for a kill decision.  The only "cleanup" a ``True`` verdict buys
   is an operator-visible ``rm <owner.json>`` *hint* printed by ``sync doctor``
   — a human-typed action against a JSON file, not an automatic one.

Flipping this to ``False`` on the unknown branch would be the actual fail-open:
it would report a daemon whose executable cannot be verified as ``present``,
suppress the orphan row, and let the preflight pass.

There is a third reason the ``except OSError`` must stay, and it is interpreter
dependent — measured, not assumed:

* Python 3.11.15 and 3.12.13 (**the CI interpreter**): ``Path.exists()`` still
  routes through ``stat()`` and PROPAGATES ``EACCES``. The guard is the only
  thing converting that into a verdict; without it a documented *pure predicate*
  raises ``PermissionError`` through ``sync status``, ``sync doctor`` and the
  preflight.
* Python 3.14.4: ``Path.exists()`` delegates to ``os.path.exists``, which
  swallows every ``OSError`` and returns ``False`` — so ``not exists()`` yields
  the same ``True`` and the ``except`` is inert.

Both routes reach the same verdict, which is why the tests below assert the
verdict rather than the route.

The pins here are what stops a later "shape-matching" pass from making that
change quietly.  See ``kitty-specs/journal-project-consent-3030-01KYKWQS/
tracer-design-decisions.md``, "Two non-egress fail-open permission decisions".
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


@pytest.fixture(autouse=True)
def _scoped_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pin HOME so ``<sync_root>/daemon/owner.json`` lands in a scratch dir."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    return tmp_path


def _build_record(**overrides: Any) -> Any:
    from specify_cli.sync.owner import DaemonOwnerRecord

    defaults: dict[str, Any] = {
        "pid": os.getpid(),
        "port": 9400,
        "token": "deadbeefcafebabe",
        "package_version": "3.2.0",
        "executable_path": sys.executable,
        "source_checkout_path": str(Path(__file__).resolve().parents[2]),
        "server_url": "https://spec-kitty-dev.fly.dev",
        "auth_principal": "tester@example.com",
        "auth_team": "t-private",
        "auth_scope": "https://spec-kitty-dev.fly.dev|tester@example.com|t-private",
        "queue_db_path": str(Path.home() / ".spec-kitty" / "queues" / "queue-aaaaaaaa.db"),
        "started_at": "2026-05-17T16:42:00+00:00",
    }
    defaults.update(overrides)
    return DaemonOwnerRecord(**defaults)


@pytest.fixture
def unstattable_executable(tmp_path: Path) -> Iterator[Path]:
    """A real path inside a mode-000 directory: stat'ing it denies with ``EACCES``.

    Skipped rather than faked where the OS cannot produce the condition (root
    ignores the mode bits; Windows has no equivalent), because a monkeypatched
    ``exists`` would prove only that the mock was installed.
    """
    if os.name != "posix":
        pytest.skip("POSIX directory permissions required to produce EACCES")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("running as root: directory mode bits do not deny traversal")

    locked = tmp_path / "locked"
    locked.mkdir()
    target = locked / "python"
    shutil.copy(sys.executable, target)
    locked.chmod(0o000)
    try:
        yield target
    finally:
        locked.chmod(stat.S_IRWXU)


def test_the_locked_executable_is_genuinely_unverifiable(unstattable_executable: Path) -> None:
    """The condition under test is real at the syscall layer, on every version.

    ``os.stat`` denies with ``EACCES`` regardless of what this interpreter's
    ``Path.exists()`` chooses to do with that error, so the fixture cannot
    silently degrade into "the file is simply missing" — which would make the
    verdict test below pass for the wrong reason.
    """
    with pytest.raises(PermissionError):
        os.stat(unstattable_executable)


def test_is_orphan_never_propagates_the_stat_failure(unstattable_executable: Path) -> None:
    """``is_orphan`` is a pure predicate: it returns a verdict, it never raises.

    On 3.11/3.12 ``Path.exists()`` propagates ``EACCES`` and the ``except
    OSError`` guard is what keeps ``sync status`` / ``sync doctor`` / the
    preflight from crashing on an unreadable path. On 3.13+ the same call
    swallows the error. This test is green on both and red if the guard is
    deleted on either.
    """
    from specify_cli.sync.owner import is_orphan

    record = _build_record(pid=os.getpid(), executable_path=str(unstattable_executable))
    try:
        verdict = is_orphan(record)
    except OSError as exc:  # pragma: no cover - the regression this pins
        pytest.fail(f"is_orphan must not propagate {type(exc).__name__} out of a pure predicate: {exc}")
    assert verdict is True


# ---------------------------------------------------------------------------
# The verdict: one probe, four inputs, two answers
# ---------------------------------------------------------------------------


def test_is_orphan_treats_an_unverifiable_executable_as_orphaned(
    unstattable_executable: Path,
) -> None:
    """PID alive but the executable cannot be stat'ed → orphan (the refusing answer).

    This is the ``unknown`` input.  The healthy control below shares the probe,
    so a predicate that answered ``True`` unconditionally would fail there.
    """
    from specify_cli.sync.owner import is_orphan

    record = _build_record(pid=os.getpid(), executable_path=str(unstattable_executable))
    assert is_orphan(record) is True, "an executable path that cannot be stat'ed must not be reported as a healthy daemon"


def test_is_orphan_control_healthy_record_is_not_orphaned() -> None:
    """Positive control for the probe above: a verifiable live daemon is healthy."""
    from specify_cli.sync.owner import is_orphan

    assert is_orphan(_build_record(pid=os.getpid(), executable_path=sys.executable)) is False


# ---------------------------------------------------------------------------
# The consequence: an orphan verdict REFUSES, it does not permit
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("verifiable", "expected_ok", "expected_status"),
    [
        pytest.param(False, False, "orphan", id="unverifiable-daemon-refuses"),
        pytest.param(True, True, "present", id="verifiable-daemon-proceeds"),
    ],
)
def test_an_unverifiable_executable_refuses_the_whole_preflight(
    unstattable_executable: Path,
    monkeypatch: pytest.MonkeyPatch,
    verifiable: bool,
    expected_ok: bool,
    expected_status: str,
) -> None:
    """End to end: an unstattable executable path ⇒ ``BoundaryFailureSet.ok`` False.

    The gate chain runs for real — ``read_owner_record`` → ``is_orphan`` →
    ``list_orphan_records`` → ``ok``.  Only the two inputs that are neither
    decisions nor under test are stubbed: the foreground identity (otherwise it
    reads the operator's live auth) and the legacy-row count (otherwise it opens
    the queue DB).  Nothing stubs the verdict itself.

    Two rows, two outcomes, one code path: a failure set that were always-ok or
    always-blocked fails one of them.  ``ok`` False is what every sync mutating
    command consults before acting, so ``True`` from ``is_orphan`` is the
    refusing answer, not a permission.
    """
    from specify_cli.sync import preflight as preflight_mod
    from specify_cli.sync.owner import write_owner_record

    executable = sys.executable if verifiable else str(unstattable_executable)
    record = _build_record(pid=os.getpid(), executable_path=executable)
    write_owner_record(record)

    foreground = preflight_mod.ForegroundIdentity(
        package_version=record.package_version,
        executable_path=Path(record.executable_path),
        source_path=Path(record.source_checkout_path),
        server_url=record.server_url,
        team_or_user=f"{record.auth_principal}/{record.auth_team}",
        queue_db_path=Path(record.queue_db_path),
        pid=os.getpid(),
    )
    monkeypatch.setattr(preflight_mod, "collect_foreground_identity", lambda repo_root: foreground)  # noqa: ARG005
    monkeypatch.setattr(preflight_mod, "_count_legacy_rows_for_scope", lambda fg: (0, 0))  # noqa: ARG005
    monkeypatch.setattr(preflight_mod, "_project_store_layout_diagnostic", lambda repo_root: None)  # noqa: ARG005

    failure_set = preflight_mod.build_boundary_failure_set(repo_root=Path.cwd())

    assert failure_set.daemon_status == expected_status
    assert failure_set.mismatches == (), f"unexpected identity mismatches: {failure_set.mismatches}"
    assert failure_set.ok is expected_ok, "an owner record whose executable cannot be verified must not let the sync preflight pass"


def test_orphan_verdict_neither_signals_nor_removes(unstattable_executable: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The bound on the permissive-looking answer: no signal, no deletion.

    ``is_orphan`` may not send a signal (C-002 — the recorded PID may have been
    recycled) and may not delete the owner record; the retirement is an
    operator-typed ``rm`` after ``sync doctor`` surfaces the row.  Those two
    facts are what make the ``True`` verdict cheap enough to be the safe
    default, so they are pinned alongside it.
    """
    from specify_cli.sync import owner as owner_mod

    def _never(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("orphan detection must not signal the recorded PID (C-002)")

    monkeypatch.setattr(os, "kill", _never)
    monkeypatch.setattr(owner_mod.os, "kill", _never, raising=False)

    record = _build_record(pid=os.getpid(), executable_path=str(unstattable_executable))
    owner_mod.write_owner_record(record)
    record_path = owner_mod.owner_record_path()

    assert owner_mod.is_orphan(record) is True
    assert record_path.exists(), "is_orphan must not remove the owner record; retirement is operator-driven"

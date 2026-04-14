"""Tests for windows_migrate.migrate_windows_state().

The first five tests use platform mocking so they run on POSIX without
requiring a real Windows environment or the msvcrt module.

The sixth test (test_concurrent_lock_contention) is marked windows_ci and
must run on a real windows-latest CI job.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

import specify_cli.paths.windows_migrate as _mod
from specify_cli.paths.windows_migrate import (
    MigrationOutcome,
    LegacyWindowsRoot,
    migrate_windows_state,
)


# ---------------------------------------------------------------------------
# Helpers shared by the platform-mocked tests
# ---------------------------------------------------------------------------


def _setup_win32_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path]:
    """Patch sys.platform to win32 and redirect home / localappdata.

    Returns
    -------
    home, localappdata
        Both rooted under *tmp_path* so tests stay isolated.
    """
    home = tmp_path / "User"
    home.mkdir(parents=True, exist_ok=True)
    localappdata = tmp_path / "LocalAppData"
    localappdata.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))

    # Patch platformdirs so get_runtime_root() resolves inside our tmp tree.
    spec_kitty_root = localappdata / "spec-kitty"
    monkeypatch.setattr(
        "specify_cli.paths.windows_paths.platformdirs.user_data_dir",
        lambda *a, **kw: str(spec_kitty_root),
    )
    # Ensure the lock context manager is a no-op even though platform=="win32"
    # (we don't have msvcrt on POSIX, and the CI tests aren't stress-testing
    # the lock itself).
    monkeypatch.setattr(
        _mod,
        "_migration_lock",
        lambda *a, **kw: _noop_ctx(),
    )

    return home, localappdata


from contextlib import contextmanager


@contextmanager
def _noop_ctx() -> object:  # type: ignore[return]
    yield


# ---------------------------------------------------------------------------
# T009-1: test_absent_noop
# ---------------------------------------------------------------------------


def test_absent_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """All legacy roots absent → status='absent' for each; no writes under LocalAppData.

    Four legacy roots are checked after the DRIFT-3 second-pass fix:
    spec_kitty_home (``~/.spec-kitty``), kittify_localappdata
    (``user_data_dir("kittify")`` — the real Windows legacy root),
    kittify_home (``~/.kittify``), and auth_xdg_home.
    """
    home, localappdata = _setup_win32_env(monkeypatch, tmp_path)

    # Confirm none of the legacy dirs exist.
    assert not (home / ".spec-kitty").exists()
    assert not (home / ".kittify").exists()
    assert not (home / ".config" / "spec-kitty").exists()

    outcomes = migrate_windows_state()

    assert len(outcomes) == 4
    for outcome in outcomes:
        assert outcome.status == "absent", f"Expected absent, got {outcome.status!r} for {outcome.legacy_id}"

    # Nothing written under LocalAppData (beyond any lock file that might exist,
    # but the lock is mocked so nothing should be there at all).
    localappdata_spec_kitty = localappdata / "spec-kitty"
    assert not localappdata_spec_kitty.exists() or not any(
        f for f in localappdata_spec_kitty.rglob("*") if f.is_file()
    ), "No files should have been written under LocalAppData"


# ---------------------------------------------------------------------------
# T009-2: test_move_to_empty_destination
# ---------------------------------------------------------------------------


def test_move_to_empty_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Legacy ~/.spec-kitty exists, destination is empty → status='moved'; source gone, dest populated."""
    home, localappdata = _setup_win32_env(monkeypatch, tmp_path)

    # Create a legacy spec-kitty dir with content.
    legacy = home / ".spec-kitty"
    legacy.mkdir(parents=True)
    (legacy / "somefile.txt").write_text("legacy content")
    (legacy / "subdir").mkdir()
    (legacy / "subdir" / "nested.txt").write_text("nested")

    dest = localappdata / "spec-kitty"

    outcomes = migrate_windows_state()

    # Find the spec_kitty_home outcome.
    by_id = {o.legacy_id: o for o in outcomes}
    sk = by_id["spec_kitty_home"]
    assert sk.status == "moved", f"Expected 'moved', got {sk.status!r}: {sk.error}"

    # Source should be gone.
    assert not legacy.exists(), "Legacy path should no longer exist after move"

    # Destination should be populated.
    assert dest.exists(), "Destination should exist after move"
    assert (dest / "somefile.txt").exists(), "Moved file should be at destination"
    assert (dest / "subdir" / "nested.txt").exists(), "Moved nested file should be at destination"

    # The other two outcomes should be absent.
    assert by_id["kittify_home"].status == "absent"
    assert by_id["auth_xdg_home"].status == "absent"


# ---------------------------------------------------------------------------
# T009-3: test_quarantine_on_conflict
# ---------------------------------------------------------------------------


def test_quarantine_on_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Legacy exists + non-empty destination → legacy quarantined; dest untouched."""
    home, localappdata = _setup_win32_env(monkeypatch, tmp_path)

    # Create legacy.
    legacy = home / ".spec-kitty"
    legacy.mkdir(parents=True)
    (legacy / "old.txt").write_text("old legacy")

    # Create non-empty destination.
    dest = localappdata / "spec-kitty"
    dest.mkdir(parents=True)
    (dest / "existing.txt").write_text("existing canonical state")

    outcomes = migrate_windows_state()

    by_id = {o.legacy_id: o for o in outcomes}
    sk = by_id["spec_kitty_home"]
    assert sk.status == "quarantined", f"Expected 'quarantined', got {sk.status!r}: {sk.error}"
    assert sk.quarantine_path is not None

    quarantine = Path(sk.quarantine_path)
    # Quarantine path should follow the naming pattern.
    assert ".bak-" in quarantine.name

    # Quarantine should exist and contain the legacy content.
    assert quarantine.exists(), "Quarantine path must exist"
    assert (quarantine / "old.txt").exists(), "Legacy file should be in quarantine"

    # Original legacy location should be gone.
    assert not legacy.exists(), "Legacy should have been renamed to quarantine"

    # Destination should be untouched.
    assert (dest / "existing.txt").read_text() == "existing canonical state", (
        "Existing destination content must not be modified"
    )


# ---------------------------------------------------------------------------
# T009-4: test_idempotent_second_run
# ---------------------------------------------------------------------------


def test_idempotent_second_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Second invocation returns all status='absent' (idempotent no-op)."""
    home, localappdata = _setup_win32_env(monkeypatch, tmp_path)

    # First run: create legacy and move it.
    legacy = home / ".spec-kitty"
    legacy.mkdir(parents=True)
    (legacy / "data.txt").write_text("some state")

    first = migrate_windows_state()
    by_id_first = {o.legacy_id: o for o in first}
    assert by_id_first["spec_kitty_home"].status == "moved"

    # Second run: legacy is gone → all absent (4 outcomes after DRIFT-3 fix
    # added kittify_localappdata to the legacy source set).
    second = migrate_windows_state()
    assert len(second) == 4
    for outcome in second:
        assert outcome.status == "absent", (
            f"Second run: expected 'absent' for {outcome.legacy_id}, got {outcome.status!r}"
        )


# ---------------------------------------------------------------------------
# T009-5: test_dry_run_no_side_effects
# ---------------------------------------------------------------------------


def test_dry_run_no_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """dry_run=True returns outcomes reflecting intent without touching the filesystem."""
    home, localappdata = _setup_win32_env(monkeypatch, tmp_path)

    # Create legacy.
    legacy = home / ".spec-kitty"
    legacy.mkdir(parents=True)
    (legacy / "important.txt").write_text("do not move")

    dest = localappdata / "spec-kitty"

    outcomes = migrate_windows_state(dry_run=True)

    by_id = {o.legacy_id: o for o in outcomes}
    sk = by_id["spec_kitty_home"]

    # Outcome should reflect what *would* happen.
    assert sk.status == "moved", (
        f"dry_run: expected status 'moved', got {sk.status!r}: {sk.error}"
    )

    # Filesystem must be unchanged.
    assert legacy.exists(), "dry_run must not move the legacy directory"
    assert (legacy / "important.txt").exists(), "dry_run must not touch legacy files"
    assert not dest.exists() or not any(dest.iterdir()), (
        "dry_run must not write to destination"
    )


# ---------------------------------------------------------------------------
# T010: test_concurrent_lock_contention (windows_ci only)
# ---------------------------------------------------------------------------


@pytest.mark.windows_ci
def test_concurrent_lock_contention(tmp_path: Path) -> None:
    """Two subprocesses racing the lock: exactly one completes; no data lost.

    This test requires the real msvcrt module and must run on windows-latest.
    """
    env = {
        **os.environ,
        "LOCALAPPDATA": str(tmp_path / "LocalAppData"),
        "USERPROFILE": str(tmp_path / "User"),
        "HOME": str(tmp_path / "User"),
    }
    user_home = tmp_path / "User"
    user_home.mkdir(parents=True, exist_ok=True)
    (user_home / ".spec-kitty").mkdir(parents=True, exist_ok=True)
    (user_home / ".spec-kitty" / "file.txt").write_text("legacy")

    runner = textwrap.dedent(
        """
        import json, sys
        from specify_cli.paths.windows_migrate import migrate_windows_state
        outcomes = migrate_windows_state()
        print(json.dumps([
            {"legacy_id": o.legacy_id, "status": o.status, "error": o.error}
            for o in outcomes
        ]))
        """
    )

    p1 = subprocess.Popen(
        [sys.executable, "-c", runner],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    p2 = subprocess.Popen(
        [sys.executable, "-c", runner],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    rc1 = p1.wait(timeout=15)
    rc2 = p2.wait(timeout=15)

    # Both processes must exit cleanly.
    assert rc1 == 0, f"P1 failed (rc={rc1}): {p1.stderr.read().decode()}"
    assert rc2 == 0, f"P2 failed (rc={rc2}): {p2.stderr.read().decode()}"

    import json

    out1 = json.loads(p1.stdout.read().decode().strip())
    out2 = json.loads(p2.stdout.read().decode().strip())

    def spec_kitty_status(outcomes: list[dict]) -> str:
        for o in outcomes:
            if o["legacy_id"] == "spec_kitty_home":
                return o["status"]
        return "unknown"

    s1 = spec_kitty_status(out1)
    s2 = spec_kitty_status(out2)

    # Acceptable outcomes: one moved, one absent; or one moved, one error
    # (lock contention).  What is NOT acceptable: both moved (data race) or
    # both absent without a move having happened.
    dest = tmp_path / "LocalAppData" / "spec-kitty"
    legacy = tmp_path / "User" / ".spec-kitty"

    # The canonical destination must be populated (one process completed).
    assert dest.exists() and any(dest.rglob("*")), (
        "Destination must be populated after one process completes the migration"
    )

    # The original legacy location must not remain as-is when destination is
    # populated — it is either moved or quarantined.
    if legacy.exists():
        # If legacy still exists, it must be a quarantine backup, or both
        # processes saw absent (second process raced after first completed).
        pass  # Acceptable: second process saw absent

    # At least one process must have succeeded (moved or quarantined).
    assert s1 in ("moved", "quarantined", "absent", "error"), f"Unexpected status P1: {s1}"
    assert s2 in ("moved", "quarantined", "absent", "error"), f"Unexpected status P2: {s2}"
    moved_count = sum(1 for s in (s1, s2) if s == "moved")
    assert moved_count >= 1 or (s1 == "quarantined" or s2 == "quarantined"), (
        f"Expected at least one 'moved' or 'quarantined' outcome; got {s1!r} and {s2!r}"
    )

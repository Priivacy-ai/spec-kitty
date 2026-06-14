"""Regression tests for WP04 per-worker HOME/state isolation (FR-002, SC-006).

These tests lock the master-enabler guarantee: every xdist worker (and the
serial ``master`` run) resolves its OWN ``Path.home()`` so parallel workers
never share or truncate the real ``~/.spec-kitty/queue.db``.

Two properties are proven:

1. **Distinct homes** — two simulated worker ids resolve *different* home base
   directories (and the serial ``master`` id resolves a third). This is the
   anti-collision invariant; a session-only fixture would violate it.
2. **Real home untouched** — the real ``~/.spec-kitty`` is neither created nor
   modified by a worker run. We record its absence / mtime before, run an
   isolated worker, and assert it is unchanged after.

These directly support WP02's ``test_real_home_isolation_guard`` (that guard
flips from skip to active once this isolation fixture exists).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

import pytest

from tests.conftest import (
    _REAL_HOME_ENV_VAR,
    _apply_home_env,
    _worker_home_base,
    _worker_id,
)

pytestmark = [pytest.mark.fast]


def _real_home() -> Path:
    """Return the operator's *real* home, bypassing the patched ``Path.home``.

    ``Path.home()`` and ``os.path.expanduser('~')`` are both redirected by the
    autouse isolation fixture. ``pytest_configure`` captures the original home
    before redirecting env vars, so tests can assert the real ``~/.spec-kitty``
    stays untouched.
    """
    return Path(os.environ[_REAL_HOME_ENV_VAR])


class _FakeWorkerInput(dict[str, str]):
    """Minimal stand-in for ``config.workerinput`` (an xdist-provided dict)."""


class _FakeConfig:
    """Stand-in for ``pytest.Config`` exposing only what the helpers read.

    The WP04 helpers touch exactly two pieces of ``pytest.Config``: the optional
    ``workerinput`` mapping and an arbitrary cached attribute they ``setattr``.
    This double implements that surface faithfully, so we ``cast`` it to
    ``pytest.Config`` at call sites rather than weakening the helper signatures.
    """

    def __init__(self, workerid: str | None, testrunuid: str = "run-fixed") -> None:
        if workerid is not None:
            self.workerinput = _FakeWorkerInput(
                workerid=workerid, testrunuid=testrunuid
            )


def _as_config(fake: _FakeConfig) -> pytest.Config:
    """Present the faithful test double to the helpers' real type."""
    return cast(pytest.Config, fake)


def test_worker_id_resolves_master_when_serial() -> None:
    """No ``workerinput`` (serial / controller) → ``master``."""
    assert _worker_id(_as_config(_FakeConfig(workerid=None))) == "master"


def test_worker_id_reads_xdist_workerid() -> None:
    assert _worker_id(_as_config(_FakeConfig(workerid="gw3"))) == "gw3"


def test_two_worker_ids_resolve_distinct_homes() -> None:
    """SC-006 anti-collision: distinct worker ids → distinct home base dirs.

    A session-only fixture would resolve a single shared home for all workers
    and break this assertion; that is the rejected design.
    """
    home_gw0 = _worker_home_base(_as_config(_FakeConfig(workerid="gw0")))
    home_gw1 = _worker_home_base(_as_config(_FakeConfig(workerid="gw1")))
    home_master = _worker_home_base(_as_config(_FakeConfig(workerid=None)))

    assert home_gw0 != home_gw1
    assert home_gw0 != home_master
    assert home_gw1 != home_master
    # Each base actually exists on disk and is worker-id-namespaced.
    for home, wid in ((home_gw0, "gw0"), (home_gw1, "gw1"), (home_master, "master")):
        assert home.is_dir()
        assert home.name == wid
    assert home_master.parent.name.startswith("serial-")
    assert home_master.parent.name != "serial"


def test_same_worker_id_is_stable_within_process() -> None:
    """The base is cached on ``config`` so import-time and fixture reads agree."""
    config = _as_config(_FakeConfig(workerid="gw7"))
    first = _worker_home_base(config)
    second = _worker_home_base(config)
    assert first == second


def test_apply_home_env_points_env_at_isolated_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_apply_home_env`` redirects HOME + XDG/AppData env vars (C-005)."""
    base = tmp_path / "isolated-home"
    _apply_home_env(base)

    assert os.environ["HOME"] == str(base)
    assert os.environ["USERPROFILE"] == str(base)
    assert os.environ["XDG_CONFIG_HOME"] == str(base / ".config")
    assert os.environ["XDG_DATA_HOME"] == str(base / ".local/share")
    assert os.environ["XDG_STATE_HOME"] == str(base / ".local/state")
    assert os.environ["LOCALAPPDATA"] == str(base / "AppData/Local")


def test_autouse_fixture_redirects_path_home() -> None:
    """The active (autouse) isolation must already be in effect for this test."""
    assert Path.home() != _real_home()
    assert "spec-kitty-test-homes" in str(Path.home())
    # The XDG vars set by the fixture live under the same isolated home.
    assert str(Path.home()) in os.environ["XDG_CONFIG_HOME"]


def test_real_spec_kitty_dir_untouched_by_worker_run(tmp_path: Path) -> None:
    """A simulated worker run must not create/modify the real ``~/.spec-kitty``.

    Record the real ``~/.spec-kitty`` state (absent, or its mtime) *before*
    exercising an isolated worker home, then assert it is unchanged after.
    """
    real_spec_kitty = _real_home() / ".spec-kitty"
    existed_before = real_spec_kitty.exists()
    mtime_before = real_spec_kitty.stat().st_mtime if existed_before else None

    # Simulate a worker writing the queue state into its isolated home.
    worker_home = _worker_home_base(_as_config(_FakeConfig(workerid="gw-iso-check")))
    isolated_spec_kitty = worker_home / ".spec-kitty"
    isolated_spec_kitty.mkdir(parents=True, exist_ok=True)
    (isolated_spec_kitty / "queue.db").write_text("worker rows", encoding="utf-8")

    # The write landed in the isolated home, not the real one.
    assert isolated_spec_kitty != real_spec_kitty
    assert (isolated_spec_kitty / "queue.db").exists()

    existed_after = real_spec_kitty.exists()
    assert existed_after == existed_before, (
        "isolation leaked: real ~/.spec-kitty existence changed "
        f"({existed_before} -> {existed_after})"
    )
    if existed_before:
        assert real_spec_kitty.stat().st_mtime == mtime_before, (
            "isolation leaked: real ~/.spec-kitty was modified"
        )

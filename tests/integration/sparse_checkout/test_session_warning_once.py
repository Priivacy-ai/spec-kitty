"""Integration test — ``warn_if_sparse_once`` is truly once-per-process (NFR-005).

Exercises ``warn_if_sparse_once`` against a real git repo with
``core.sparseCheckout=true`` to confirm that across N consecutive CLI-style
call sites the warning fires exactly once per process. This is the backstop
for the FR-010 / NFR-005 exactly-once emission contract that WP06/WP07
warning call sites rely on.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import pytest

from specify_cli.git import sparse_checkout as sc_mod
from specify_cli.git.sparse_checkout import (
    _reset_session_warning_state,
    warn_if_sparse_once,
)


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    _reset_session_warning_state()


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _make_sparse_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", str(path)])
    _run(["git", "-C", str(path), "config", "user.email", "t@example.com"])
    _run(["git", "-C", str(path), "config", "user.name", "T"])
    _run(["git", "-C", str(path), "config", "core.sparseCheckout", "true"])


def test_warn_fires_exactly_once_across_many_calls(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    repo = tmp_path / "repo"
    _make_sparse_repo(repo)

    caplog.set_level(logging.WARNING, logger=sc_mod.logger.name)

    # Simulate being invoked at many CLI surfaces within the same process.
    for cmd in [
        "merge",
        "implement",
        "review",
        "accept",
        "tasks:move-task",
        "doctor",
        "dashboard",
    ]:
        warn_if_sparse_once(repo, command=cmd)

    hits = [
        r
        for r in caplog.records
        if "spec_kitty.sparse_checkout.detected" in r.getMessage()
    ]
    assert len(hits) == 1, (
        f"Expected exactly one session warning across N call sites, got "
        f"{len(hits)}: {[r.getMessage() for r in hits]}"
    )
    assert "command=merge" in hits[0].getMessage(), (
        "The first caller wins — subsequent CLI surfaces must not overwrite the command label."
    )


def test_warn_records_first_command_label_not_last(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    repo = tmp_path / "repo"
    _make_sparse_repo(repo)

    caplog.set_level(logging.WARNING, logger=sc_mod.logger.name)

    warn_if_sparse_once(repo, command="implement")
    warn_if_sparse_once(repo, command="merge")
    warn_if_sparse_once(repo, command="doctor")

    hits = [
        r
        for r in caplog.records
        if "spec_kitty.sparse_checkout.detected" in r.getMessage()
    ]
    assert len(hits) == 1
    assert "command=implement" in hits[0].getMessage()


def test_warn_does_not_fire_on_clean_repo_even_after_many_calls(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "-q", str(repo)])
    _run(["git", "-C", str(repo), "config", "user.email", "t@example.com"])
    _run(["git", "-C", str(repo), "config", "user.name", "T"])

    caplog.set_level(logging.WARNING, logger=sc_mod.logger.name)

    for _ in range(10):
        warn_if_sparse_once(repo, command="merge")

    assert not any(
        "spec_kitty.sparse_checkout.detected" in r.getMessage()
        for r in caplog.records
    )


def test_module_level_flag_is_real_cache_not_decorator_sugar() -> None:
    """Sanity check: the once-per-process mechanism must be a module global."""
    assert hasattr(sc_mod, "_SPARSE_WARNING_EMITTED"), (
        "warn_if_sparse_once must be backed by a module-level flag per R5."
    )
    # Starts False after the fixture reset above.
    assert sc_mod._SPARSE_WARNING_EMITTED is False

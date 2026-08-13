"""Contract tests for the pre-readable-identity mission-create target seam."""

from __future__ import annotations

from pathlib import Path

import pytest

from mission_runtime import (
    ActionContextError,
    CommitTarget,
    resolve_create_time_write_target,
)

pytestmark = pytest.mark.unit


def test_create_time_target_preserves_explicit_short_branch() -> None:
    """The bootstrap seam returns the exact explicit planning branch."""
    assert resolve_create_time_write_target("owned-mission") == CommitTarget(
        ref="owned-mission"
    )


@pytest.mark.parametrize("branch", ["", "   ", "refs/heads/owned-mission"])
def test_create_time_target_refuses_non_short_branch_shapes(branch: str) -> None:
    """Empty and fully-qualified inputs fail before commit routing."""
    with pytest.raises(ActionContextError) as exc_info:
        resolve_create_time_write_target(branch)

    assert exc_info.value.code == "CREATE_TIME_TARGET_INVALID"


def test_create_time_target_ignores_ambient_checkout_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CWD and root environment cannot redirect an explicit create target."""
    first_cwd = tmp_path / "first"
    second_cwd = tmp_path / "second"
    first_cwd.mkdir()
    second_cwd.mkdir()

    monkeypatch.chdir(first_cwd)
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(tmp_path / "foreign-primary"))
    first = resolve_create_time_write_target("owned-mission")

    monkeypatch.chdir(second_cwd)
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(tmp_path / "different-primary"))
    second = resolve_create_time_write_target("owned-mission")

    assert first == second == CommitTarget(ref="owned-mission")

"""Parity guard for ``tests/_factories.make_mission()`` (FR-008 / E-06 / IC-07).

``make_mission()`` MUST be a thin delegate over ``create_mission_core()`` --
never a forked re-implementation of the meta-assembly schema. This module
asserts that invariant plus the behaviour-preservation of the
``allow_worktree_context`` seam added to ``create_mission_core()`` to make a
side-effect-free, no-coordination-branch entrypoint usable from test code
(T038 / NFR-003).

A raw byte-compare across two independent calls is unachievable as-is:
``mission_id`` (a ``ULID``) and ``created_at`` (wall-clock) are minted fresh
every call, and the mission directory / ``slug`` / ``mission_slug`` fields
embed the ``mission_id``-derived ``mid8`` suffix. This test freezes both the
ULID mint and the clock so both calls produce the identical mission_id and
timestamp, making a true byte-identical comparison of the written
``meta.json`` possible -- the strongest form of the parity assertion.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import subprocess

import pytest

from mission_runtime import MissionTopology
import specify_cli.core.mission_creation as mission_creation_module
from specify_cli.core.mission_creation import MissionCreationError, create_mission_core
from tests._factories import make_mission

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_FROZEN_MISSION_ID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
_FROZEN_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


class _FrozenULID:
    """Stand-in for ``ulid.ULID()`` whose ``str()`` is a fixed value."""

    def __str__(self) -> str:  # noqa: D105 - trivial stringification
        return _FROZEN_MISSION_ID


def _init_git_repo(repo: Path, *, branch: str = "main") -> None:
    (repo / ".kittify").mkdir(parents=True, exist_ok=True)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"], cwd=repo, check=True)


def _read_meta_bytes(repo_root: Path, mission_slug_prefix: str) -> bytes:
    matches = [
        p for p in (repo_root / "kitty-specs").iterdir() if p.name.startswith(f"{mission_slug_prefix}-")
    ]
    assert len(matches) == 1, f"expected exactly one mission dir, found {matches}"
    return (matches[0] / "meta.json").read_bytes()


@pytest.fixture
def _frozen_mint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Freeze the ULID mint and wall-clock inside ``mission_creation`` so two
    independent ``create_mission_core()`` calls made under this fixture mint
    the identical ``mission_id`` / ``created_at`` -- the only two per-call
    non-deterministic fields in the schema (the ``mid8`` embedded in
    ``slug``/``mission_slug`` derives from ``mission_id``, so freezing it also
    pins those fields).
    """

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz: object | None = None) -> _FrozenDatetime:  # noqa: ARG003
            return cls.fromtimestamp(_FROZEN_NOW.timestamp(), tz=UTC)

    monkeypatch.setattr(mission_creation_module, "ULID", _FrozenULID)
    monkeypatch.setattr(mission_creation_module, "datetime", _FrozenDatetime)


def test_make_mission_meta_is_byte_identical_to_direct_core_call(
    tmp_path: Path, _frozen_mint: None
) -> None:
    """E-06 / IC-07: make_mission() delegates -- it does not fork the schema."""
    direct_repo = tmp_path / "direct"
    factory_repo = tmp_path / "factory"
    direct_repo.mkdir()
    factory_repo.mkdir()
    _init_git_repo(direct_repo)
    _init_git_repo(factory_repo)

    friendly_name = "Parity Mission"
    purpose_tldr = "Deliver parity mission cleanly for the team."
    purpose_context = (
        "This mission delivers parity mission so product and engineering "
        "can move forward with a clear outcome and shared understanding."
    )

    create_mission_core(
        direct_repo,
        "parity-mission",
        friendly_name=friendly_name,
        purpose_tldr=purpose_tldr,
        purpose_context=purpose_context,
        target_branch="main",
        topology=MissionTopology.SINGLE_BRANCH,
        allow_worktree_context=True,
    )
    make_mission(
        factory_repo,
        "parity-mission",
        friendly_name=friendly_name,
        purpose_tldr=purpose_tldr,
        purpose_context=purpose_context,
        target_branch="main",
        topology=MissionTopology.SINGLE_BRANCH,
        allow_worktree_context=True,
    )

    direct_bytes = _read_meta_bytes(direct_repo, "parity-mission")
    factory_bytes = _read_meta_bytes(factory_repo, "parity-mission")

    assert direct_bytes == factory_bytes


def test_make_mission_applies_explicit_overrides_on_production_shaped_meta(
    tmp_path: Path, _frozen_mint: None
) -> None:
    """Overrides land on top of the production schema, not a forked one."""
    repo = tmp_path / "override-repo"
    repo.mkdir()
    _init_git_repo(repo)

    result = make_mission(repo, "override-mission", friendly_name="Custom Override Name")

    assert result.meta["friendly_name"] == "Custom Override Name"
    meta_bytes = _read_meta_bytes(repo, "override-mission")
    assert b'"friendly_name": "Custom Override Name"' in meta_bytes
    # Still production-shaped: the schema fields make_mission() did not
    # override come straight from create_mission_core().
    assert result.meta["mission_id"] == _FROZEN_MISSION_ID
    assert result.meta["topology"] == "single_branch"
    assert "coordination_branch" not in result.meta


def test_create_mission_core_worktree_guard_default_still_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T038 behaviour-preservation proof: the new ``allow_worktree_context``
    seam defaults to ``False``, so the pre-existing interactive/CLI guard
    against scaffolding a mission from inside a worktree is unchanged for
    every existing caller that does not pass the new keyword.
    """
    repo = tmp_path / "guard-default-repo"
    repo.mkdir()
    _init_git_repo(repo)

    # Simulate the *process* cwd resolving inside a worktree, independent of
    # the temp ``repo_root`` under test -- this is exactly what
    # ``is_worktree_context(Path.cwd())`` observes for real test runs
    # executed from a lane worktree checkout.
    monkeypatch.setattr(mission_creation_module, "is_worktree_context", lambda _p: True)

    with pytest.raises(MissionCreationError, match="worktree"):
        create_mission_core(
            repo,
            "guard-default-mission",
            topology=MissionTopology.SINGLE_BRANCH,
            friendly_name="Guard Default",
            purpose_tldr="Deliver guard default cleanly for the team.",
            purpose_context="This mission proves the worktree guard still blocks by default.",
        )


def test_create_mission_core_worktree_guard_bypass_is_behaviour_preserving(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The opt-in bypass unblocks mission creation from a worktree-shaped cwd
    while every other guard and the resulting schema stay unchanged --
    proving the new entrypoint is behaviour-preserving (NFR-003), not a new
    code path with different output shape.
    """
    repo = tmp_path / "guard-bypass-repo"
    repo.mkdir()
    _init_git_repo(repo)

    monkeypatch.setattr(mission_creation_module, "is_worktree_context", lambda _p: True)

    result = create_mission_core(
        repo,
        "guard-bypass-mission",
        topology=MissionTopology.SINGLE_BRANCH,
        allow_worktree_context=True,
        friendly_name="Guard Bypass",
        purpose_tldr="Deliver guard bypass cleanly for the team.",
        purpose_context="This mission proves the worktree guard bypass is behaviour-preserving.",
    )

    assert result.feature_dir.exists()
    assert result.meta["topology"] == "single_branch"

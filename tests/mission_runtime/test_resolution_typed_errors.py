"""WP05 typed-error pass-through: MissionSelectorAmbiguous must translate to
ActionContextError at the mission_runtime boundary.

When ``resolve_action_context`` / ``resolve_placement_only`` is called with an
ambiguous mission handle (one that matches more than one mission in the repo),
the underlying ``specify_cli`` exception ``MissionSelectorAmbiguous`` must be
caught at the ``resolution.py`` boundary and re-raised as the single
consumer-facing type ``ActionContextError`` with the specific stable code
``MISSION_AMBIGUOUS_SELECTOR`` — never escaped as a raw ``specify_cli``
exception (FR-005 / #2010 bug #15).

Red-state receipt (pre-fix, unmodified resolution.py):
    The try-block at resolution.py:183 only catches StatusReadPathNotFound.
    When the handle is ambiguous, MissionSelectorAmbiguous propagates up
    uncaught through resolve_action_context, escaping the mission_runtime
    boundary as a raw specify_cli exception. This test asserts that
    ActionContextError is raised with code MISSION_AMBIGUOUS_SELECTOR —
    which FAILS on unmodified code because MissionSelectorAmbiguous escapes
    instead.

Green-state (post-fix):
    The new ``except MissionSelectorAmbiguous`` arm in ``_resolve_mission_slug``
    translates the raw exception to ActionContextError(MISSION_AMBIGUOUS_SELECTOR),
    making the test pass.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from mission_runtime import (
    ActionContextError,
    MissionArtifactKind,
    resolve_action_context,
    resolve_placement_only,
)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

# Two missions that share the same human slug stripped of their numeric prefix.
# When the operator passes the bare human slug, the resolver matches both and
# raises MissionSelectorAmbiguous (C-CTX-4).
_MID8_A = "AABB1100"
_MID8_B = "CCDD2200"
_MISSION_ID_A = f"{_MID8_A}000000000000000000"  # 26-char ULID-shaped
_MISSION_ID_B = f"{_MID8_B}000000000000000000"  # 26-char ULID-shaped
_HUMAN_SLUG = "ambiguous-name"
_DIRNAME_A = f"001-{_HUMAN_SLUG}"
_DIRNAME_B = f"002-{_HUMAN_SLUG}"
# The bare human slug is the ambiguous handle: it matches both _DIRNAME_A and
# _DIRNAME_B when stripped of their numeric prefix.
_AMBIGUOUS_HANDLE = _HUMAN_SLUG


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.invalid")
    _git(r, "config", "user.name", "Test")
    _git(r, "config", "commit.gpgsign", "false")
    (r / ".kittify").mkdir()
    (r / ".kittify" / "config.yaml").write_text(
        "agents:\n  available:\n    - claude\n", encoding="utf-8"
    )
    return r


def _build_mission(
    repo: Path,
    *,
    dirname: str,
    mission_id: str,
    mid8: str,
) -> Path:
    """Build a minimal mission directory with meta.json and commit it."""
    feature_dir = repo / "kitty-specs" / dirname
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "mission_id": mission_id,
        "mid8": mid8,
        "mission_slug": dirname,
        "mission_type": "software-dev",
        "target_branch": "main",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (feature_dir / "tasks").mkdir(exist_ok=True)
    return feature_dir


@pytest.fixture
def ambiguous_repo(repo: Path) -> Path:
    """Repo with two missions sharing the same human slug (ambiguous handle)."""
    _build_mission(
        repo,
        dirname=_DIRNAME_A,
        mission_id=_MISSION_ID_A,
        mid8=_MID8_A,
    )
    _build_mission(
        repo,
        dirname=_DIRNAME_B,
        mission_id=_MISSION_ID_B,
        mid8=_MID8_B,
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "two-ambiguous-missions")
    return repo


def test_ambiguous_handle_raises_action_context_error_with_specific_code(
    ambiguous_repo: Path,
) -> None:
    """Ambiguous handle → ActionContextError(MISSION_AMBIGUOUS_SELECTOR) at the boundary.

    Before the WP05 fix: MissionSelectorAmbiguous escapes resolve_action_context
    as a raw specify_cli exception (no ActionContextError wrapping, no stable code).
    After the fix: ActionContextError is raised with code MISSION_AMBIGUOUS_SELECTOR.
    """
    with pytest.raises(ActionContextError) as excinfo:
        resolve_action_context(
            ambiguous_repo,
            action="status",
            feature=_AMBIGUOUS_HANDLE,
        )

    assert excinfo.value.code == "MISSION_AMBIGUOUS_SELECTOR", (
        f"Expected code 'MISSION_AMBIGUOUS_SELECTOR', got {excinfo.value.code!r}. "
        "The MissionSelectorAmbiguous exception escaped the mission_runtime boundary "
        "as a raw specify_cli exception instead of being translated."
    )
    assert _AMBIGUOUS_HANDLE in str(excinfo.value), (
        "The error message must include the ambiguous handle so operators can diagnose."
    )


def test_ambiguous_handle_resolve_placement_only_raises_action_context_error(
    ambiguous_repo: Path,
) -> None:
    """resolve_placement_only must also translate MissionSelectorAmbiguous.

    The candidate_feature_dir_for_mission call in resolve_placement_only also
    routes through the read-path resolver, which can raise MissionSelectorAmbiguous.
    The translation must apply there too — not only in resolve_action_context.
    """
    with pytest.raises(ActionContextError) as excinfo:
        resolve_placement_only(
            ambiguous_repo,
            _AMBIGUOUS_HANDLE,
            kind=MissionArtifactKind.STATUS_STATE,
        )

    assert excinfo.value.code == "MISSION_AMBIGUOUS_SELECTOR", (
        f"Expected code 'MISSION_AMBIGUOUS_SELECTOR', got {excinfo.value.code!r}. "
        "MissionSelectorAmbiguous escaped resolve_placement_only untranslated."
    )

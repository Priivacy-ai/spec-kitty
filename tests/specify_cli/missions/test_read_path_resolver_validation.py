"""NFR-002 tests: rejection fires INSIDE the read primitives, not at a caller.

T004 — prove that:
  (a) primary_feature_dir_for_mission raises ValueError for malformed slugs.
  (b) resolve_mission_read_path raises ValueError for malformed slugs.
  (c) The guard fires BEFORE _resolve_existing_for_slug is called — a guard
      placed AFTER composition would satisfy (a)/(b) while a malformed slug
      had already flowed through path composition (the squad-flagged gaming
      path). The spy assertion makes this un-fakeable.
  (d) A valid real-format slug still returns the composed kitty-specs/<slug>
      path unchanged (NFR-006 regression guard).

Fixtures use a real temp git repo + full-ULID-bearing real-format slug
(NFR-003: topology-true, production-shaped data only).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.missions._read_path_resolver import (
    primary_feature_dir_for_mission,
    resolve_mission_read_path,
)

pytestmark = [pytest.mark.fast]

# Production-shaped slugs (NFR-003: no fabricated short ids)
_REAL_SLUG = "canonical-seams-path-trust-guard-capability-01KVBBT6"
_REAL_MID8 = "01KVBBT6"
_REAL_MISSION_ID = "01KVBBT6FEQ01NHNSQD7X8JTPE"

_TRAVERSAL_SLUGS = [
    "../escape",
    "..",
    ".",
    "a/b",
    ".hidden",
    "..foo",
    "foo..",
    "a..b",
    "",
    "   ",
]


@pytest.fixture()
def real_git_repo(tmp_path: Path) -> Path:
    """Create a minimal real git repo with kitty-specs directory."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        check=True,
        capture_output=True,
        cwd=str(tmp_path),
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        check=True,
        capture_output=True,
        cwd=str(tmp_path),
    )
    # Create the .kittify marker so locate_project_root finds this root
    (tmp_path / ".kittify").mkdir()
    (tmp_path / "kitty-specs").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# (a) primary_feature_dir_for_mission raises for malformed slugs
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad_slug", _TRAVERSAL_SLUGS)
def test_primary_raises_for_malformed_slug(
    real_git_repo: Path,
    bad_slug: str,
) -> None:
    """primary_feature_dir_for_mission must raise ValueError for traversal slugs."""
    with pytest.raises(ValueError, match="safe path segment"):
        primary_feature_dir_for_mission(real_git_repo, bad_slug)


# ---------------------------------------------------------------------------
# (b) resolve_mission_read_path raises for malformed slugs
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad_slug", _TRAVERSAL_SLUGS)
def test_resolve_raises_for_malformed_slug(
    real_git_repo: Path,
    bad_slug: str,
) -> None:
    """resolve_mission_read_path must raise ValueError for traversal slugs."""
    with pytest.raises(ValueError, match="safe path segment"):
        resolve_mission_read_path(real_git_repo, bad_slug, "")


# ---------------------------------------------------------------------------
# (c) Guard fires BEFORE _resolve_existing_for_slug (topology-proof)
# ---------------------------------------------------------------------------
def test_guard_fires_before_resolve_existing_for_slug(real_git_repo: Path) -> None:
    """Spy on _resolve_existing_for_slug: it must NEVER be called with a malformed slug.

    A guard placed AFTER composition would still let the slug flow through
    ``_resolve_existing_for_slug`` before raising. This assertion proves
    the guard is truly at the front of ``resolve_mission_read_path``.
    """
    mock_spy = MagicMock(return_value=None)
    with patch(
        "specify_cli.missions._read_path_resolver._resolve_existing_for_slug",
        mock_spy,
    ), pytest.raises(ValueError, match="safe path segment"):
        resolve_mission_read_path(real_git_repo, "../escape", "")

    # The critical assertion: _resolve_existing_for_slug must NOT have been called
    mock_spy.assert_not_called()


def test_guard_fires_before_resolve_existing_for_various_traversal(
    real_git_repo: Path,
) -> None:
    """Spy asserts _resolve_existing_for_slug not called for any traversal slug."""
    bad_slugs = ["../escape", ".hidden", "..foo", "a..b", "a/b"]
    for bad_slug in bad_slugs:
        mock_spy = MagicMock(return_value=None)
        with (
            patch(
                "specify_cli.missions._read_path_resolver._resolve_existing_for_slug",
                mock_spy,
            ),
            pytest.raises(ValueError, match="safe path segment"),
        ):
            resolve_mission_read_path(real_git_repo, bad_slug, "")
        assert not mock_spy.called, (
            f"_resolve_existing_for_slug was called with malformed slug {bad_slug!r} — "
            f"the guard must fire BEFORE composition"
        )


# ---------------------------------------------------------------------------
# (d) Valid real-format slugs return the composed kitty-specs/<slug> path
# ---------------------------------------------------------------------------
def test_valid_slug_returns_composed_path(real_git_repo: Path) -> None:
    """A valid real-format slug returns the expected kitty-specs/<slug> path (NFR-006).

    Uses resolve_mission_read_path (not candidate_*) to test the primitive
    directly; no coord worktree materialized so it falls through to the primary
    candidate path.
    """
    result = resolve_mission_read_path(
        real_git_repo, _REAL_SLUG, _REAL_MID8, require_exists=False
    )
    # The path should be the kitty-specs/ candidate for this slug
    assert "kitty-specs" in str(result), (
        f"Expected kitty-specs in path, got {result}"
    )
    # Must contain the slug (or a slug-mid8 composite)
    assert _REAL_SLUG in str(result) or _REAL_MID8 in str(result), (
        f"Expected slug {_REAL_SLUG!r} or mid8 {_REAL_MID8!r} in path, got {result}"
    )


def test_primary_valid_slug_returns_composed_path(real_git_repo: Path) -> None:
    """primary_feature_dir_for_mission returns kitty-specs/<slug> for valid slug."""
    result = primary_feature_dir_for_mission(real_git_repo, _REAL_SLUG)
    assert result.name == _REAL_SLUG, (
        f"Expected directory name {_REAL_SLUG!r}, got {result.name!r}"
    )
    assert "kitty-specs" in str(result), (
        f"Expected kitty-specs in path, got {result}"
    )


def test_primary_full_ulid_returns_composed_path(real_git_repo: Path) -> None:
    """primary_feature_dir_for_mission accepts a full 26-char ULID (NFR-006)."""
    result = primary_feature_dir_for_mission(real_git_repo, _REAL_MISSION_ID)
    assert result.name == _REAL_MISSION_ID
    assert "kitty-specs" in str(result)

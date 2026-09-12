"""Site A/B diagnosability: ``ref_advance`` meta.json reads fail loud on corruption.

WP02 of ``meta-json-fail-closed-routing-01KZPJ1F``. Routes ``ref_advance``'s two
``meta.json`` decode sites onto the kernel L1 (``kernel.meta_decode.decode_meta``)
so a **present-but-unparseable** committed (site B, ``_committed_meta_object``) or
worktree (site A, ``_meta_change_is_vcs_lock_only``) ``meta.json`` raises
:class:`kernel.meta_decode.MetaDecodeError` **naming the source**, instead of
being silently absorbed to ``{}`` / ``False`` (FR-003..FR-007, US2).

The verdict itself rides the kernel sentinel comparator
(:func:`kernel.vcs_lock.is_vcs_lock_only_change`, absent != present-but-null,
C-005).

**Red-first (git-verifiable).** This file is committed in the commit *preceding*
the routing change. Against that pre-routing tree ``_committed_meta_object`` /
``_meta_change_is_vcs_lock_only`` still parse via the private
``_parse_meta_object`` and silently absorb malformed content, so the two
corrupt-arm ``pytest.raises(MetaDecodeError)`` assertions below fail there
(``git show <routing-parent>:...`` proves it). They pass only after the routing.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from kernel.meta_decode import MetaDecodeError
from kernel.vcs_lock import is_vcs_lock_only_change
from specify_cli.git.ref_advance import (
    _committed_meta_object,
    _meta_change_is_vcs_lock_only,
)

# ref_advance shells out to real ``git show``; both sites need a real repo.
pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_META_REL = "kitty-specs/diag-mission/meta.json"


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed in {cwd}: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "T")
    _git(root, "config", "commit.gpgsign", "false")


def _valid_meta() -> dict[str, object]:
    return {"slug": "diag-mission", "mission_type": "software-dev"}


def _valid_meta_text() -> str:
    return json.dumps(_valid_meta(), sort_keys=True) + "\n"


def _commit_meta(root: Path, content: str) -> Path:
    """Seed a committed ``meta.json`` carrying *content* at HEAD; return its path."""
    meta_path = root / _META_REL
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(content, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed meta.json")
    return meta_path


def _seed_without_meta(root: Path) -> None:
    """Create a HEAD commit that does NOT carry ``meta.json``."""
    (root / "README.md").write_text("seed\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed")


# --- Site B (`_committed_meta_object`): the committed `git show HEAD:path` read --


def test_committed_corrupt_meta_raises_naming_ref_path(tmp_path: Path) -> None:
    """RED-first: a present-but-unparseable committed blob fails loud.

    Pre-routing ``_committed_meta_object`` returns ``{}`` (silent absorb), so
    this ``pytest.raises`` is red on the parent commit. Post-routing it raises
    :class:`MetaDecodeError` naming ``HEAD:<path>`` (FR-004/FR-006, D6 typed +
    identifier assertion).
    """
    root = tmp_path / "repo"
    _init_repo(root)
    _commit_meta(root, "{not valid json")

    with pytest.raises(MetaDecodeError, match="meta.json") as excinfo:
        _committed_meta_object(root, _META_REL, None)
    assert f"HEAD:{_META_REL}" in str(excinfo.value)


def test_committed_meta_absent_at_head_is_benign_empty(tmp_path: Path) -> None:
    """Absent-at-HEAD (``git show`` returncode != 0) stays benign ``{}`` — only a
    present-but-corrupt committed blob raises (FR-006 absent arm preserved)."""
    root = tmp_path / "repo"
    _init_repo(root)
    _seed_without_meta(root)

    assert _committed_meta_object(root, _META_REL, None) == {}


def test_committed_valid_meta_returns_mapping(tmp_path: Path) -> None:
    """A valid committed blob decodes to its mapping (FR-005 happy path)."""
    root = tmp_path / "repo"
    _init_repo(root)
    _commit_meta(root, _valid_meta_text())

    assert _committed_meta_object(root, _META_REL, None) == _valid_meta()


# --- Site A (`_meta_change_is_vcs_lock_only`): the worktree read + comparator ---


def test_worktree_corrupt_meta_raises_naming_path(tmp_path: Path) -> None:
    """RED-first: a present-but-unparseable worktree blob fails loud.

    Pre-routing ``_meta_change_is_vcs_lock_only`` treats a malformed worktree
    read as ``None`` and returns ``False`` (silent absorb), so this
    ``pytest.raises`` is red on the parent commit. Post-routing it raises
    :class:`MetaDecodeError` naming the worktree filesystem path (FR-003, D6).
    """
    root = tmp_path / "repo"
    _init_repo(root)
    meta_path = _commit_meta(root, _valid_meta_text())
    # Tracked-modify the worktree file into malformed content.
    meta_path.write_text("{still not json", encoding="utf-8")

    with pytest.raises(MetaDecodeError, match="meta.json") as excinfo:
        _meta_change_is_vcs_lock_only(root, _META_REL, None)
    assert str(meta_path) in str(excinfo.value)


def test_worktree_vcs_lock_only_change_verdict_unchanged(tmp_path: Path) -> None:
    """FR-005 happy path: a vcs-lock-only worktree edit is still recognised as a
    lock stamp (``True``) after routing onto the kernel comparator."""
    root = tmp_path / "repo"
    _init_repo(root)
    _commit_meta(root, _valid_meta_text())

    worktree_obj = {**_valid_meta(), "vcs": "git", "vcs_locked_at": "2026-08-10T00:00:00+00:00"}
    (root / _META_REL).write_text(json.dumps(worktree_obj, sort_keys=True) + "\n", encoding="utf-8")

    assert _meta_change_is_vcs_lock_only(root, _META_REL, None) is True


def test_worktree_genuine_edit_still_blocks(tmp_path: Path) -> None:
    """A non-lock worktree edit is genuine dirt (``False``) — no false-open."""
    root = tmp_path / "repo"
    _init_repo(root)
    _commit_meta(root, _valid_meta_text())

    worktree_obj = {**_valid_meta(), "friendly_name": "operator renamed"}
    (root / _META_REL).write_text(json.dumps(worktree_obj, sort_keys=True) + "\n", encoding="utf-8")

    assert _meta_change_is_vcs_lock_only(root, _META_REL, None) is False


# --- C-005: absent != present-but-null (the kernel comparator ref_advance rides) --


def test_c005_present_null_lock_field_is_still_lock_only() -> None:
    """A ``vcs_locked_at`` present-but-``None`` vs absent is a *difference*
    (absent != present-but-null), but it is a lock field, so the change stays
    lock-only (``True``). The retired ``.get()`` comparator erased that
    distinction; the sentinel comparator preserves it deterministically."""
    assert is_vcs_lock_only_change({"slug": "m"}, {"slug": "m", "vcs_locked_at": None}) is True


def test_c005_present_null_non_lock_field_blocks() -> None:
    """A **non-lock** field present-but-``None`` vs absent is a real difference,
    so the change is NOT lock-only (``False``). Under the old ``.get()``
    semantics both sides read ``None`` and this collapsed to a false ``True`` —
    the C-005 verdict flip this mission pins (US2 AC1)."""
    assert is_vcs_lock_only_change({"slug": "m"}, {"slug": "m", "friendly_name": None}) is False

"""Diagnosability of ``meta.json`` reads in ``specify_cli.git.ref_advance`` (FR-005).

Mission ``meta-fail-closed-3162-01KZ7FSQ``, WP05 (sites A and B of the bypass set).

Two sites are covered here:

* **Site A** -- :func:`specify_cli.git.ref_advance._meta_change_is_vcs_lock_only`
  (``ref_advance.py:238``), the mission's single **routed** bypass read: its
  read+parse pair is replaced by
  :func:`specify_cli.core.paths.load_meta_fail_closed`, which raises
  :class:`~specify_cli.core.paths.MissionMetaReadError` on a corrupt file.
* **Site B** -- :func:`specify_cli.git.ref_advance._committed_meta_object`
  (``ref_advance.py:192``), **diagnosable only**: corrupt-at-HEAD must be
  distinguishable from absent-at-HEAD, which ``returncode != 0`` already
  separates internally.

**Why the assertions do not simply look for ``"meta.json"``.** The porcelain
line for a dirty ``kitty-specs/<slug>/meta.json`` *already* contains both the
path and the substring ``meta.json``, so an assertion of the form
``"meta.json" in text and path in text`` passes on the UNROUTED baseline and
proves nothing.  Every assertion below therefore also requires the
**diagnosis** -- :data:`_DECODE_PHRASE` -- which no baseline arm emits.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.git.ref_advance import (
    RefAdvanceDirtyWorktreeError,
    _committed_meta_object,
    _meta_change_is_vcs_lock_only,
    advance_branch_ref,
)

# This suite shells out to real git via subprocess fixtures; register it with the
# gate-coverage system (C-006) so test_no_new_orphan_surfaces recognises it.
pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

MISSION_SLUG = "3162-meta-diagnosability"
MISSION_BRANCH = "kitty/mission-3162-meta-diagnosability"
META_RELPATH = f"kitty-specs/{MISSION_SLUG}/meta.json"

# The diagnosis substring. Present ONLY when the corrupt arm fires; absent from
# every porcelain line, so an assertion requiring it cannot pass vacuously.
_DECODE_PHRASE = "could not be decoded"


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


def _valid_meta() -> dict[str, object]:
    """A realistic, schema-valid mission ``meta.json`` payload."""
    return {
        "slug": MISSION_SLUG,
        "mission_slug": MISSION_SLUG,
        "friendly_name": "Meta diagnosability",
        "mission_type": "software-dev",
        "target_branch": "feat/meta-fail-closed-3162",
        "created_at": "2026-08-06T00:00:00+00:00",
    }


def _build_repo(root: Path) -> tuple[Path, Path, str]:
    """Return ``(repo_root, worktree, new_sha)``.

    ``worktree`` has ``MISSION_BRANCH`` checked out at the commit carrying a
    VALID ``meta.json``; ``new_sha`` is a fast-forward descendant of that tip.
    """
    repo_root = root / "repo"
    repo_root.mkdir()
    _git(repo_root, "init", "-q", "-b", "main")
    _git(repo_root, "config", "user.email", "t@example.invalid")
    _git(repo_root, "config", "user.name", "T")
    _git(repo_root, "config", "commit.gpgsign", "false")
    (repo_root / "README.md").write_text("seed\n", encoding="utf-8")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "seed")

    mission_dir = repo_root / "kitty-specs" / MISSION_SLUG
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(
        json.dumps(_valid_meta(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _git(repo_root, "checkout", "-q", "-b", MISSION_BRANCH)
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "mission: seed meta.json")

    (repo_root / "docs").mkdir()
    (repo_root / "docs" / "note.md").write_text("target\n", encoding="utf-8")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "mission: consolidation commit")
    new_sha = _git(repo_root, "rev-parse", "HEAD").stdout.strip()

    _git(repo_root, "reset", "--hard", "HEAD~1")
    _git(repo_root, "checkout", "-q", "main")
    worktree = root / "wt"
    _git(repo_root, "worktree", "add", "-q", str(worktree), MISSION_BRANCH)
    return repo_root, worktree, new_sha


# --------------------------------------------------------------------------
# Site A -- ROUTED onto load_meta_fail_closed(meta_path.parent)
# --------------------------------------------------------------------------


def test_corrupt_worktree_meta_blocks_advance_and_is_diagnosed(tmp_path: Path) -> None:
    """SC-012 site A: a corrupt working-copy ``meta.json`` blocks AND says why.

    RED before routing: the advance is still blocked (the unroutable parse
    returns ``None`` -> "genuine dirt"), but the operator sees only the bare
    porcelain line ``M kitty-specs/.../meta.json`` with no indication that the
    file is undecodable -- indistinguishable from an ordinary edit.
    """
    repo_root, worktree, new_sha = _build_repo(tmp_path)
    (worktree / META_RELPATH).write_text("{not json", encoding="utf-8")

    with pytest.raises(RefAdvanceDirtyWorktreeError) as excinfo:
        advance_branch_ref(repo_root, MISSION_BRANCH, new_sha)

    text = str(excinfo.value)
    # (a) still blocks -- the advance did not happen.
    assert (
        _git(repo_root, "rev-parse", MISSION_BRANCH).stdout.strip() != new_sha
    ), "a corrupt meta.json must not let the ref advance"
    # (b) names meta.json AND the path AND the diagnosis.
    assert "meta.json" in text
    assert META_RELPATH in text
    assert _DECODE_PHRASE in text, (
        "corrupt meta.json must be diagnosed, not reported as an ordinary "
        f"dirty entry; got:\n{text}"
    )


def test_valid_worktree_meta_emits_no_decode_diagnosis(tmp_path: Path) -> None:
    """SC-012 site A negative control: a VALID meta.json produces no diagnosis."""
    repo_root, worktree, new_sha = _build_repo(tmp_path)
    meta = _valid_meta()
    meta["friendly_name"] = "Operator renamed this mission"
    (worktree / META_RELPATH).write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    with pytest.raises(RefAdvanceDirtyWorktreeError) as excinfo:
        advance_branch_ref(repo_root, MISSION_BRANCH, new_sha)

    text = str(excinfo.value)
    # A genuine edit still blocks (no false-open) but is NOT a decode failure.
    assert META_RELPATH in text
    assert _DECODE_PHRASE not in text, (
        f"a valid meta.json must not be reported as undecodable; got:\n{text}"
    )


def test_non_utf8_worktree_meta_is_diagnosed_instead_of_escaping(
    tmp_path: Path,
) -> None:
    """The deliberate behaviour delta at site A -- an IMPROVEMENT, not a regression.

    Baseline: ``meta_path.read_text(encoding="utf-8")`` raises
    :class:`UnicodeDecodeError`, which is a :class:`ValueError` subclass and
    therefore **NOT** caught by the site's ``except OSError``. A non-UTF-8
    ``meta.json`` escapes ``_meta_change_is_vcs_lock_only`` uncaught and crashes
    the dirty-worktree scan.

    After routing, ``load_meta_fail_closed`` -> ``_parse_meta_text`` lists
    ``UnicodeDecodeError`` explicitly (``mission_metadata.py:349``, #3163), so
    the input is blocked-and-diagnosed. ``NFR-003`` binds the four degrade
    sites, not this one.
    """
    repo_root, worktree, new_sha = _build_repo(tmp_path)
    # Invalid UTF-8: a lone 0xFF byte cannot start any UTF-8 sequence.
    (worktree / META_RELPATH).write_bytes(b'{"slug": "\xff\xfe"}')

    with pytest.raises(RefAdvanceDirtyWorktreeError) as excinfo:
        advance_branch_ref(repo_root, MISSION_BRANCH, new_sha)

    text = str(excinfo.value)
    assert "meta.json" in text
    assert META_RELPATH in text
    assert _DECODE_PHRASE in text


def test_absent_worktree_meta_still_returns_false(tmp_path: Path) -> None:
    """Site A's ``None`` (absent) arm is unchanged: absent -> ``False``."""
    repo_root, worktree, _new_sha = _build_repo(tmp_path)
    (worktree / META_RELPATH).unlink()

    assert (
        _meta_change_is_vcs_lock_only(worktree, META_RELPATH, None) is False
    ), "an absent meta.json must remain 'not a lock-only change' (False)"


# --------------------------------------------------------------------------
# Site B -- diagnosable only (_committed_meta_object)
# --------------------------------------------------------------------------


def test_corrupt_blob_at_head_is_diagnosed(tmp_path: Path) -> None:
    """SC-012 site B: corrupt-at-HEAD is diagnosed, naming meta.json and the ref path."""
    repo_root, worktree, _new_sha = _build_repo(tmp_path)
    # Commit a corrupt meta.json so HEAD:<path> exists but does not parse.
    (worktree / META_RELPATH).write_text("{not json", encoding="utf-8")
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-q", "-m", "corrupt meta at HEAD")

    notes: list[str] = []
    result = _committed_meta_object(worktree, META_RELPATH, None, diagnostics=notes)

    # Return contract unchanged: unparseable committed blob -> {}.
    assert result == {}
    assert notes, "corrupt-at-HEAD must emit a diagnosis"
    joined = "\n".join(notes)
    assert "meta.json" in joined
    assert f"HEAD:{META_RELPATH}" in joined
    assert _DECODE_PHRASE in joined


def test_valid_blob_at_head_emits_no_diagnosis(tmp_path: Path) -> None:
    """SC-012 site B negative control: a valid committed blob parses silently."""
    _repo_root, worktree, _new_sha = _build_repo(tmp_path)

    notes: list[str] = []
    result = _committed_meta_object(worktree, META_RELPATH, None, diagnostics=notes)

    assert result["mission_slug"] == MISSION_SLUG
    assert notes == [], f"a valid committed meta.json must not be diagnosed; got {notes}"


def test_absent_at_head_is_not_reported_as_corrupt(tmp_path: Path) -> None:
    """Absent-at-HEAD stays ``{}`` with NO corrupt diagnosis -- the two arms stay distinct.

    ``returncode != 0`` already separates absent-at-HEAD from corrupt-at-HEAD
    internally; this pins that the separation survives.
    """
    _repo_root, worktree, _new_sha = _build_repo(tmp_path)

    notes: list[str] = []
    result = _committed_meta_object(
        worktree, "kitty-specs/never-committed/meta.json", None, diagnostics=notes
    )

    assert result == {}
    assert notes == [], (
        f"absent-at-HEAD must NOT be reported as corrupt-at-HEAD; got {notes}"
    )

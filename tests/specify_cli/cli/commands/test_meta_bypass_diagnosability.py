"""``SC-012``: every ``meta.json`` bypass read is diagnosable (``FR-005``).

Mission ``meta-fail-closed-3162-01KZ7FSQ``, WP05.

**Counting convention, declared inline with every count below**: the mission's
bypass set is **5 read expressions / 6 invocation sites**. The two totals are
never addable. They differ because
:func:`specify_cli.cli.commands.merge_driver._load_json_object` is ONE read
expression invoked at TWO call sites -- the ``ours`` and ``theirs`` arguments
to ``reconcile_meta_payloads``.

This file covers sites **C**, **D** and **E**; sites **A** and **B** live in
``tests/specify_cli/git/test_ref_advance_meta_diagnosability.py`` because they
are git-plumbing and need a real worktree fixture.

| Site | ``module:symbol`` | Covered in |
|---|---|---|
| A | ``git.ref_advance:_meta_change_is_vcs_lock_only`` | ``tests/specify_cli/git/`` (ROUTED) |
| B | ``git.ref_advance:_committed_meta_object`` | ``tests/specify_cli/git/`` |
| C | ``cli.commands.implement_cores:_is_self_write_only_diff`` | here |
| D | ``cli.commands.implement_cores:_committed_meta_mapping`` | here |
| E | ``cli.commands.merge_driver:_load_json_object`` | here (BOTH invocations) |

Every corrupt-fixture assertion is on the message **text** and requires the
file to be named (``meta.json``) **and** the path to appear. A type-only
assertion does not satisfy ``SC-012``. Each corrupt row has a **valid-file
negative control** beside it proving the message is absent on a good file.

**Reachability (review cycle 1 blocker).** ``SC-012``'s bar is *operator-visible*,
not "collected somewhere". The unit-level rows below drive the two
``implement_cores`` helpers directly with a test-allocated sink, which proves the
message text but NOT that anything reaches an operator. The
``TestSitesCandDReachTheOperator`` class is the row that carries ``SC-012`` for
sites C and D: it drives the **production entry point**
(``implement._ensure_planning_artifacts_committed_git``, the same
"real entry point" standard site A's ``advance_branch_ref`` test sets) against a
real git repository and asserts on what the operator actually sees. Those tests
go red on a tree where the sink is not threaded from the production caller.
"""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest
import typer
from rich.console import Console

# This module drives real git repositories via ``subprocess`` (``git init`` plus real
# commits) in TestSitesCandDReachTheOperator, so the marker-correctness gate's Rule 1
# requires a MODULE-level ``git_repo``. Class-level decorators do not satisfy either
# marker gate -- both parse a top-level ``pytestmark`` assignment and never see
# class- or function-level marks. An earlier revision marked only the class, which
# left this file with no module-level pytestmark at all and redded two architectural
# gates (test_pytest_marker_convention, test_pytest_marker_correctness).
pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

from specify_cli.cli.commands.implement_cores import (
    DEFAULT_GIT_PORT,
    _committed_meta_mapping,
    _is_self_write_only_diff,
    _SubprocessGitPort,
)

# The diagnosis substring shared by every bypass site's corrupt arm. Chosen so
# no valid-file path and no ordinary status line can contain it -- an
# assertion requiring it cannot pass vacuously.
_DECODE_PHRASE = "could not be decoded"

_VALID_META: dict[str, object] = {
    "slug": "3162-bypass",
    "mission_slug": "3162-bypass",
    "mission_type": "software-dev",
    "vcs": "git",
}

CORRUPT_JSON = "{not json"

_MISSION_SLUG = "3162-bypass"
_MISSION_META_REPO_REL = f"kitty-specs/{_MISSION_SLUG}/meta.json"
_PLANNING_BRANCH = "main"


class _StubGitPort:
    """Minimal ``GitPort`` stub returning a canned blob for ``show_blob``."""

    def __init__(self, blob: bytes | None) -> None:
        self._blob = blob

    def show_blob(self, repo_root: Path, ref: str, repo_rel: str) -> bytes | None:
        return self._blob


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# Site C -- implement_cores:_is_self_write_only_diff  (1 read expression)
#
# NOT routed. The obstacle is the routed BUDGET, spent by T029 on site A --
# NOT structure: `source` at implement_cores.py:423 is a real resolved
# filesystem path under a `name == _META_JSON_FILENAME` gate (:426) and its
# parent IS a feature dir, so `load_meta_fail_closed` would fit here today.
# --------------------------------------------------------------------------


def test_site_c_corrupt_working_meta_is_diagnosed(tmp_path: Path) -> None:
    """Corrupt working-copy meta.json -> message names meta.json AND the path."""
    repo_rel = "kitty-specs/3162-bypass/meta.json"
    source = _write(tmp_path / repo_rel, CORRUPT_JSON)

    notes: list[str] = []
    result = _is_self_write_only_diff(
        tmp_path, repo_rel, None, git=_StubGitPort(None), diagnostics=notes
    )

    # Return contract unchanged: a corrupt meta.json is NOT a self-write.
    assert result is False
    joined = "\n".join(notes)
    assert "meta.json" in joined
    assert str(source) in joined
    assert _DECODE_PHRASE in joined


def test_site_c_valid_working_meta_emits_no_diagnosis(tmp_path: Path) -> None:
    """Site C valid-file negative control."""
    repo_rel = "kitty-specs/3162-bypass/meta.json"
    _write(tmp_path / repo_rel, json.dumps(_VALID_META))

    notes: list[str] = []
    _is_self_write_only_diff(
        tmp_path,
        repo_rel,
        None,
        git=_StubGitPort(json.dumps(_VALID_META).encode("utf-8")),
        diagnostics=notes,
    )

    assert notes == [], f"a valid meta.json must not be diagnosed; got {notes}"


# --------------------------------------------------------------------------
# Site D -- implement_cores:_committed_meta_mapping  (1 read expression)
# --------------------------------------------------------------------------


def test_site_d_corrupt_committed_blob_is_diagnosed(tmp_path: Path) -> None:
    """Unparseable committed blob -> message names meta.json AND the ref-qualified path."""
    repo_rel = "kitty-specs/3162-bypass/meta.json"

    notes: list[str] = []
    result = _committed_meta_mapping(
        tmp_path,
        repo_rel,
        None,
        git=_StubGitPort(CORRUPT_JSON.encode("utf-8")),
        diagnostics=notes,
    )

    # Return contract unchanged: unparseable -> None.
    assert result is None
    joined = "\n".join(notes)
    assert "meta.json" in joined
    assert repo_rel in joined
    assert _DECODE_PHRASE in joined


def test_site_d_valid_committed_blob_emits_no_diagnosis(tmp_path: Path) -> None:
    """Site D valid-file negative control."""
    repo_rel = "kitty-specs/3162-bypass/meta.json"

    notes: list[str] = []
    result = _committed_meta_mapping(
        tmp_path,
        repo_rel,
        None,
        git=_StubGitPort(json.dumps(_VALID_META).encode("utf-8")),
        diagnostics=notes,
    )

    assert result == _VALID_META
    assert notes == []


def test_site_d_absent_blob_is_not_reported_as_corrupt(tmp_path: Path) -> None:
    """Absent-at-ref stays ``None`` and silent -- distinct from corrupt-at-ref."""
    notes: list[str] = []
    result = _committed_meta_mapping(
        tmp_path,
        "kitty-specs/3162-bypass/meta.json",
        None,
        git=_StubGitPort(None),
        diagnostics=notes,
    )

    assert result is None
    assert notes == [], f"absent must not be reported as corrupt; got {notes}"


def test_default_git_port_is_untouched(tmp_path: Path) -> None:
    """The injected-port default is still the real git adapter (WP05 changed the
    *signatures* of two cores that default to it, never the default itself).

    Both halves are falsifiable, unlike the ``is not None`` this replaced
    (review cycle 1 MINOR / DIR-041): swapping the default for a stub or a fake
    breaks the identity pin, and a default that stopped shelling out to git
    breaks the round-trip -- ``show_blob`` must return the committed bytes for a
    tracked path and ``None`` for one absent at the ref.
    """
    assert isinstance(DEFAULT_GIT_PORT, _SubprocessGitPort)

    repo = _init_repo(tmp_path)
    committed = json.dumps(_VALID_META)
    _stage_mission_meta(repo, committed=committed, working=CORRUPT_JSON)

    assert DEFAULT_GIT_PORT.show_blob(repo, "HEAD", _MISSION_META_REPO_REL) == committed.encode("utf-8")
    assert DEFAULT_GIT_PORT.show_blob(repo, "HEAD", "kitty-specs/absent/meta.json") is None


# --------------------------------------------------------------------------
# Site E -- merge_driver:_load_json_object
#
# ONE read expression invoked at TWO call sites (the `ours` and `theirs`
# arguments to `reconcile_meta_payloads`). BOTH invocations are covered, which
# is the whole difference between "5 read expressions" and "6 invocation
# sites". Its pinned tolerance (missing -> {}, blank -> {}) must survive.
# --------------------------------------------------------------------------


def test_site_e_corrupt_file_is_diagnosed(tmp_path: Path) -> None:
    """Corrupt meta.json -> EventLogMergeError naming meta.json AND the path."""
    from specify_cli.cli.commands.merge_driver import (
        EventLogMergeError,
        _load_json_object,
    )

    path = _write(tmp_path / "meta.json", CORRUPT_JSON)

    with pytest.raises(EventLogMergeError) as excinfo:
        _load_json_object(path)

    text = str(excinfo.value)
    assert "meta.json" in text
    assert str(path) in text
    assert _DECODE_PHRASE in text


def test_site_e_valid_file_emits_no_diagnosis(tmp_path: Path) -> None:
    """Site E valid-file negative control."""
    from specify_cli.cli.commands.merge_driver import _load_json_object

    path = _write(tmp_path / "meta.json", json.dumps(_VALID_META))

    assert _load_json_object(path) == _VALID_META


def test_site_e_pinned_tolerance_survives(tmp_path: Path) -> None:
    """``missing -> {}`` and ``blank -> {}`` are UNCHANGED (pinned by 2709)."""
    from specify_cli.cli.commands.merge_driver import _load_json_object

    assert _load_json_object(tmp_path / "absent.json") == {}
    assert _load_json_object(_write(tmp_path / "blank.json", "   \n")) == {}


@pytest.mark.parametrize("corrupt_side", ["ours", "theirs"])
def test_site_e_both_invocations_are_covered(tmp_path: Path, corrupt_side: str) -> None:
    """BOTH of site E's two invocation sites diagnose a corrupt payload.

    ``merge_driver_meta`` calls ``_load_json_object`` twice -- once for
    ``ours`` and once for ``theirs``. Covering only one would leave half of the
    "6 invocation sites" total unasserted.
    """
    from specify_cli.cli.commands.merge_driver import (
        EventLogMergeError,
        _load_json_object,
    )

    ours = _write(
        tmp_path / "ours" / "meta.json",
        CORRUPT_JSON if corrupt_side == "ours" else json.dumps(_VALID_META),
    )
    theirs = _write(
        tmp_path / "theirs" / "meta.json",
        CORRUPT_JSON if corrupt_side == "theirs" else json.dumps(_VALID_META),
    )
    corrupt_path = ours if corrupt_side == "ours" else theirs

    # Reproduce the call shape at both argument positions.
    with pytest.raises(EventLogMergeError) as excinfo:
        (_load_json_object(ours), _load_json_object(theirs))

    text = str(excinfo.value)
    assert "meta.json" in text
    assert str(corrupt_path) in text
    assert _DECODE_PHRASE in text


# --------------------------------------------------------------------------
# Sites C and D -- REACHABILITY through the production entry point
#
# ``SC-012`` requires an operator-VISIBLE message: "the generic dirty-worktree
# message must no longer be the only thing the operator sees at any of them."
# The rows above allocate the sink themselves, so they would stay green on a
# tree where no production caller supplies one -- exactly the review cycle 1
# blocker. These rows allocate nothing: they drive
# ``implement._ensure_planning_artifacts_committed_git`` (the git EXECUTOR that
# the implement-claim precondition calls, ``implement.py:1716`` post-edit) against a real
# git repository and read the rendered console output.
# --------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    """A real one-commit git repository on ``_PLANNING_BRANCH``."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", _PLANNING_BRANCH)
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


def _stage_mission_meta(repo: Path, *, committed: str, working: str) -> Path:
    """Commit *committed* as the mission's meta.json, then leave *working* dirty.

    Returns the mission directory. The dirty assertion is the fixture's own
    control: with a clean worktree the precondition is a silent no-op and every
    assertion downstream would pass vacuously.
    """
    mission_dir = repo / "kitty-specs" / _MISSION_SLUG
    mission_dir.mkdir(parents=True, exist_ok=True)
    meta = mission_dir / "meta.json"
    meta.write_text(committed, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "mission meta")
    meta.write_text(working, encoding="utf-8")
    assert _git(repo, "status", "--porcelain", str(mission_dir)), "fixture must leave meta.json dirty"
    return mission_dir


class TestSitesCandDReachTheOperator:
    """``SC-012`` for sites C and D, asserted on operator-visible output only."""

    @staticmethod
    def _operator_output(repo: Path, mission_dir: Path, monkeypatch: pytest.MonkeyPatch) -> str:
        """Everything the operator sees from one ``auto_commit=False`` claim.

        The module ``console`` is replaced by a real :class:`rich.console.Console`
        with an explicit width AND height (bypassing TTY / ``COLUMNS`` detection)
        and ``soft_wrap``, so a long ``tmp_path`` is never wrapped mid-path --
        the substring assertions below are then about the message, not about the
        ambient terminal size.
        """
        from specify_cli.cli.commands import implement as implement_module

        buffer = io.StringIO()
        monkeypatch.setattr(
            implement_module,
            "console",
            Console(file=buffer, width=400, height=50, no_color=True, soft_wrap=True),
        )

        # auto_commit=False is the ONLY path that consults the self-write
        # predicate at all, and it refuses with typer.Exit(1) once a planning
        # artifact is left uncommitted -- that refusal is the "generic
        # dirty-worktree message" SC-012 says must no longer stand alone.
        with pytest.raises(typer.Exit):
            implement_module._ensure_planning_artifacts_committed_git(
                repo_root=repo,
                feature_dir=mission_dir,
                mission_slug=_MISSION_SLUG,
                wp_id="WP05",
                planning_branch=_PLANNING_BRANCH,
                auto_commit=False,
            )
        return buffer.getvalue()

    def test_site_c_corrupt_working_meta_is_operator_visible(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Corrupt working-copy meta.json: the operator is told so, by name and path."""
        repo = _init_repo(tmp_path)
        mission_dir = _stage_mission_meta(repo, committed=json.dumps(_VALID_META), working=CORRUPT_JSON)

        output = self._operator_output(repo, mission_dir, monkeypatch)

        assert _DECODE_PHRASE in output, f"site C is not operator-visible; operator saw:\n{output}"
        assert "meta.json" in output
        assert str((mission_dir / "meta.json").resolve()) in output

    def test_site_d_corrupt_committed_meta_is_operator_visible(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unparseable COMMITTED blob with a valid working copy: site D's arm.

        The working meta must parse, otherwise :func:`_is_self_write_only_diff`
        returns at its own corrupt arm (site C) and site D is never reached.
        """
        repo = _init_repo(tmp_path)
        working = json.dumps({**_VALID_META, "friendly_name": "valid working copy"})
        mission_dir = _stage_mission_meta(repo, committed=CORRUPT_JSON, working=working)

        output = self._operator_output(repo, mission_dir, monkeypatch)

        assert _DECODE_PHRASE in output, f"site D is not operator-visible; operator saw:\n{output}"
        assert "meta.json" in output
        assert f"HEAD:{_MISSION_META_REPO_REL}" in output

    def test_valid_meta_reaches_the_operator_without_a_decode_diagnosis(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Negative control: a genuinely-dirty but well-formed meta.json.

        Refuses the claim exactly as before and names the file in the generic
        listing, but says nothing about decoding. Without this row the two
        assertions above could pass on any output that merely mentions
        ``meta.json`` -- it is what makes ``_DECODE_PHRASE`` load-bearing.
        """
        repo = _init_repo(tmp_path)
        working = json.dumps({**_VALID_META, "friendly_name": "a genuine non-lock edit"})
        mission_dir = _stage_mission_meta(repo, committed=json.dumps(_VALID_META), working=working)

        output = self._operator_output(repo, mission_dir, monkeypatch)

        assert _MISSION_META_REPO_REL in output, f"the generic refusal must still list the file; got:\n{output}"
        assert _DECODE_PHRASE not in output, f"a well-formed meta.json must not be diagnosed; got:\n{output}"

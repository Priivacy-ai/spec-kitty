"""Permanent guard: mission create leaves no undisclosed dirty scaffold (#2693).

Originally a red-first P0 reproduction under ``tests/regression/``; the product
defect is FIXED and this test now lives beside its create-command siblings
(``test_mission_create_checkout_restore.py``, ``test_mission_creation_topology.py``)
as a standing regression guard.

DEFECT (fixed)
--------------
``create_mission_core`` (``src/specify_cli/core/mission_creation.py``) used to
commit exactly ONE file — ``meta.json`` — and report the mission complete while
leaving the rest of the generated scaffold untracked *and* undisclosed:

  * ``status.events.jsonl`` — the canonical status log, initialised empty at
    scaffold time and then MUTATED by the step-8 event-emission leg
    (``emit_mission_created_local`` / ``emit_artifact_phase``) which ran *after*
    the sole ``meta.json`` commit, so its events were never committed and never
    reported.
  * ``tasks/.gitkeep`` — untracked and enumerated nowhere.

FIX
---
The event-emission leg now runs BEFORE a single transactional scaffold commit
that stages the full create-owned set — ``meta.json`` + ``status.events.jsonl``
+ ``tasks/README.md`` + ``tasks/.gitkeep`` — in ONE commit. ``spec.md`` remains
intentionally uncommitted (#846, committed later by ``/spec-kitty.specify``) and
is disclosed as a structured uncommitted artifact in the CLI ``--json`` payload,
so it is never both untracked and undisclosed.

INVARIANT
---------
A command that reports mission creation complete does not leave a generated file
both untracked in the working tree AND absent from the reported artifact set:
every generated file is either committed or explicitly disclosed.

Drives the real production entry point ``create_mission_core`` over a real git
repository, hence the ``integration`` + ``git_repo`` marks its siblings use.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mission_runtime import MissionTopology
from specify_cli.core.mission_creation import create_mission_core

from tests._factories import provision_test_charter

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# A non-protected feature branch — ``safe_commit`` refuses to write to a
# protected branch (``main``), mirroring the issue's ``--start-branch feat/repro``.
_FEATURE_BRANCH = "feat/repro"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def _init_git_repo(repo: Path) -> None:
    """A clean checkout with a provisioned charter, on a feature branch, with
    the baseline (charter + empty kitty-specs) committed so the ONLY residue the
    assertion sees is the mission scaffold itself."""
    (repo / ".kittify").mkdir(exist_ok=True)
    provision_test_charter(repo)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    (repo / "kitty-specs" / ".gitkeep").touch()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "Test")
    # Commit the baseline (charter + empty kitty-specs) so it is not itself
    # reported as untracked residue.
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "baseline")
    _git(repo, "branch", "-M", "main")
    _git(repo, "checkout", "-b", _FEATURE_BRANCH)


def _mission_summary(slug: str) -> dict[str, str]:
    title = slug.replace("-", " ").strip() or "test mission"
    return {
        "friendly_name": title.title(),
        "purpose_tldr": f"Deliver {title} cleanly for the team.",
        "purpose_context": (
            f"This mission delivers {title} so product and engineering can move "
            "forward with a clear outcome and shared understanding."
        ),
    }


def _untracked_files(repo: Path) -> list[str]:
    """Repo-relative paths of untracked working-tree files (``git status`` ``??``)."""
    out = _git(repo, "status", "--porcelain").stdout.splitlines()
    untracked: list[str] = []
    for line in out:
        if line.startswith("?? "):
            entry = line[3:].strip()
            if entry.endswith("/"):
                # Directory summary — expand to the files within it.
                for child in sorted((repo / entry).rglob("*")):
                    if child.is_file():
                        untracked.append(str(child.relative_to(repo)))
            else:
                untracked.append(entry)
    return untracked


def test_mission_create_does_not_leave_undisclosed_dirty_scaffold(tmp_path: Path) -> None:
    """After create reports success, no generated file is BOTH untracked in the
    working tree AND absent from the reported artifact set (#2693, fixed).

    Regression guard: ``status.events.jsonl`` and ``tasks/.gitkeep`` are now
    committed transactionally at create time, and ``spec.md`` (intentionally
    uncommitted, #846) stays disclosed in the reported artifact set.
    """
    _init_git_repo(tmp_path)

    result = create_mission_core(
        tmp_path,
        "issue-2693",
        topology=MissionTopology.SINGLE_BRANCH,
        **_mission_summary("issue-2693"),
    )

    feature_dir = result.feature_dir
    feature_rel = feature_dir.relative_to(tmp_path)

    # The artifacts the command reports it produced (the CLI --json envelope
    # echoes this same set as ``created_files``). This is the "structured list"
    # the issue's Expected outcome allows for intentionally-uncommitted files.
    reported = {str(p.relative_to(tmp_path)) for p in result.created_files}

    # Untracked generated files that live under the mission's own directory.
    untracked_in_mission = [
        entry
        for entry in _untracked_files(tmp_path)
        if entry.startswith(f"{feature_rel}/")
    ]

    # The core invariant (#2693): every generated file left untracked must be
    # disclosed to the caller. A file that is neither committed nor reported is
    # silent residue — exactly what the issue rejects.
    undisclosed = [entry for entry in untracked_in_mission if entry not in reported]

    assert not undisclosed, (
        "issue #2693: mission create reported completion but left generated "
        "scaffolding untracked AND undisclosed (neither committed nor listed in "
        f"created_files): {undisclosed}. Expected: one transactionally complete "
        "commit, or a structured list of the artifacts intentionally left "
        "uncommitted."
    )

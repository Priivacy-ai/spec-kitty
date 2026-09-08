"""End-to-end acceptance for the 3.2.6.1 first-run path (#4035, #4033, #3988).

**Why this exists rather than more unit tests.** The scaffold-rollback and
unborn-HEAD tests call ``create_mission_core`` directly with
``allow_worktree_context=True`` and an injected exception. That is the right
shape for pinning those mechanisms, and it is also why they could not have
caught the defect that actually broke the tutorial: running ``specify`` on
``main`` fails with ``refusing to commit to protected branch``, which depends on
real git state and the real command wiring, not on an injected error.

So this module drives the CLI as a **subprocess** against **real temporary git
repositories** and asserts what a user observes: exit codes, how many mission
directories exist, whether a declared coordination branch resolves, and whether
anything is left behind. Every scenario below was a manual shell walkthrough
during the hotfix; this is that walkthrough made deterministic, so a reviewer
can re-run it instead of trusting a transcript.

Run just this file:

    pytest tests/acceptance/test_first_run_path_3_2_6_1.py -v

**Proven to detect the defects, not merely to pass.** Run against a pristine
``v3.2.6`` worktree together with ``test_mission_creation_preflight.py``, 12 of
the 15 tests fail. The three that pass there are guards on paths that were never
broken, not detectors, and that is deliberate:
``test_documented_getting_started_path_succeeds`` and
``test_plan_runs_on_the_mission_the_tutorial_creates`` exercise the
feature-branch path; ``test_committed_owned_checkout_does_not_use_primary_unborn_head``
pins that the owned-checkout unborn-HEAD check reads the right checkout and
does not over-refuse. Re-verified 2026-09-08 after the preflight revision.
Reproduce with::

    git worktree add --detach /tmp/baseline326 v3.2.6
    cp tests/acceptance/test_first_run_path_3_2_6_1.py /tmp/baseline326/tests/acceptance/
    cd /tmp/baseline326 && uv sync --frozen --all-extras
    uv run --no-sync pytest tests/acceptance/test_first_run_path_3_2_6_1.py -v

These are slow by construction (each test does real ``git`` and a real CLI
start-up), so they carry ``integration`` + ``git_repo`` like their siblings.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TIMEOUT = 300


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


def _cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Invoke the CLI the way a user does — a separate process, real argv.

    ``python -m specify_cli`` rather than a ``spec-kitty`` from PATH: PATH may
    hold a different (often stale) install, which would silently test the wrong
    code. See the stale-install gotcha in CLAUDE.md.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("SPEC_KITTY_HOME", str(cwd / ".spec-kitty-home"))
    return subprocess.run(
        [sys.executable, "-m", "specify_cli", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=_TIMEOUT,
        env=env,
        stdin=subprocess.DEVNULL,
    )


def _missions(repo: Path) -> list[str]:
    specs = repo / "kitty-specs"
    return sorted(entry.name for entry in specs.iterdir() if entry.is_dir()) if specs.exists() else []


def _declared_coordination_branch(repo: Path, mission: str) -> str | None:
    meta = json.loads((repo / "kitty-specs" / mission / "meta.json").read_text(encoding="utf-8"))
    value = meta.get("coordination_branch")
    return str(value) if value else None


def _ref_exists(repo: Path, ref: str) -> bool:
    return subprocess.run(["git", "rev-parse", "--verify", "-q", ref], cwd=repo, capture_output=True, check=False).returncode == 0


def _unwrapped(result: subprocess.CompletedProcess[str]) -> str:
    """Combined stdout+stderr with wrapping collapsed.

    Rich hard-wraps console output at the terminal width, so a phrase like
    "protected branch" arrives split across a newline. Matching raw output makes
    a message assertion fail (or, worse, pass only at some widths).
    """
    return " ".join((result.stdout + " " + result.stderr).split())


def _porcelain(repo: Path) -> str:
    return subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """An initialized project with one commit, sitting on ``main``.

    Mirrors the corrected Getting Started steps 1-3. Step 4 (the feature
    branch) is deliberately left to each test, because whether it happened is
    the thing several of these are about.
    """
    repo = tmp_path / "my-spec-project"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "Test")
    init = _cli(repo, "init", ".", "--ai", "claude")
    assert init.returncode == 0, f"`spec-kitty init` failed:\n{init.stdout}\n{init.stderr}"
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "Initial commit")
    return repo


# ---------------------------------------------------------------------------
# #3988 — the documented first-run path must actually work
# ---------------------------------------------------------------------------


def test_documented_getting_started_path_succeeds(project: Path) -> None:
    """Getting Started, verbatim, produces one sound mission.

    "Sound" is the load-bearing word: a mission whose declared coordination
    branch does not exist is the #4033 defect, and it reported success.
    """
    _git(project, "checkout", "-b", "my-first-mission")

    result = _cli(project, "specify", "Build a tiny command-line task list app with add, complete, and delete actions.")

    assert result.returncode == 0, f"the documented path failed:\n{result.stdout}\n{result.stderr}"
    missions = _missions(project)
    assert len(missions) == 1, f"expected exactly one mission, got {missions}"

    branch = _declared_coordination_branch(project, missions[0])
    assert branch is not None
    assert _ref_exists(project, branch), f"meta.json declares {branch!r}, which does not exist in git"


def test_plan_runs_on_the_mission_the_tutorial_creates(project: Path) -> None:
    """The next documented command also works — the mission is usable, not just present."""
    _git(project, "checkout", "-b", "my-first-mission")
    assert _cli(project, "specify", "Build a tiny command-line task list app.").returncode == 0

    mission = _missions(project)[0]
    # The agent's specify workflow authors and commits the specification after
    # CLI scaffold creation. Exercise that documented boundary with real Git.
    spec_file = project / "kitty-specs" / mission / "spec.md"
    spec_file.write_text(
        "# Task List Specification\n\n"
        "## Functional Requirements\n\n"
        "- **FR-001**: Users can add a task with a non-empty title.\n"
        "- **FR-002**: Users can mark an existing task complete.\n"
        "- **FR-003**: Users can delete an existing task by its identifier.\n\n"
        "## Acceptance Scenarios\n\n"
        "Adding a task preserves its title and assigns a stable identifier.\n"
        "Completing that identifier marks only that task complete.\n"
        "Deleting that identifier removes it from the task list.\n",
        encoding="utf-8",
    )
    committed = _cli(
        project,
        "spec-commit",
        "--mission",
        mission,
        "--message",
        "Add task list specification",
        str(spec_file),
        "--json",
    )
    assert committed.returncode == 0, _unwrapped(committed)
    tracked_spec = _git(project, "show", f"HEAD:{spec_file.relative_to(project).as_posix()}")
    assert tracked_spec.stdout == spec_file.read_text(encoding="utf-8")
    result = _cli(project, "plan", "--mission", mission, "--json")

    assert result.returncode == 0, f"`plan` failed on a freshly created mission:\n{result.stdout}\n{result.stderr}"
    assert json.loads(result.stdout)["result"] == "success", result.stdout
    assert (project / "kitty-specs" / mission / "plan.md").is_file()


def test_specify_on_main_refuses_cleanly(project: Path) -> None:
    """On ``main``, ``specify`` refuses — and leaves nothing behind.

    The refusal itself is correct and intended: planning artifacts may not land
    on a protected branch. What #4035 reported is the debris, so that is what is
    asserted here alongside the exit code.
    """
    result = _cli(project, "specify", "task-list")

    assert result.returncode != 0, "expected a non-zero exit on a protected branch"
    combined = _unwrapped(result)
    assert "refusing to commit to protected branch" in combined, f"expected a protected-branch refusal, got:\n{combined}"
    assert _missions(project) == [], "a refused create left a mission directory behind"
    assert _porcelain(project) == "", "a refused create left the working tree dirty"


# ---------------------------------------------------------------------------
# #4035 — the reporter's exact scenario
# ---------------------------------------------------------------------------


def test_reporter_scenario_yields_exactly_one_mission(project: Path) -> None:
    """The bug report, replayed end to end.

    Before the fix this produced two ``kitty-specs/<slug>-<ULID>/`` directories
    for one intended mission, one of them dead and invisible to every branch.
    This asserting **1** is the whole point of the release.
    """
    failed = _cli(project, "specify", "task-list", "--mission-type", "software-dev", "--json")
    assert failed.returncode != 0
    assert _missions(project) == [], "step 1 left an orphan scaffold — this is the #4035 defect"

    recovered = _cli(
        project,
        "agent",
        "mission",
        "create",
        "task-list",
        "--mission-type",
        "software-dev",
        "--friendly-name",
        "Task List",
        "--purpose-tldr",
        "add/edit/delete tasks",
        "--start-branch",
        "feat/task-list",
        "--json",
    )

    assert recovered.returncode == 0, f"the documented recovery failed:\n{recovered.stdout}\n{recovered.stderr}"
    missions = _missions(project)
    assert len(missions) == 1, f"one intended mission produced {len(missions)} directories: {missions}"


def test_documented_recovery_from_the_protected_branch_error(project: Path) -> None:
    """Troubleshooting's advice works: branch, retry, one mission."""
    assert _cli(project, "specify", "task-list").returncode != 0

    _git(project, "checkout", "-b", "my-first-mission")
    retried = _cli(project, "specify", "task-list")

    assert retried.returncode == 0, f"retry on a feature branch failed:\n{retried.stdout}\n{retried.stderr}"
    assert len(_missions(project)) == 1


# ---------------------------------------------------------------------------
# #4033 — unborn HEAD
# ---------------------------------------------------------------------------


def test_unborn_head_refuses_before_writing_anything(tmp_path: Path) -> None:
    """A repo with no commits cannot host a mission, and is told so.

    Before the fix this exited 0 and produced a mission declaring a
    coordination branch that could never have been created.
    """
    repo = tmp_path / "unborn"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "Test")
    assert _cli(repo, "init", ".", "--ai", "claude").returncode == 0
    heads = list((repo / ".git" / "refs" / "heads").glob("*")) if (repo / ".git" / "refs" / "heads").exists() else []
    assert heads == [], f"fixture invalid: the repo already has a branch ({heads})"

    result = _cli(repo, "specify", "task-list")

    assert result.returncode != 0, "expected a non-zero exit on an unborn HEAD"
    combined = _unwrapped(result)
    assert "no commits yet" in combined, f"expected the no-commits refusal, got:\n{combined}"
    assert _missions(repo) == [], "the refusal still wrote a scaffold"


def test_unborn_head_error_names_a_remedy_that_works(tmp_path: Path) -> None:
    """A guard that blocks without a working recovery is worse than the bug.

    Runs the exact command the error prescribes and asserts the next attempt
    gets somewhere — specifically, past the unborn-HEAD refusal.
    """
    repo = tmp_path / "unborn-recover"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "Test")
    assert _cli(repo, "init", ".", "--ai", "claude").returncode == 0

    blocked = _cli(repo, "specify", "task-list")
    assert "git commit --allow-empty -m 'Initial commit'" in _unwrapped(blocked)

    _git(repo, "commit", "--allow-empty", "-m", "Initial commit")
    _git(repo, "checkout", "-b", "my-first-mission")
    retried = _cli(repo, "specify", "task-list")

    assert retried.returncode == 0, f"the prescribed remedy did not unblock the user:\n{retried.stdout}\n{retried.stderr}"
    assert len(_missions(repo)) == 1


# ---------------------------------------------------------------------------
# Release metadata
# ---------------------------------------------------------------------------


def test_version_is_the_patch_release(project: Path) -> None:
    result = _cli(project, "--version")
    assert result.returncode == 0
    assert "3.2.6.1" in _unwrapped(result)


def test_no_retired_org_in_user_facing_urls() -> None:
    """The patch must not republish ``Priivacy-ai`` links to PyPI.

    Package metadata plus the runtime constant that builds issue URLs — the two
    places a user actually lands on. Docstring references are out of scope on
    this line and are deliberately not asserted.
    """
    pyproject = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    urls_block = pyproject.split("[project.urls]", 1)[1].split("\n[", 1)[0]
    assert "Priivacy-ai" not in urls_block, f"[project.urls] still names the retired org:\n{urls_block}"

    issue_matrix = (_REPO_ROOT / "src" / "specify_cli" / "tasks" / "issue_matrix.py").read_text(encoding="utf-8")
    assert '_CANONICAL_REPO_SLUG = "spec-kitty/spec-kitty"' in issue_matrix

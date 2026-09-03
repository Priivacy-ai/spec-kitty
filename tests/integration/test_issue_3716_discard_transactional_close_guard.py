"""Permanent guard: ``mission close --discard`` is transactional and honest.

Issue #3716 (FIXED): the ``--discard`` path on a coord-topology mission had two
defects, both surfaced through the REAL ``spec-kitty mission close --discard
--force`` entry point:

Defect 1 — uncommitted ``meta.json`` flatten.
    ``_flatten_discarded_mission`` pops ``coordination_branch`` + ``topology``
    and sets ``flattened: true`` in ``meta.json`` as the LAST write on the path,
    and used to have NO commit leg. A command that reported success left
    ``M kitty-specs/<slug>/meta.json`` in ``git status --porcelain``. The fix
    (``mission_type._commit_flattened_meta``) commits the flatten to the PRIMARY
    surface — the mission's ``target_branch`` — never the coordination branch,
    which the discard already deleted.

Defect 2 — completion provenance on an abandoned mission.
    The retrospective the discard path persisted was stamped
    ``provenance.kind: runtime_post_completion`` because ``ProvenanceKind`` had
    no abandonment member. The fix adds ``runtime_abandoned`` and threads it from
    the discard leg (``_discard_mission`` → ``teardown_coordination_topology`` →
    ``run_retrospective_postcondition`` → the facilitator's ``provenance_kind``),
    so an abandoned mission is no longer tagged as completed.

These are now permanent regression guards against those two defects recurring.
The sibling ``test_mission_close_discard_coord_teardown.py`` drives the same real
CLI entry point and split-brain coord fixture.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from specify_cli.cli.commands import mission_type
from specify_cli.coordination import CoordinationWorkspace

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

runner = CliRunner()

MISSION_ID = "01J6XW9K000000000000000000"
MID8 = MISSION_ID[:8]
SLUG = f"demo-coord-mission-{MID8}"
COORD_BRANCH = CoordinationWorkspace.branch_name(SLUG, MID8)

# The completion provenance kind that must NOT be stamped on a discarded mission.
_COMPLETION_PROVENANCE_KIND = "runtime_post_completion"
# The abandonment provenance kind the discard leg must stamp instead (#3716).
_ABANDONED_PROVENANCE_KIND = "runtime_abandoned"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def coord_mission(tmp_path: Path) -> Path:
    """A coordination-topology mission in the split-brain surface layout.

    Primary branch carries meta.json (with ``coordination_branch`` +
    ``topology: coord``) + lanes.json; the coordination branch's mission dir is
    status-only; a real coordination worktree is materialised.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".kittify").mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    # A real spec-kitty project gitignores its own sync-state frame (see e.g.
    # ``test_accept_residual_partition.py``); without this, the whole-tree
    # porcelain assertion below would spuriously trip on the offline queue's
    # ambient ``.kittify/sync-state.json`` local write, which is unrelated to
    # the #3716 defect under test.
    (repo / ".gitignore").write_text(
        ".worktrees/\n.kittify/sync-state.json\n", encoding="utf-8"
    )

    fdir = repo / "kitty-specs" / SLUG
    fdir.mkdir(parents=True)
    (fdir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": SLUG,
                "mission_id": MISSION_ID,
                "mid8": MID8,
                "coordination_branch": COORD_BRANCH,
                "mission_branch": COORD_BRANCH,
                "target_branch": "main",
                "topology": "coord",
                "flattened": False,
            }
        ),
        encoding="utf-8",
    )
    (fdir / "lanes.json").write_text(
        json.dumps(
            {
                "version": 1,
                "mission_slug": SLUG,
                "mission_id": MISSION_ID,
                "mission_branch": COORD_BRANCH,
                "target_branch": "main",
                "computed_at": "2026-01-01T00:00:00+00:00",
                "computed_from": "test",
                "lanes": [
                    {
                        "lane_id": "lane-a",
                        "wp_ids": ["WP01"],
                        "write_scope": [],
                        "predicted_surfaces": [],
                        "depends_on_lanes": [],
                        "parallel_group": 0,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (fdir / "status.events.jsonl").write_text("", encoding="utf-8")
    (fdir / "status.json").write_text("{}", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed primary mission surface")

    # Coordination branch: status-only mission dir (drop planning artifacts).
    _git(repo, "branch", COORD_BRANCH)
    _git(repo, "checkout", "-q", COORD_BRANCH)
    _git(
        repo,
        "rm",
        "-q",
        f"kitty-specs/{SLUG}/meta.json",
        f"kitty-specs/{SLUG}/lanes.json",
    )
    _git(repo, "commit", "-q", "-m", "coord: status-only mission surface")
    _git(repo, "checkout", "-q", "main")

    # Materialise the real coordination worktree (full checkout of coord branch).
    CoordinationWorkspace.resolve(repo, SLUG, MID8)
    assert CoordinationWorkspace.is_present(repo, SLUG, MID8)
    return repo


def _run_discard(repo: Path) -> None:
    result = runner.invoke(
        mission_type.app,
        ["close", "--mission", SLUG, "--discard", "--force"],
        env={"PWD": str(repo)},
    )
    assert result.exit_code == 0, result.output


def _porcelain_paths(repo: Path) -> list[str]:
    out = _git(repo, "status", "--porcelain").stdout
    return [line[3:] for line in out.splitlines() if line.strip()]


def test_close_discard_commits_meta_flatten(
    coord_mission: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defect 1: after ``--discard`` reports success, its own ``meta.json``
    flatten is committed — the WHOLE working tree is clean, not just
    ``meta.json`` in isolation.

    (squad) Strengthened from a ``meta.json``-only check to a whole-tree
    ``git status --porcelain`` empty assertion: the retrospective the discard
    path persists (``retrospective.yaml``, pinned by
    ``test_teardown_seam_persist_before_destroy``) is written to the SAME
    working tree by the SAME command invocation, so a narrower check that
    only inspects ``meta.json`` would miss an uncommitted retrospective write
    landing alongside it. A real spec-kitty project's own ambient
    ``.kittify/sync-state.json`` is gitignored by the fixture above so it
    cannot produce a false positive here.
    """
    repo = coord_mission
    monkeypatch.chdir(repo)

    _run_discard(repo)

    dirty = _porcelain_paths(repo)
    assert dirty == [], (
        "issue #3716 defect 1 (squad-strengthened): `mission close --discard` "
        "reported success but left the working tree dirty — either its own "
        "meta.json flatten, or the retrospective it persists alongside it, is "
        f"uncommitted. git status --porcelain: {dirty!r}"
    )


def test_close_discard_retrospective_provenance_is_abandoned(
    coord_mission: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defect 2: the retrospective persisted by ``--discard`` is stamped with
    abandonment provenance, never completion provenance.
    """
    repo = coord_mission
    monkeypatch.chdir(repo)

    _run_discard(repo)

    retro_path = repo / "kitty-specs" / SLUG / "retrospective.yaml"
    assert retro_path.exists(), (
        "the discard path is expected to persist a retrospective "
        "(pinned by test_teardown_seam_persist_before_destroy)"
    )
    data = yaml.safe_load(retro_path.read_text(encoding="utf-8"))
    kind = (data.get("provenance") or {}).get("kind")
    assert kind != _COMPLETION_PROVENANCE_KIND, (
        "issue #3716 defect 2: a discarded/abandoned mission must NOT be stamped "
        f"with completion provenance ({kind!r})."
    )
    assert kind == _ABANDONED_PROVENANCE_KIND, (
        "issue #3716 defect 2: the discard leg must stamp the abandonment "
        f"provenance kind {_ABANDONED_PROVENANCE_KIND!r}; got {kind!r}."
    )

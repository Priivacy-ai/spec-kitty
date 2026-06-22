"""WP05 — single write-surface authority for planning commits (FR-007, #2063, SC-004).

Covers:

* **T025** — ``safe_commit_cmd`` separates its two responsibilities (NFR-002): the
  generic operator-file path keeps ``--to-branch``/HEAD inference; the
  mission-aware planning path (a ``kitty-specs/<slug>/`` artifact for a resolvable
  mission) resolves its destination via the WP03 seam, never from
  ``get_current_branch``.
* **T026** — a coord-topology planning commit (``spec.md``) lands on the
  **seam-resolved** coordination branch (NOT primary HEAD), AND the committed
  ``spec.md`` is **read back** from the same seam-resolved surface via the
  next-command read leg (the #2063 round-trip SC-004 demands).

These tests exercise the REAL seam (``resolve_placement_only`` /
``candidate_feature_dir_for_mission``) on a protected primary — a test that only
mocks the router or asserts the WRITE leg is insufficient (renata / SC-004).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.coordination.commit_router import commit_for_mission
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.missions._read_path_resolver import candidate_feature_dir_for_mission

from tests.git.protected_target_fixtures import (  # noqa: F401 — pytest fixture re-export
    ProtectedTargetRepo,
    build_protected_target_repo,
    protected_target_repo,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.regression]

# Realistic identity (NFR-005 / test-data policy): full ULID, derived mid8, and a
# production-shaped slug whose tail IS the mid8 (the mission-identity naming the
# read-path resolver's mid8_from_slug heuristic recovers).
_FULL_ULID = "01KVPR00WP05AUTH0000000001"
_MID8 = _FULL_ULID[:8]
_SLUG = f"write-surface-authority-{_MID8}"
# The coord branch reconstructs VERBATIM and is idempotent on an already-embedded
# ``-<mid8>`` tail (coord_reconstruct_branch), so the mid8 appears ONCE.
_COORD_BRANCH = f"kitty/mission-{_SLUG}"
_SPEC_BODY = "# Spec\n\nFR-007: the planning commit lands on the seam-resolved surface.\n"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _seed_coord_mission(repo_root: Path) -> tuple[Path, Path]:
    """Seed a coord-topology mission (meta + spec.md) + the coordination branch."""
    feature_dir = repo_root / "kitty-specs" / _SLUG
    feature_dir.mkdir(parents=True)
    meta = {
        "mission_id": _FULL_ULID,
        "mission_slug": _SLUG,
        "mid8": _MID8,
        "coordination_branch": _COORD_BRANCH,
        "mission_type": "software-dev",
        "friendly_name": "Write Surface Authority E2E",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    spec_path = feature_dir / "spec.md"
    spec_path.write_text(_SPEC_BODY, encoding="utf-8")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-m", "chore: seed coord-topology mission")
    _git(repo_root, "branch", _COORD_BRANCH)
    return feature_dir, spec_path


# ---------------------------------------------------------------------------
# T026 — coord-topology planning commit WRITES to + READS BACK from the seam surface
# ---------------------------------------------------------------------------


class TestCoordTopologyPlanningCommitRoundTrip:
    """#2063 / SC-004: write lands on the seam-resolved surface AND reads back from it."""

    def test_spec_commit_lands_and_reads_back_from_coordination_surface(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", raising=False)
        repo = build_protected_target_repo(tmp_path)
        repo.assert_target_is_protected()
        feature_dir, spec_path = _seed_coord_mission(repo.repo_root)

        # New spec content so there is something to commit.
        spec_path.write_text(_SPEC_BODY + "\nFR-009: status emission converges.\n", encoding="utf-8")
        expected_body = spec_path.read_text(encoding="utf-8")

        # WRITE leg: route through the REAL seam (resolve_placement_only classifies
        # the coord topology). No router mock — the placement_ref is the value the
        # seam computes, not a stub.
        policy = ProtectionPolicy.resolve(repo.repo_root)
        result = commit_for_mission(
            repo_root=repo.repo_root,
            mission_slug=_SLUG,
            files=(spec_path,),
            message="spec: seam-resolved planning commit",
            policy=policy,
        )

        assert result.status == "committed", f"diagnostic={result.diagnostic!r}"
        assert result.placement_ref == _COORD_BRANCH, (
            "WRITE leg: the planning commit must land on the seam-resolved "
            f"coordination branch, not primary HEAD; got {result.placement_ref!r}"
        )

        # READ-BACK leg (SC-004): resolve the next-command read surface the way
        # /spec-kitty.tasks would (candidate_feature_dir_for_mission, the coord-aware
        # resolver) and assert the committed spec.md content is recoverable from THAT
        # surface — the #2063 round-trip, not merely placement_ref == coord branch.
        read_surface = candidate_feature_dir_for_mission(repo.repo_root, _SLUG)
        read_back_spec = read_surface / "spec.md"
        assert read_back_spec.exists(), (
            "READ-BACK leg: the next-command read surface "
            f"({read_surface}) does not expose the committed spec.md — the write "
            "and read legs diverge (the #2063 desync)."
        )
        assert read_back_spec.read_text(encoding="utf-8") == expected_body, (
            "READ-BACK leg: spec.md read from the seam-resolved surface does not "
            "match the committed content — SC-004 round-trip is broken."
        )

        # The read surface must be the coordination worktree (not the primary dir),
        # proving the round-trip is on the SAME seam-resolved surface as the write.
        assert ".worktrees" in str(read_surface), (
            "READ-BACK leg: a coord-topology mission's read surface must be the "
            f"materialised coordination worktree; got {read_surface}"
        )

    def test_negative_primary_read_does_not_see_the_coord_commit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Anti-fakeable: the PRIMARY checkout must NOT carry the committed spec change.

        Proves the write actually moved off primary HEAD onto the coord surface —
        if the commit had landed on primary, this would find the new content there
        and the round-trip assertion above would be vacuous.
        """
        monkeypatch.delenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", raising=False)
        repo = build_protected_target_repo(tmp_path)
        feature_dir, spec_path = _seed_coord_mission(repo.repo_root)
        new_body = _SPEC_BODY + "\nonly-on-coord marker.\n"
        spec_path.write_text(new_body, encoding="utf-8")

        policy = ProtectionPolicy.resolve(repo.repo_root)
        commit_for_mission(
            repo_root=repo.repo_root,
            mission_slug=_SLUG,
            files=(spec_path,),
            message="spec: coord-only marker",
            policy=policy,
        )

        # The committed content lives on the coord branch, not on the primary HEAD.
        primary_show = subprocess.run(
            ["git", "show", f"main:kitty-specs/{_SLUG}/spec.md"],
            cwd=repo.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert "only-on-coord marker" not in primary_show.stdout, (
            "primary HEAD (main) carries the coord-only marker — the commit did "
            "NOT route to the coordination surface (the #2063 write-surface bug)."
        )


# ---------------------------------------------------------------------------
# T025 — safe-commit separates its two responsibilities (FR-007 / NFR-002)
# ---------------------------------------------------------------------------


class TestSafeCommitTwoResponsibilities:
    """The generic operator-file path stays HEAD-driven; the mission-aware path uses the seam."""

    def test_generic_path_resolves_from_to_branch_not_the_seam(self, tmp_path: Path) -> None:
        """A non-mission file with --to-branch resolves the explicit ref (generic path)."""
        from specify_cli.cli.commands.safe_commit_cmd import _resolve_commit_target

        operator_file = tmp_path / "notes.txt"
        operator_file.write_text("operator note\n", encoding="utf-8")

        target = _resolve_commit_target(
            explicit_to_branch="lane-x",
            repo_root=tmp_path,
            files=[operator_file],
        )
        assert target.ref == "lane-x"

    def test_generic_path_without_to_branch_uses_head(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A non-mission file without --to-branch infers HEAD (generic path preserved)."""
        import specify_cli.cli.commands.safe_commit_cmd as mod

        operator_file = tmp_path / "config.toml"
        operator_file.write_text("x = 1\n", encoding="utf-8")
        monkeypatch.setattr(mod, "get_current_branch", lambda _root: "lane-head")

        target = mod._resolve_commit_target(
            explicit_to_branch=None,
            repo_root=tmp_path,
            files=[operator_file],
        )
        assert target.ref == "lane-head", "generic HEAD inference must be preserved (NFR-002)"

    def test_mission_aware_path_resolves_via_seam_not_head(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A kitty-specs/<slug>/ artifact for a resolvable mission resolves via the seam.

        Asserts the seam value is used AND that ``get_current_branch`` is never
        consulted as the destination decision (the #2063 root) on this path.
        """
        import specify_cli.cli.commands.safe_commit_cmd as mod
        from mission_runtime import CommitTarget, CommitTargetKind

        spec = tmp_path / "kitty-specs" / "001-demo" / "spec.md"
        spec.parent.mkdir(parents=True)
        spec.write_text("# Spec\n", encoding="utf-8")

        head_consulted = False

        def _spy_head(_root: Path) -> str:
            nonlocal head_consulted
            head_consulted = True
            return "should-not-be-the-destination"

        monkeypatch.setattr(mod, "get_current_branch", _spy_head)
        monkeypatch.setattr(
            "mission_runtime.resolve_placement_only",
            lambda _root, _slug: CommitTarget(ref="kitty/mission-001-demo-AAAA1111", kind=CommitTargetKind.COORDINATION),
        )

        target = mod._resolve_commit_target(
            explicit_to_branch=None,
            repo_root=tmp_path,
            files=[spec],
        )
        assert target.ref == "kitty/mission-001-demo-AAAA1111"
        assert target.kind is CommitTargetKind.COORDINATION
        assert not head_consulted, (
            "mission-aware path consulted get_current_branch as the destination "
            "decision (the #2063 root); it must resolve via the WP03 seam instead."
        )

    def test_unresolvable_mission_path_falls_back_to_generic_head(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A kitty-specs-looking path whose seam can't resolve degrades to the generic path.

        Guards against the discriminator hard-failing a legitimate commit when the
        mission isn't resolvable yet (no churn for missing missions).
        """
        import specify_cli.cli.commands.safe_commit_cmd as mod
        from mission_runtime import ActionContextError

        spec = tmp_path / "kitty-specs" / "ghost" / "spec.md"
        spec.parent.mkdir(parents=True)
        spec.write_text("# Spec\n", encoding="utf-8")

        def _raise(_root: Path, _slug: str) -> object:
            raise ActionContextError("FEATURE_CONTEXT_UNRESOLVED", "no such mission")

        monkeypatch.setattr("mission_runtime.resolve_placement_only", _raise)
        monkeypatch.setattr(mod, "get_current_branch", lambda _root: "fallback-head")

        target = mod._resolve_commit_target(
            explicit_to_branch=None,
            repo_root=tmp_path,
            files=[spec],
        )
        assert target.ref == "fallback-head", (
            "an unresolvable mission path must fall back to the generic HEAD path, "
            "not raise — keeping legitimate commits functional."
        )

    def test_mission_slug_discriminator_only_fires_for_kitty_specs_paths(self, tmp_path: Path) -> None:
        """The discriminator returns a slug only for kitty-specs/<slug>/ artifacts."""
        from specify_cli.cli.commands.safe_commit_cmd import _mission_slug_from_paths

        operator = tmp_path / "src" / "main.py"
        operator.parent.mkdir(parents=True)
        operator.write_text("x\n", encoding="utf-8")
        assert _mission_slug_from_paths(tmp_path, [operator]) is None

        spec = tmp_path / "kitty-specs" / "042-mission" / "plan.md"
        spec.parent.mkdir(parents=True)
        spec.write_text("y\n", encoding="utf-8")
        assert _mission_slug_from_paths(tmp_path, [spec]) == "042-mission"

"""Unit tests for the runtime-state gate exemption (FR-007, C-004).

Covers the NAMED allowlist — ``status.events.jsonl``, ``status.json``,
``review-cycle-N.md`` (glob), ``issue-matrix.md``, ``acceptance-matrix.json``,
``notes.md`` — anchored to the RUNNING mission's OWN ``feature_dir``. The
exemption fires BEFORE the path-heuristic classifier (mirroring the existing
move/exception exemptions) and must NOT exempt another mission's runtime
files, nor spec.md/plan.md/tasks.md, which stay reviewable (C-004).

Two layers are tested:

* Pure unit tests against :func:`assess_file`/:func:`check_diff_compliance`
  (no I/O — the classifier is deliberately testable without git or the
  filesystem).
* A thin integration test through
  :func:`specify_cli.bulk_edit.gate.check_review_diff_compliance`, which
  verifies the ``feature_dir`` -> ``feature_dir_rel`` anchoring wiring end to
  end against a real git repo.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.bulk_edit.diff_check import (
    assess_file,
    check_diff_compliance,
)
from specify_cli.bulk_edit.gate import check_review_diff_compliance
from specify_cli.bulk_edit.occurrence_map import OccurrenceMap


pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_map(
    categories: dict[str, dict[str, str]] | None = None,
) -> OccurrenceMap:
    """Build an OccurrenceMap where every classifiable category is do_not_change.

    Deliberately restrictive: any file that reaches the path-heuristic
    classifier (i.e. is NOT exempted) will violate, so tests can assert
    "still classifies/violates" without depending on category-action nuance.
    """
    categories = categories or {
        "code_symbols": {"action": "do_not_change"},
        "user_facing_strings": {"action": "do_not_change"},
        "serialized_keys": {"action": "do_not_change"},
    }
    raw = {
        "target": {"term": "oldName", "operation": "rename"},
        "categories": categories,
        "exceptions": [],
    }
    return OccurrenceMap(
        target_term="oldName",
        target_replacement=None,
        target_operation="rename",
        categories=categories,
        exceptions=[],
        status=None,
        raw=raw,
    )


OWN_FEATURE_DIR = "kitty-specs/coord-commit-integrity-01KY5JS8"
OTHER_FEATURE_DIR = "kitty-specs/some-other-mission-01ABCXYZ"


# ---------------------------------------------------------------------------
# (a) own status.events.jsonl -> exempt
# ---------------------------------------------------------------------------


class TestOwnRuntimeStateExempt:
    @pytest.mark.parametrize(
        "basename",
        [
            "status.events.jsonl",
            "status.json",
            "review-cycle-1.md",
            "review-cycle-12.md",
            "issue-matrix.md",
            "acceptance-matrix.json",
            "notes.md",
        ],
    )
    def test_own_runtime_state_file_is_exempt(self, basename: str) -> None:
        path = f"{OWN_FEATURE_DIR}/{basename}"
        result = assess_file(path, _make_map(), feature_dir_rel=OWN_FEATURE_DIR)

        assert result.path == path
        assert result.category is None
        assert result.source == "runtime-state"
        assert result.action is None
        assert result.violation is False
        assert basename in result.reason

    def test_own_review_cycle_under_wp_subdir_is_exempt(self) -> None:
        # review-cycle-N.md lives under kitty-specs/<mission>/tasks/<WP-slug>/.
        path = f"{OWN_FEATURE_DIR}/tasks/WP05-gate-exemption/review-cycle-1.md"
        result = assess_file(path, _make_map(), feature_dir_rel=OWN_FEATURE_DIR)

        assert result.source == "runtime-state"
        assert result.violation is False

    def test_check_diff_compliance_passes_own_runtime_state_only_diff(self) -> None:
        changed_files = [
            f"{OWN_FEATURE_DIR}/status.events.jsonl",
            f"{OWN_FEATURE_DIR}/status.json",
        ]
        result = check_diff_compliance(changed_files, _make_map(), OWN_FEATURE_DIR)

        assert result.passed is True
        assert result.errors == []
        assert all(a.source == "runtime-state" for a in result.assessments)


# ---------------------------------------------------------------------------
# (b) another mission's runtime file -> NOT exempt
# ---------------------------------------------------------------------------


class TestOtherMissionRuntimeStateNotExempt:
    def test_other_missions_status_events_not_exempt(self) -> None:
        path = f"{OTHER_FEATURE_DIR}/status.events.jsonl"
        result = assess_file(path, _make_map(), feature_dir_rel=OWN_FEATURE_DIR)

        assert result.source != "runtime-state"
        # status.events.jsonl carries no recognized extension in the
        # path-heuristic rules, so it falls through as unclassified — still
        # a violation, just for a different (FR-008) reason than exemption.
        assert result.violation is True

    def test_no_feature_dir_rel_never_exempts(self) -> None:
        # feature_dir_rel=None means "cannot anchor" -- must never exempt.
        path = f"{OWN_FEATURE_DIR}/status.events.jsonl"
        result = assess_file(path, _make_map(), feature_dir_rel=None)

        assert result.source != "runtime-state"

    def test_sibling_directory_prefix_is_not_treated_as_nested(self) -> None:
        # kitty-specs/coord-commit-integrity-01KY5JS8-other is NOT under
        # kitty-specs/coord-commit-integrity-01KY5JS8 despite the string
        # prefix match risk -- the anchor must respect path boundaries.
        path = "kitty-specs/coord-commit-integrity-01KY5JS8-other/status.json"
        result = assess_file(path, _make_map(), feature_dir_rel=OWN_FEATURE_DIR)

        assert result.source != "runtime-state"


# ---------------------------------------------------------------------------
# (c) spec.md/plan.md/tasks.md under the same feature_dir -> still classify
# ---------------------------------------------------------------------------


class TestReviewableSurfaceStillClassifies:
    @pytest.mark.parametrize("basename", ["spec.md", "plan.md", "tasks.md"])
    def test_planning_artifacts_are_not_exempt_even_under_own_feature_dir(
        self, basename: str
    ) -> None:
        path = f"{OWN_FEATURE_DIR}/{basename}"
        result = assess_file(path, _make_map(), feature_dir_rel=OWN_FEATURE_DIR)

        assert result.source != "runtime-state"
        # .md classifies as user_facing_strings, which this fixture map marks
        # do_not_change -- still reviewable, still blockable.
        assert result.category == "user_facing_strings"
        assert result.violation is True


# ---------------------------------------------------------------------------
# (d) a non-runtime file under the feature_dir -> still classify/violate
# ---------------------------------------------------------------------------


class TestNonRuntimeFileStillClassifies:
    def test_source_file_under_feature_dir_is_not_exempt(self) -> None:
        path = f"{OWN_FEATURE_DIR}/contracts/gate-and-doctor-contracts.md"
        result = assess_file(path, _make_map(), feature_dir_rel=OWN_FEATURE_DIR)

        assert result.source != "runtime-state"
        assert result.category == "user_facing_strings"
        assert result.violation is True

    def test_occurrence_map_yaml_is_not_exempt(self) -> None:
        # occurrence_map.yaml itself is mission bookkeeping too, but it is
        # deliberately NOT in the FR-007 allowlist (it is the artifact the
        # gate is built on, not runtime state) -- confirm it still classifies.
        path = f"{OWN_FEATURE_DIR}/occurrence_map.yaml"
        result = assess_file(path, _make_map(), feature_dir_rel=OWN_FEATURE_DIR)

        assert result.source != "runtime-state"
        assert result.category == "serialized_keys"


# ---------------------------------------------------------------------------
# Integration: gate.py wiring (feature_dir -> feature_dir_rel anchoring)
# ---------------------------------------------------------------------------


def _run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _commit(repo: Path, message: str) -> str:
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", message)
    return _run_git(repo, "rev-parse", "HEAD")


REVIEW_DIFF_OCCURRENCE_MAP = """\
target:
  term: oldName
  operation: rename
categories:
  code_symbols:
    action: do_not_change
  user_facing_strings:
    action: do_not_change
  serialized_keys:
    action: do_not_change
"""


@pytest.mark.git_repo
class TestCheckReviewDiffComplianceAnchoring:
    """End-to-end: feature_dir nested under repo_root, real git diff."""

    def _make_repo_with_mission(self, tmp_path: Path) -> tuple[Path, Path]:
        repo = tmp_path / "repo"
        repo.mkdir()
        _run_git(repo, "init")
        _run_git(repo, "config", "user.email", "test@example.com")
        _run_git(repo, "config", "user.name", "Test User")

        feature_dir = repo / OWN_FEATURE_DIR
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(
            json.dumps({"change_mode": "bulk_edit"}), encoding="utf-8"
        )
        (feature_dir / "occurrence_map.yaml").write_text(
            REVIEW_DIFF_OCCURRENCE_MAP, encoding="utf-8"
        )
        (repo / "README.md").write_text("placeholder\n", encoding="utf-8")
        _commit(repo, "initial")
        return repo, feature_dir

    def test_own_status_events_exempt_end_to_end(self, tmp_path: Path) -> None:
        repo, feature_dir = self._make_repo_with_mission(tmp_path)
        base = _run_git(repo, "rev-parse", "HEAD")
        (feature_dir / "status.events.jsonl").write_text("{}\n", encoding="utf-8")
        _commit(repo, "runtime state append")

        result = check_review_diff_compliance(
            feature_dir=feature_dir,
            repo_root=repo,
            base_ref=base,
            head_ref="HEAD",
        )

        assert result is not None
        assert result.passed is True
        assert all(a.source == "runtime-state" for a in result.assessments)

    def test_other_missions_runtime_file_not_exempt_end_to_end(
        self, tmp_path: Path
    ) -> None:
        repo, feature_dir = self._make_repo_with_mission(tmp_path)
        other_dir = repo / OTHER_FEATURE_DIR
        other_dir.mkdir(parents=True)
        base = _run_git(repo, "rev-parse", "HEAD")
        (other_dir / "status.events.jsonl").write_text("{}\n", encoding="utf-8")
        _commit(repo, "other mission runtime state append")

        result = check_review_diff_compliance(
            feature_dir=feature_dir,
            repo_root=repo,
            base_ref=base,
            head_ref="HEAD",
        )

        assert result is not None
        assert result.passed is False
        assert any(
            a.path.endswith("status.events.jsonl") and a.source != "runtime-state"
            for a in result.assessments
        )

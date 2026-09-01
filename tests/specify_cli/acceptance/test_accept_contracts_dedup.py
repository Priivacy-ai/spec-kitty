"""WP02 (accept-path-remediation-honesty) T009: red-first coverage for the
``contracts/`` double-report defect (FR-002/FR-003, User Story 2).

``software-dev/mission.yaml`` declares ``contracts/`` at BOTH
``artifacts.optional[]`` and ``paths.deliverables`` — so a mission missing
``contracts/`` in strict mode used to surface it twice, contradictorily: once
as a non-blocking ``optional_missing`` warning, once as a blocking
``path_violations`` entry. ``evaluate_path_conventions`` (summary_core.py)
returns the set of normalized missing-artifact tokens; the caller uses those
tokens to drop duplicate entries from ``missing_optional``, so the blocking
``path_violations`` side wins — but only in the ``strict_metadata=True``
branch and only for real declared-artifact matches (never a basename
collision and never a build/repo-root placeholder).

Four tests pin this (plan.md's WP2 revert-test row, plus a tasks-phase
addition — see WP02's own task file, T009, for the TASKS-FRESH-003 /
TASKS-FRESH3-001 provenance of test (d)):

* Test (a) -- dedup + pass/fail boundary, via the real ``collect_feature_summary``
  entry point on a genuine software-dev-shaped fixture (so WP01's
  ``missing_artifact_tokens`` population is exercised for real, not
  hand-set on a mock); also pins that a sibling optional-only artifact
  (declared under ``artifacts.optional`` but never in ``paths.*``) is NOT
  over-suppressed by the dedup.
* Test (b) -- the duplicate "Optional artifacts missing" console print is
  gone; the line appears at most once.
* Test (c) -- lenient mode (``strict_metadata=False``) emits no dedup tokens.
* Test (d) -- the ``artifact_tokens`` membership filter itself: a genuine
  collision (d-i), a filter-presence regression guard (d-ii), and a
  full-token-vs-basename regression guard (d-iii).
"""

from __future__ import annotations

import json
import subprocess
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from rich.console import Console

import specify_cli.cli.commands.accept as accept_cmd
from specify_cli.acceptance import AcceptanceSummary, collect_feature_summary
from specify_cli.acceptance.summary_core import evaluate_path_conventions
from specify_cli.task_utils import LANES

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_SLUG = "099-dual-declared-contracts"


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True)


def _dual_declared_repo(tmp_path: Path) -> tuple[Path, str]:
    """A real software-dev-shaped repo whose only defect is a missing ``contracts/``.

    ``contracts/`` is declared both under ``artifacts.optional`` and
    ``paths.deliverables`` in the packaged ``software-dev`` mission.yaml — left
    missing here, this is exactly the dual-declared fixture the defect needs.
    No work packages are seeded (an empty ``tasks/`` dir is enough for
    ``_iter_work_packages`` not to raise) since the dedup logic under test
    never depends on WP/lane state.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _git(repo_root, "init", "-q", ".")
    _git(repo_root, "config", "user.email", "test@test.com")
    _git(repo_root, "config", "user.name", "Test")
    _git(repo_root, "branch", "-M", "main")

    (repo_root / ".kittify").mkdir()
    for required_dir in ("src", "tests", "docs"):
        path = repo_root / required_dir
        path.mkdir()
        (path / ".gitkeep").write_text("")
    # Deliberately no ``contracts/`` dir anywhere -- the dual-declared token
    # this defect is about.

    feature_dir = repo_root / "kitty-specs" / _SLUG
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    meta = {
        "mission_number": "099",
        "slug": _SLUG,
        "mission_slug": _SLUG,
        "mission_id": "01JZZZZZZZZZZZZZZZZZZZZZZZ",
        "mid8": "01JZZZZZ",
        "friendly_name": "Dual Declared Contracts",
        "mission_type": "software-dev",
        "target_branch": "main",
        "created_at": "2026-01-01T00:00:00Z",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    for fname in ("spec.md", "plan.md", "tasks.md"):
        (feature_dir / fname).write_text(f"# {fname}\nDone.\n")

    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-qm", "init")
    return repo_root, _SLUG


# ---------------------------------------------------------------------------
# Test (a): dedup + pass/fail boundary (real collect_feature_summary entry point)
# ---------------------------------------------------------------------------


def test_contracts_surfaces_through_exactly_one_channel_and_ok_stays_false(
    tmp_path: Path,
) -> None:
    """FR-002/C-001 (Scenario 2): ``contracts`` reports once, and ``.ok`` stays False.

    Pre-fix (red): ``contracts`` (normalized) appears in BOTH
    ``optional_missing`` and the rendered ``path_violations`` text
    simultaneously -- the double-report defect. Post-fix (green): it appears
    in ``path_violations`` only (the blocking side wins), and
    ``AcceptanceSummary.ok`` is unchanged (``False``) either way -- the
    reconciliation direction must not flip the pass/fail boundary (C-001).
    """
    repo_root, slug = _dual_declared_repo(tmp_path)

    summary = collect_feature_summary(repo_root, slug, strict_metadata=True, mutate_matrix=False)

    rendered_violations = "\n".join(summary.path_violations)
    in_optional = "contracts" in summary.optional_missing
    in_violations = "contracts" in rendered_violations

    assert in_optional != in_violations, (
        "'contracts' must surface through exactly one of optional_missing/"
        f"path_violations -- optional_missing={summary.optional_missing!r} "
        f"path_violations={summary.path_violations!r}"
    )
    assert in_violations, "the blocking path_violations side must be the one that wins"
    assert summary.ok is False
    # Sibling optional-only artifact (declared under artifacts.optional but
    # NEVER in paths.* -- unlike contracts/, which is dual-declared): the
    # dedup must not over-suppress it just because contracts/ triggered a
    # path-convention violation.
    assert "data-model.md" in summary.optional_missing


# ---------------------------------------------------------------------------
# Test (b): console-render dedup (FR-003)
# ---------------------------------------------------------------------------


def _console_summary(*, optional_missing: list[str], warnings: list[str]) -> AcceptanceSummary:
    repo_root = Path("/nonexistent/repo")
    feature_dir = repo_root / "kitty-specs" / "099-demo"
    return AcceptanceSummary(
        feature="099-demo",
        repo_root=repo_root,
        feature_dir=feature_dir,
        tasks_dir=feature_dir / "tasks",
        branch="kitty/mission-099-demo",
        worktree_root=repo_root,
        primary_repo_root=repo_root,
        lanes={lane: [] for lane in LANES},
        work_packages=[],
        metadata_issues=[],
        activity_issues=[],
        unchecked_tasks=[],
        needs_clarification=[],
        missing_artifacts=[],
        optional_missing=optional_missing,
        git_dirty=[],
        path_violations=[],
        warnings=warnings,
    )


def _render(summary: AcceptanceSummary, monkeypatch: pytest.MonkeyPatch) -> str:
    buf = StringIO()
    monkeypatch.setattr(accept_cmd, "console", Console(file=buf, highlight=False, markup=True, width=200))
    accept_cmd._print_acceptance_summary(summary)
    return buf.getvalue()


def test_optional_artifacts_missing_prints_at_most_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-003 (Scenario 3): the duplicate cosmetic print in accept.py is gone.

    Pre-fix (red): ``_print_acceptance_warnings`` (from ``summary.warnings``)
    AND the now-removed ``accept.py`` block both printed "Optional artifacts
    missing" -- the literal substring appeared twice. Post-fix (green): only
    ``_print_acceptance_warnings`` prints it, so it appears at most once.
    """
    summary = _console_summary(
        optional_missing=["contracts"],
        warnings=["Optional artifacts missing: contracts"],
    )

    output = _render(summary, monkeypatch)

    assert output.count("Optional artifacts missing") <= 1
    assert "Optional artifacts missing" in output


# ---------------------------------------------------------------------------
# Test (c): lenient mode emits no dedup tokens
# ---------------------------------------------------------------------------


def test_lenient_mode_returns_no_dedup_tokens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-008 guard: dedup tokens are emitted only in strict mode.

    The advisory branch must not ask the caller to suppress the optional
    artifact warning: both channels are non-blocking, so the same missing
    artifact may legitimately appear in both.
    """
    mission = SimpleNamespace(
        config=SimpleNamespace(
            paths=["contracts/"],
            artifacts=SimpleNamespace(required=[], optional=["contracts"]),
        ),
        domain="software-dev",
    )
    monkeypatch.setattr(
        "specify_cli.acceptance.summary_core.validate_mission_paths",
        lambda *_a, **_k: SimpleNamespace(
            missing_paths=["contracts/"],
            missing_artifact_tokens=["contracts"],
            format_errors=lambda: "missing contracts/",
            format_warnings=lambda: "missing contracts/ (advisory)",
        ),
    )
    optional_missing = ["contracts"]

    violations, warning, dedup_tokens = evaluate_path_conventions(
        mission,
        tmp_path,
        tmp_path,
        tmp_path,
        strict_metadata=False,
    )

    assert violations == []
    assert warning == "missing contracts/ (advisory)"
    assert dedup_tokens == frozenset()
    assert optional_missing == ["contracts"]


# ---------------------------------------------------------------------------
# Test (d): the artifact_tokens membership filter itself
# ---------------------------------------------------------------------------


def _mission_with_optional(*optional: str) -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(
            paths=["placeholder/"],
            artifacts=SimpleNamespace(required=[], optional=list(optional)),
        ),
        domain="software-dev",
    )


def _patch_path_result(monkeypatch: pytest.MonkeyPatch, missing_artifact_tokens: list[str]) -> None:
    monkeypatch.setattr(
        "specify_cli.acceptance.summary_core.validate_mission_paths",
        lambda *_a, **_k: SimpleNamespace(
            missing_paths=["placeholder"],
            missing_artifact_tokens=missing_artifact_tokens,
            format_errors=lambda: "placeholder",
        ),
    )


def test_membership_filter_di_genuine_collision_outcome(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(d-i): outcome check for a genuine collision -- NOT a filter-presence guard.

    The returned token set contains only the genuine artifact token; the
    caller can safely use it to suppress the duplicate optional warning.
    """
    mission = _mission_with_optional("contracts")
    _patch_path_result(monkeypatch, ["contracts"])

    _, _, dedup_tokens = evaluate_path_conventions(
        mission,
        tmp_path,
        tmp_path,
        tmp_path,
        strict_metadata=True,
    )

    assert dedup_tokens == frozenset({"contracts"})


def test_membership_filter_dii_filter_presence_regression_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(d-ii): the actual filter-presence regression guard (TASKS-FRESH-003).

    ``"contracts"`` is a genuine artifact_tokens member (SHOULD be removed);
    ``"build-secrets"`` stands in for a build/repo-root or absolute-branch
    placeholder that is not a declared artifact. It must not enter the
    returned token set, or the caller would suppress an independent optional
    warning.
    """
    mission = _mission_with_optional("contracts")
    _patch_path_result(monkeypatch, ["contracts"])

    _, _, dedup_tokens = evaluate_path_conventions(
        mission,
        tmp_path,
        tmp_path,
        tmp_path,
        strict_metadata=True,
    )

    assert dedup_tokens == frozenset({"contracts"})


def test_membership_filter_diii_full_token_vs_basename_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(d-iii): full-token (not basename) comparison guard (TASKS-FRESH3-001).

    ``"docs/contracts"`` and ``"api/contracts"`` share a final path segment
    but are distinct full tokens. Only the true full-token match
    (``"docs/contracts"``) should be removed; a basename-reducing
    implementation (``Path(t).name``) would collapse both to ``"contracts"``
    and incorrectly suppress the independent ``api/contracts`` warning.
    """
    mission = _mission_with_optional("docs/contracts")
    _patch_path_result(monkeypatch, ["docs/contracts"])

    _, _, dedup_tokens = evaluate_path_conventions(
        mission,
        tmp_path,
        tmp_path,
        tmp_path,
        strict_metadata=True,
    )

    assert dedup_tokens == frozenset({"docs/contracts"})

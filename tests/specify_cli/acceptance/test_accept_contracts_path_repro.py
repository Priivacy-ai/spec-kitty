"""WP04 (accept-path-remediation-honesty-01M0TWZP) T013-T014: the single,
named, runnable FR-007 repro fixture.

Mission: ``accept-path-remediation-honesty-01M0TWZP``.
Source issues: #3730 (this mission), #3085 (the maintainer triage comment
this fixture satisfies -- 2026-08-02: "add a focused repro/acceptance
fixture ... before implementation").
Functions under test: :func:`specify_cli.validators.paths.validate_mission_paths`
and :func:`specify_cli.acceptance.collect_feature_summary`.

``software-dev/mission.yaml`` (``src/specify_cli/missions/software-dev/mission.yaml``,
the canonical runtime tree per C-003 -- NOT ``packs/built-in/missions/``) declares
``contracts/`` at BOTH ``artifacts.optional[]`` (line ~145) and
``paths.deliverables`` (line ~154). Before this mission's fix (WP01-WP03), a
mission missing ``contracts/`` on disk exhibited two defects simultaneously:

1. **Wrong-path-reported defect** (#3085a / FR-001): ``validate_mission_paths``
   reported the bare declared token (``"contracts/"``) instead of the
   resolved, feature_dir-relative location it actually tested
   (``kitty-specs/<slug>/contracts/``) -- so remediation pointed a reader at
   the wrong directory.
2. **Double-reporting defect** (#3085b / FR-002/FR-003): the same missing
   ``contracts/`` surfaced through BOTH a non-blocking
   ``AcceptanceSummary.optional_missing`` warning AND a blocking
   ``path_violations`` entry -- a self-contradictory report.

This fixture builds a real, on-disk ``software-dev``-shaped mission layout
(no hand-built ``PathValidationResult``/``AcceptanceSummary`` stand-ins
anywhere) and drives it through the real entry points:

* ``validate_mission_paths`` directly, for the wrong-path assertion
  (Assertion 1).
* ``collect_feature_summary`` directly, for the double-reporting assertion
  on the ``AcceptanceSummary`` object (Assertion 2).
* the real ``accept`` CLI command (``--json --diagnose``, via
  ``CliRunner``), for an independently-falsifiable double-reporting
  assertion computed directly on the parsed JSON payload's own
  ``optional_missing``/``path_violations`` keys (Assertion 3) -- see the
  WP04 task file's ``>>> DEVIATION FROM plan.md (TASKS-FRESH-002) <<<`` note
  for why this is NOT a JSON-vs-object comparison (a literal comparison
  against Assertion 2's own result would be structurally guaranteed to pass
  whenever Assertion 2 passes, since ``AcceptanceSummary.to_dict()`` is a
  direct read of the same attributes -- see ``acceptance/__init__.py:430,432``
  -- making it non-falsifiable for FR-002/Scenario 4).

Reversibility (T015, FR-007/SC-004/NFR-001): reverse-applying WP01+WP02's
``src/`` hunks (``e8b87a5dd``, ``ebcb77301``) flips Assertions 1-3 from pass
to fail -- see this WP's implementation notes / mission report for the
concrete before/after evidence.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app as root_app
from specify_cli.acceptance import collect_feature_summary
from specify_cli.mission import get_mission_for_feature
from specify_cli.validators.paths import _normalize_path_token, validate_mission_paths

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_SLUG = "098-fr007-contracts-repro"

runner = CliRunner()


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True)


def _dual_declared_repro_repo(tmp_path: Path) -> tuple[Path, str, Path]:
    """A real, on-disk ``software-dev``-shaped repo reproducing both #3085 defects.

    Mirrors the established fixture-building convention in
    ``test_accept_contracts_dedup.py``'s ``_dual_declared_repo`` (WP02):
    ``src/``, ``tests/``, ``docs/`` exist; ``contracts/`` -- declared at BOTH
    ``artifacts.optional`` and ``paths.deliverables`` in the packaged
    ``software-dev`` mission.yaml -- is deliberately left missing. No work
    packages are seeded (an empty ``tasks/`` dir suffices).

    Returns ``(repo_root, slug, feature_dir)``.
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
    # both #3085 defects are about.

    feature_dir = repo_root / "kitty-specs" / _SLUG
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    meta = {
        "mission_number": "098",
        "slug": _SLUG,
        "mission_slug": _SLUG,
        "mission_id": "01JYYYYYYYYYYYYYYYYYYYYYYY",
        "mid8": "01JYYYYY",
        "friendly_name": "FR-007 Contracts Repro",
        "mission_type": "software-dev",
        "target_branch": "main",
        "created_at": "2026-01-01T00:00:00Z",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    for fname in ("spec.md", "plan.md", "tasks.md"):
        (feature_dir / fname).write_text(f"# {fname}\nDone.\n")

    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-qm", "init")
    return repo_root, _SLUG, feature_dir


# ---------------------------------------------------------------------------
# Assertion 1 -- wrong-path-reported defect (FR-001), via validate_mission_paths
# directly
# ---------------------------------------------------------------------------


def test_assertion1_reported_path_is_the_resolved_location_not_the_bare_token(
    tmp_path: Path,
) -> None:
    """FR-001 / #3085a: the reported missing-path string is the resolved,
    feature_dir-relative location actually tested, not the bare declared token.

    Pre-WP1 (red): ``result.missing_paths`` contains the bare declared token
    ``"contracts/"`` -- pointing a reader at the wrong (repo-root) directory.
    Post-WP1 (green): it contains the resolved location
    ``kitty-specs/<slug>/contracts/``.
    """
    repo_root, slug, feature_dir = _dual_declared_repro_repo(tmp_path)
    mission = get_mission_for_feature(feature_dir, project_root=repo_root)

    result = validate_mission_paths(mission, repo_root, feature_dir=feature_dir)

    expected_resolved = f"kitty-specs/{slug}/contracts/"
    assert result.missing_paths == [expected_resolved], (
        f"expected exactly the resolved location {expected_resolved!r}, got {result.missing_paths!r}"
    )
    assert "contracts/" not in result.missing_paths, (
        "the bare declared token must not be reported in place of the resolved location"
    )


# ---------------------------------------------------------------------------
# Assertion 2 -- double-reporting defect (FR-002/FR-003), via
# collect_feature_summary directly
# ---------------------------------------------------------------------------


def test_assertion2_contracts_surfaces_through_exactly_one_channel(
    tmp_path: Path,
) -> None:
    """FR-002/FR-003 / #3085b: ``contracts`` (normalized) is reported through
    exactly one of ``AcceptanceSummary.optional_missing`` /
    the rendered ``path_violations`` text -- never both, never neither.

    Pre-WP2 (red): ``"contracts"`` appears in BOTH ``optional_missing`` and
    ``path_violations`` simultaneously -- the self-contradictory
    double-report. Post-WP2 (green): it appears in ``path_violations`` only
    (the blocking side wins, per C-001 -- the pass/fail boundary must not
    move).
    """
    repo_root, slug, _feature_dir = _dual_declared_repro_repo(tmp_path)

    summary = collect_feature_summary(repo_root, slug, strict_metadata=True, mutate_matrix=False)

    rendered_violations = "\n".join(summary.path_violations)
    in_optional = any(_normalize_path_token(entry) == "contracts" for entry in summary.optional_missing)
    in_violations = "contracts" in rendered_violations

    assert in_optional != in_violations, (
        "'contracts' must surface through exactly one of optional_missing/"
        f"path_violations -- optional_missing={summary.optional_missing!r} "
        f"path_violations={summary.path_violations!r}"
    )
    assert in_violations, "the blocking path_violations side must be the one that wins (C-001)"
    assert summary.ok is False, (
        "the reconciliation must not flip the pass/fail boundary (C-001) -- .ok must stay False"
    )


# ---------------------------------------------------------------------------
# Assertion 3 -- --json internal consistency, independently falsifiable on the
# parsed JSON payload's own keys (deliberate deviation from plan.md, see
# module docstring / WP04 task file TASKS-FRESH-002 note)
# ---------------------------------------------------------------------------


def test_assertion3_json_payload_reports_contracts_through_exactly_one_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-002 Edge Case / Scenario 4 of User Story 2, via the real ``accept``
    CLI's ``--json`` output.

    Computes the exactly-one-of check directly on the parsed JSON payload's
    own ``optional_missing``/``path_violations`` keys -- NOT by comparing the
    JSON to Assertion 2's ``AcceptanceSummary``-object-level result. A
    comparison-based check would be structurally guaranteed to pass
    regardless of WP2's correctness, since ``AcceptanceSummary.to_dict()``
    (``acceptance/__init__.py:430,432``) is a direct read of the same
    attributes Assertion 2 already reads -- both sides would be wrong
    identically on a WP2 revert (TASKS-VERIFY-001).

    Pre-WP2 (red): the parsed JSON payload's own ``optional_missing`` AND
    ``path_violations`` keys both contain ``"contracts"`` simultaneously.
    Post-WP2 (green): only ``path_violations`` does.
    """
    repo_root, slug, _feature_dir = _dual_declared_repro_repo(tmp_path)
    monkeypatch.chdir(repo_root)

    result = runner.invoke(root_app, ["accept", "--mission", slug, "--json", "--diagnose"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)

    optional_missing = payload["optional_missing"]
    path_violations = payload["path_violations"]
    rendered_violations = "\n".join(path_violations)
    in_optional = any(_normalize_path_token(entry) == "contracts" for entry in optional_missing)
    in_violations = "contracts" in rendered_violations

    assert in_optional != in_violations, (
        "the parsed --json payload's own 'contracts' entry must surface through "
        f"exactly one of optional_missing/path_violations -- optional_missing={optional_missing!r} "
        f"path_violations={path_violations!r}"
    )
    assert in_violations, "the blocking path_violations side must be the one that wins (C-001)"

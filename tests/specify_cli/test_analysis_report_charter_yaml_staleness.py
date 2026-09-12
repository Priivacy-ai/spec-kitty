"""Test that analysis-report charter staleness input hashes charter.yaml, not charter.md."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]


def _write_required_artifacts(feature_dir: Path) -> None:
    """Write minimal artifacts needed for analysis report hashing."""
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n\nFR-001.\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")


def test_analysis_report_staleness_hashes_charter_yaml_when_md_absent(tmp_path):
    """SC-001: staleness computes without error when charter.md is absent.

    The analysis-report staleness input must key on charter.yaml, not charter.md.
    This test verifies that:
    1. charter.yaml is the resolved canonical source for staleness hashing
    2. charter.md is NOT used (even if we had the fallbacks)
    3. Staleness computation succeeds when only charter.yaml exists
    """
    from charter.bundle import CHARTER_YAML
    from specify_cli.analysis_report import check_analysis_report_current, collect_input_artifact_hashes, write_analysis_report

    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "test-charter-yaml-01KS"
    _write_required_artifacts(feature_dir)

    # Seed charter.yaml (the canonical source)
    charter_yaml_path = repo_root / CHARTER_YAML
    charter_yaml_path.parent.mkdir(parents=True, exist_ok=True)
    charter_yaml_path.write_text("charter_version: 1\n", encoding="utf-8")

    # Explicitly delete charter.md to ensure staleness doesn't look for it
    for candidate in [
        repo_root / ".kittify" / "charter" / "charter.md",
        repo_root / "charter" / "charter.md",
    ]:
        if candidate.exists():
            candidate.unlink()

    # Test 1: collect_input_artifact_hashes must hash charter.yaml, not charter.md
    hashes = collect_input_artifact_hashes(feature_dir, repo_root)
    assert "charter" in hashes
    # FR-007/NFR-001: repo-relative path (canonical_root falls back to repo_root
    # outside git), never absolute.
    assert hashes["charter"]["path"] == str(charter_yaml_path.relative_to(repo_root))
    assert hashes["charter"]["sha256"] is not None, "charter.yaml must be hashed"

    # Test 2: write_analysis_report must succeed (staleness input is valid)
    result = write_analysis_report(
        feature_dir=feature_dir,
        repo_root=repo_root,
        body="# Analysis Report\n\nNo issues.\n",
    )
    assert result.path.exists()
    assert result.input_artifacts["charter"]["sha256"] is not None

    # Test 3: check_analysis_report_current must compute without error
    freshness = check_analysis_report_current(feature_dir, repo_root)
    assert freshness.ok is True, "Staleness check must succeed with charter.yaml present"


def test_analysis_report_staleness_no_regression_both_files_present(tmp_path):
    """Regression pin: behavior unchanged when both charter.yaml and charter.md exist.

    When both files are present (upgrade scenario), staleness still keys on
    charter.yaml (not charter.md), but the behavior is unchanged.
    """
    from charter.bundle import CHARTER_YAML
    from specify_cli.analysis_report import check_analysis_report_current, collect_input_artifact_hashes, write_analysis_report

    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "test-both-files-01KS"
    _write_required_artifacts(feature_dir)

    # Seed BOTH charter.yaml and the legacy charter.md
    charter_yaml_path = repo_root / CHARTER_YAML
    charter_yaml_path.parent.mkdir(parents=True, exist_ok=True)
    charter_yaml_path.write_text("charter_version: 1\n", encoding="utf-8")

    # Also write the legacy charter.md (at the canonical .kittify location)
    legacy_md = repo_root / ".kittify" / "charter" / "charter.md"
    legacy_md.parent.mkdir(parents=True, exist_ok=True)
    legacy_md.write_text("# Charter\n\nLegacy markdown.\n", encoding="utf-8")

    # Test: staleness must hash charter.yaml, not charter.md
    hashes = collect_input_artifact_hashes(feature_dir, repo_root)
    # FR-007/NFR-001: repo-relative path (canonical_root falls back to repo_root
    # outside git), never absolute.
    assert hashes["charter"]["path"] == str(charter_yaml_path.relative_to(repo_root))
    # Should hash charter.yaml, not the legacy charter.md
    charter_yaml_hash = hashes["charter"]["sha256"]
    assert charter_yaml_hash is not None

    # Write report with this hash
    result = write_analysis_report(
        feature_dir=feature_dir,
        repo_root=repo_root,
        body="# Analysis Report\n\nNo issues.\n",
    )
    assert result.input_artifacts["charter"]["sha256"] == charter_yaml_hash

    # Staleness check must still pass (behavior unchanged)
    freshness = check_analysis_report_current(feature_dir, repo_root)
    assert freshness.ok is True


def test_analysis_report_staleness_hashes_charter_md_when_yaml_absent(tmp_path):
    """Landing-fold regression: charter.md-only (pre-compile) projects still

    get a staleness input hashed from their actual charter content. WP03
    (b4a518844) repointed ``_charter_path`` to charter.yaml only and dropped
    both charter.md candidates, on the premise that charter.md is "legacy
    and not universally present" -- but a project that authored charter.md
    and has not yet run ``charter sync``/compile is the common pre-compile
    shape, not a legacy one. This must key on the canonical
    ``.kittify/charter/charter.md`` (not the fully-legacy, already-refused
    ``<root>/charter/charter.md``).
    """
    from specify_cli.analysis_report import check_analysis_report_current, collect_input_artifact_hashes, write_analysis_report

    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "test-charter-md-only-01KS"
    _write_required_artifacts(feature_dir)

    # Seed ONLY charter.md (no charter.yaml compiled yet).
    charter_md_path = repo_root / ".kittify" / "charter" / "charter.md"
    charter_md_path.parent.mkdir(parents=True, exist_ok=True)
    charter_md_path.write_text("# Authored Charter\n\nNo yaml compiled yet.\n", encoding="utf-8")

    hashes = collect_input_artifact_hashes(feature_dir, repo_root)
    assert "charter" in hashes
    # FR-007/NFR-001: repo-relative path (canonical_root falls back to repo_root
    # outside git), never absolute.
    assert hashes["charter"]["path"] == str(charter_md_path.relative_to(repo_root))
    assert hashes["charter"]["sha256"] is not None, "charter.md must be hashed when charter.yaml is absent"

    result = write_analysis_report(
        feature_dir=feature_dir,
        repo_root=repo_root,
        body="# Analysis Report\n\nNo issues.\n",
    )
    assert result.path.exists()
    assert result.input_artifacts["charter"]["sha256"] is not None

    freshness = check_analysis_report_current(feature_dir, repo_root)
    assert freshness.ok is True, "Staleness check must succeed with only charter.md present"

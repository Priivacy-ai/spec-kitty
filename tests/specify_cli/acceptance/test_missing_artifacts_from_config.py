"""WP03 (accept-path-convention-override-01M14P41) T014: coverage for the
#3785 optional-artifact SSOT fold.

``_missing_artifacts`` used to derive its optional-artifact set from a hardcoded
list that had drifted from the mission's declared ``artifacts.optional`` -- it
omitted software-dev's ``checklists/`` (FR-006, User Story 3). The fold makes the
set config-driven via :meth:`Mission.get_optional_artifacts`, with a load-bearing
fallback (C-009) for the ``mission is None`` and artifacts-less-config cases so the
#3783 regression (a ``SimpleNamespace`` mission with no ``artifacts`` attribute)
never raises ``AttributeError``.

Tests here pin, with dict/set-equality assertions:

* The optional set is derived from the real ``software-dev/mission.yaml`` and now
  INCLUDES ``checklists/`` (previously omitted by the hardcoded list).
* End-to-end strict accept on a software-dev mission missing ``contracts/`` still
  classifies ``contracts`` as BLOCKING (``path_violations``), deduped out of
  ``optional_missing`` -- a severity assertion, not list membership (C-003; severity
  is decided downstream in ``evaluate_path_conventions``, not in
  ``_missing_artifacts``).
* Both fallback triggers -- ``mission is None`` AND an artifacts-less mission stub --
  return the hardcoded fallback with no ``AttributeError``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import specify_cli
from specify_cli.acceptance import (
    _FALLBACK_OPTIONAL_ARTIFACTS,
    _missing_artifacts,
    _optional_artifact_tokens,
    collect_feature_summary,
)
from specify_cli.mission import Mission

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# The packaged software-dev mission whose ``artifacts.optional`` is the SSOT the
# fold reads from. Its declaration includes ``checklists/`` -- the token the old
# hardcoded list dropped.
_SOFTWARE_DEV_MISSION_DIR = Path(specify_cli.__file__).parent / "missions" / "software-dev"

# The full optional-artifact declaration in that mission.yaml (the SSOT the fold
# now honors -- note ``checklists/``, absent from the historical fallback).
_EXPECTED_SOFTWARE_DEV_OPTIONAL = {
    "data-model.md",
    "contracts/",
    "quickstart.md",
    "research.md",
    "checklists/",
}


# ---------------------------------------------------------------------------
# T013: config-driven optional set (now includes checklists/)
# ---------------------------------------------------------------------------


def test_optional_tokens_derived_from_mission_include_checklists() -> None:
    """FR-006: the optional set comes from ``artifacts.optional`` and now carries
    ``checklists/`` -- the token the drifted hardcoded list omitted."""
    mission = Mission(_SOFTWARE_DEV_MISSION_DIR)

    tokens = set(_optional_artifact_tokens(mission))

    assert tokens == _EXPECTED_SOFTWARE_DEV_OPTIONAL
    # Regression pin: the fold's whole point is that ``checklists/`` is now
    # considered, unlike the hardcoded fallback.
    assert "checklists/" in tokens
    assert "checklists/" not in set(_FALLBACK_OPTIONAL_ARTIFACTS)


def test_missing_artifacts_reports_checklists_from_config(tmp_path: Path) -> None:
    """``_missing_artifacts`` flags a mission-declared optional (``checklists/``)
    that is absent on disk -- proof the set is config-driven end to end.

    ``Path`` trailing-slash normalization maps the ``checklists/`` /
    ``contracts/`` tokens to their bare relative strings.
    """
    mission = Mission(_SOFTWARE_DEV_MISSION_DIR)
    feature_dir = tmp_path / "feature"
    feature_dir.mkdir()
    for name in ("spec.md", "plan.md", "tasks.md"):
        (feature_dir / name).write_text("done\n")

    _missing_required, missing_optional = _missing_artifacts(feature_dir, mission)

    assert set(missing_optional) == {
        "data-model.md",
        "contracts",
        "quickstart.md",
        "research.md",
        "checklists",
    }


# ---------------------------------------------------------------------------
# C-003: contracts/ severity (blocking) is unchanged, end-to-end
# ---------------------------------------------------------------------------


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True)


def _software_dev_repo_missing_contracts(tmp_path: Path) -> tuple[Path, str]:
    """A real software-dev-shaped repo whose only defect is a missing
    ``contracts/`` (declared under both ``artifacts.optional`` and
    ``paths.deliverables``)."""
    slug = "099-missing-contracts"
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
    # Deliberately no ``contracts/`` dir anywhere.

    feature_dir = repo_root / "kitty-specs" / slug
    (feature_dir / "tasks").mkdir(parents=True)
    meta = {
        "mission_number": "099",
        "slug": slug,
        "mission_slug": slug,
        "mission_id": "01JZZZZZZZZZZZZZZZZZZZZZZZ",
        "mid8": "01JZZZZZ",
        "friendly_name": "Missing Contracts",
        "mission_type": "software-dev",
        "target_branch": "main",
        "created_at": "2026-01-01T00:00:00Z",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    for fname in ("spec.md", "plan.md", "tasks.md"):
        (feature_dir / fname).write_text(f"# {fname}\nDone.\n")

    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-qm", "init")
    return repo_root, slug


def test_contracts_stays_blocking_after_config_driven_fold(tmp_path: Path) -> None:
    """C-003: a software-dev mission missing ``contracts/`` still classifies it as
    a BLOCKING ``path_violations`` entry, deduped out of ``optional_missing``.

    Severity, not list membership: ``_missing_artifacts`` is severity-blind; the
    downstream ``evaluate_path_conventions`` dedup keeps ``contracts`` on the
    blocking side. This must be byte-identical to the #3783 result even though the
    optional set is now config-driven (and includes ``checklists/``).
    """
    repo_root, slug = _software_dev_repo_missing_contracts(tmp_path)

    summary = collect_feature_summary(repo_root, slug, strict_metadata=True, mutate_matrix=False)

    rendered_violations = "\n".join(summary.path_violations)
    in_optional = "contracts" in summary.optional_missing
    in_violations = "contracts" in rendered_violations

    # Exactly one channel -- the blocking one wins.
    assert in_optional != in_violations, (
        f"optional_missing={summary.optional_missing!r} path_violations={summary.path_violations!r}"
    )
    assert in_violations, "contracts must remain on the blocking path_violations side"
    assert summary.ok is False


# ---------------------------------------------------------------------------
# C-009: fallback guards -- None AND artifacts-less mission (no AttributeError)
# ---------------------------------------------------------------------------


def test_none_mission_falls_back_to_hardcoded_list() -> None:
    """``mission is None`` (``MissionError``) ⇒ the hardcoded fallback."""
    assert _optional_artifact_tokens(None) == list(_FALLBACK_OPTIONAL_ARTIFACTS)


def test_artifacts_less_mission_falls_back_without_attribute_error() -> None:
    """C-009: a mission whose ``config`` has no ``artifacts`` attribute -- the
    #3783 ``SimpleNamespace`` stub -- falls back without raising ``AttributeError``.

    A bare ``mission.config.artifacts.optional`` (or an unguarded
    ``get_optional_artifacts()``) would raise here.
    """
    stub = SimpleNamespace(
        name="Software Dev Kitty",
        config=SimpleNamespace(paths={"workspace": "src", "tests": "tests", "deliverables": "contracts"}),
    )

    # Must not raise, and must return the hardcoded fallback verbatim.
    assert _optional_artifact_tokens(stub) == list(_FALLBACK_OPTIONAL_ARTIFACTS)


def test_missing_artifacts_fallback_matches_for_none_and_artifacts_less(tmp_path: Path) -> None:
    """Both fallback triggers produce identical ``_missing_artifacts`` output on
    the same empty feature dir -- confirming the artifacts-less path degrades to
    exactly the ``None`` behavior."""
    feature_dir = tmp_path / "feature"
    feature_dir.mkdir()
    for name in ("spec.md", "plan.md", "tasks.md"):
        (feature_dir / name).write_text("done\n")

    stub = SimpleNamespace(config=SimpleNamespace(paths={}))

    _req_none, optional_none = _missing_artifacts(feature_dir, None)
    _req_stub, optional_stub = _missing_artifacts(feature_dir, stub)

    assert optional_none == optional_stub
    # The fallback set (no ``checklists/``): quickstart/data-model/research/contracts.
    assert set(optional_none) == {"quickstart.md", "data-model.md", "research.md", "contracts"}

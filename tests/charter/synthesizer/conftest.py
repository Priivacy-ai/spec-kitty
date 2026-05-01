"""Shared pytest fixtures for the charter synthesizer test suite.

Provides:
- minimal_interview_snapshot: small deterministic interview answer dict
- minimal_doctrine_snapshot: small doctrine catalog snapshot
- minimal_drg_snapshot: minimal DRG graph snapshot
- sample_synthesis_target: a SynthesisTarget for a sample directive
- sample_synthesis_request: a complete SynthesisRequest ready for hashing
- fixture_adapter: a FixtureAdapter pointed at tests/charter/fixtures/synthesizer/
- fixture_root: Path to the fixture root directory
"""

from __future__ import annotations

from pathlib import Path

import pytest

from charter.synthesizer.request import SynthesisRequest, SynthesisTarget
from charter.synthesizer.fixture_adapter import FixtureAdapter


# The synthesizer suite is the coverage authority for charter's critical-path
# pipeline. Keep every test in this directory on the fast charter lane so the
# diff-coverage gate sees the real synthesis coverage instead of only the
# legacy non-synth charter tests.
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        item.add_marker(pytest.mark.fast)


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_interview_snapshot() -> dict:
    """Minimal frozen interview answers for deterministic testing."""
    return {
        "mission_type": "software_dev",
        "language_scope": ["python"],
        "testing_philosophy": "test-driven development with high coverage",
        "neutrality_posture": "balanced",
        "selected_directives": ["DIRECTIVE_003"],
        "risk_appetite": "moderate",
    }


@pytest.fixture
def minimal_doctrine_snapshot() -> dict:
    """Minimal shipped doctrine snapshot for deterministic testing."""
    return {
        "directives": {
            "DIRECTIVE_003": {
                "id": "DIRECTIVE_003",
                "title": "Decision Documentation",
                "body": "Document significant architectural decisions via ADRs.",
            }
        },
        "tactics": {},
        "styleguides": {},
    }


@pytest.fixture
def minimal_drg_snapshot() -> dict:
    """Minimal DRG graph snapshot for deterministic testing."""
    return {
        "nodes": [
            {"urn": "directive:DIRECTIVE_003", "kind": "directive", "id": "DIRECTIVE_003"}
        ],
        "edges": [],
        "schema_version": "1",
    }


# ---------------------------------------------------------------------------
# SynthesisTarget and SynthesisRequest
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_synthesis_target() -> SynthesisTarget:
    """A sample SynthesisTarget for a directive."""
    return SynthesisTarget(
        kind="directive",
        slug="project-decision-doc-directive",
        title="Project Decision Documentation Directive",
        artifact_id="PROJECT_001",
        source_section="testing_philosophy",
        source_urns=("directive:DIRECTIVE_003",),
    )


@pytest.fixture
def sample_synthesis_request(
    sample_synthesis_target: SynthesisTarget,
    minimal_interview_snapshot: dict,
    minimal_doctrine_snapshot: dict,
    minimal_drg_snapshot: dict,
) -> SynthesisRequest:
    """A complete SynthesisRequest ready for hashing and adapter calls."""
    return SynthesisRequest(
        target=sample_synthesis_target,
        interview_snapshot=minimal_interview_snapshot,
        doctrine_snapshot=minimal_doctrine_snapshot,
        drg_snapshot=minimal_drg_snapshot,
        run_id="01KPE222CD1MMCYEGB3ZCY51VR",
        adapter_hints={"language": "python"},
    )


# ---------------------------------------------------------------------------
# Fixture adapter
# ---------------------------------------------------------------------------

@pytest.fixture
def fixture_root() -> Path:
    """Path to tests/charter/fixtures/synthesizer/."""
    return Path(__file__).parent.parent / "fixtures" / "synthesizer"


@pytest.fixture
def fixture_adapter(fixture_root: Path) -> FixtureAdapter:
    """FixtureAdapter pointed at the canonical fixture root."""
    return FixtureAdapter(fixture_root=fixture_root)

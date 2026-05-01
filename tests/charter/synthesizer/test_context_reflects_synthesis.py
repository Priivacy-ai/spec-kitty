"""End-to-end synthesis visibility tests for compiler/context consumers.

These tests exercise the real synthesis pipeline rather than writing fake
project doctrine files by hand. That keeps FR-018 / SC-005 honest: the charter
consumers should only see project-local doctrine after a successful synthesis.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from charter._doctrine_paths import resolve_project_root
from charter.compiler import _default_doctrine_service
from charter.context import _build_doctrine_service
from charter.synthesizer import FixtureAdapter, SynthesisRequest, SynthesisTarget, synthesize


@pytest.fixture
def fixture_root() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "synthesizer"


@pytest.fixture
def adapter(fixture_root: Path) -> FixtureAdapter:
    return FixtureAdapter(fixture_root=fixture_root)


@pytest.fixture
def synthesis_request() -> SynthesisRequest:
    interview_snapshot: dict[str, Any] = {
        "mission_type": "software_dev",
        "language_scope": ["python"],
        "testing_philosophy": "test-driven development with high coverage",
        "neutrality_posture": "balanced",
        "selected_directives": ["DIRECTIVE_003"],
        "risk_appetite": "moderate",
    }
    doctrine_snapshot: dict[str, Any] = {
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
    drg_snapshot: dict[str, Any] = {
        "nodes": [{"urn": "directive:DIRECTIVE_003", "kind": "directive", "id": "DIRECTIVE_003"}],
        "edges": [],
        "schema_version": "1",
    }
    return SynthesisRequest(
        target=SynthesisTarget(
            kind="directive",
            slug="mission-type-scope-directive",
            title="Mission Type Scope Directive",
            artifact_id="PROJECT_001",
            source_section="mission_type",
        ),
        interview_snapshot=interview_snapshot,
        doctrine_snapshot=doctrine_snapshot,
        drg_snapshot=drg_snapshot,
        run_id="01KPE222CD1MMCYEGB3ZCY51VR",
        adapter_hints={"language": "python"},
    )


def _project_directive_ids(service: Any) -> set[str]:
    return {directive.id for directive in service.directives.list_all() if directive.id.startswith("PROJECT_")}


def test_no_project_root_before_synthesis(tmp_path: Path) -> None:
    assert resolve_project_root(tmp_path) is None


def test_synthesis_creates_project_doctrine_root(
    tmp_path: Path,
    synthesis_request: SynthesisRequest,
    adapter: FixtureAdapter,
) -> None:
    synthesize(synthesis_request, adapter=adapter, repo_root=tmp_path)
    assert resolve_project_root(tmp_path) == tmp_path / ".kittify" / "doctrine"


def test_compiler_service_reflects_project_directives_after_synthesis(
    tmp_path: Path,
    synthesis_request: SynthesisRequest,
    adapter: FixtureAdapter,
) -> None:
    before_ids = _project_directive_ids(_default_doctrine_service(tmp_path))
    assert before_ids == set()

    synthesize(synthesis_request, adapter=adapter, repo_root=tmp_path)

    after_ids = _project_directive_ids(_default_doctrine_service(tmp_path))
    assert after_ids - before_ids, "Expected synthesis to surface at least one project directive"


def test_context_service_reflects_project_directives_after_synthesis(
    tmp_path: Path,
    synthesis_request: SynthesisRequest,
    adapter: FixtureAdapter,
) -> None:
    before_ids = _project_directive_ids(_build_doctrine_service(tmp_path))
    assert before_ids == set()

    synthesize(synthesis_request, adapter=adapter, repo_root=tmp_path)

    after_ids = _project_directive_ids(_build_doctrine_service(tmp_path))
    assert after_ids - before_ids, "Expected context service to expose project-local doctrine after synthesis"

"""Tests for profile inheritance resolution and matching integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.agent_profiles.profile import TaskContext
from doctrine.agent_profiles.repository import AgentProfileRepository
pytestmark = [pytest.mark.fast, pytest.mark.doctrine]



@pytest.fixture
def inheritance_repo(tmp_path: Path) -> AgentProfileRepository:
    shipped = tmp_path / "shipped"
    shipped.mkdir()

    (shipped / "implementer.agent.yaml").write_text(
        """profile-id: implementer
name: Implementer
purpose: Build missions
routing-priority: 70
specialization:
  primary-focus: implementation
specialization-context:
  languages: [python, javascript]
  frameworks: [django]
  domain-keywords: [api]
collaboration:
  handoff-to: [reviewer]
mode-defaults:
  - mode: analysis
    description: Analyze first
    use-case: plan
initialization-declaration: hello
""",
        encoding="utf-8",
    )

    (shipped / "python-pedro.agent.yaml").write_text(
        """profile-id: python-pedro
name: Python Pedro
purpose: Python specialist
specializes-from: implementer
specialization:
  primary-focus: python implementation
specialization-context:
  languages: [python]
mode-defaults:
  - mode: creative
    description: explore
    use-case: spike
""",
        encoding="utf-8",
    )

    (shipped / "backend-pedro.agent.yaml").write_text(
        """profile-id: backend-pedro
name: Backend Pedro
purpose: Backend specialist
specializes-from: python-pedro
specialization:
  primary-focus: backend apis
""",
        encoding="utf-8",
    )

    return AgentProfileRepository(shipped_dir=shipped, project_dir=None)


def test_resolve_profile_inherits_missing_fields(inheritance_repo: AgentProfileRepository) -> None:
    resolved = inheritance_repo.resolve_profile("python-pedro")

    assert resolved.collaboration.handoff_to == ["reviewer"]
    assert resolved.specialization_context is not None
    assert resolved.specialization_context.languages == ["python"]
    assert resolved.specialization_context.frameworks == ["django"]


def test_resolve_profile_supports_multi_level_chain(inheritance_repo: AgentProfileRepository) -> None:
    resolved = inheritance_repo.resolve_profile("backend-pedro")

    assert resolved.specialization.primary_focus == "backend apis"
    assert resolved.specialization_context is not None
    assert resolved.specialization_context.languages == ["python"]
    assert resolved.specialization_context.frameworks == ["django"]


def test_resolve_profile_missing_parent_raises_key_error(tmp_path: Path) -> None:
    shipped = tmp_path / "shipped"
    shipped.mkdir()
    (shipped / "orphan.agent.yaml").write_text(
        """profile-id: orphan
name: Orphan
purpose: orphan
specializes-from: missing-parent
specialization:
  primary-focus: orphan
""",
        encoding="utf-8",
    )

    repo = AgentProfileRepository(shipped_dir=shipped, project_dir=None)

    with pytest.raises(KeyError, match="missing-parent"):
        repo.resolve_profile("orphan")


def test_resolve_profile_cycle_raises(tmp_path: Path) -> None:
    shipped = tmp_path / "shipped"
    shipped.mkdir()
    (shipped / "a.agent.yaml").write_text(
        """profile-id: a
name: A
purpose: a
specializes-from: b
specialization:
  primary-focus: a
""",
        encoding="utf-8",
    )
    (shipped / "b.agent.yaml").write_text(
        """profile-id: b
name: B
purpose: b
specializes-from: a
specialization:
  primary-focus: b
""",
        encoding="utf-8",
    )

    repo = AgentProfileRepository(shipped_dir=shipped, project_dir=None)

    with pytest.raises(ValueError, match="Cycle detected"):
        repo.resolve_profile("a")


def test_matching_uses_resolved_profile_context(inheritance_repo: AgentProfileRepository) -> None:
    context = TaskContext(language="python", framework="django", complexity="high")
    best = inheritance_repo.find_best_match(context)

    assert best is not None
    # backend-pedro inherits django framework through the chain and has the most specific focus.
    assert best.profile_id in {"python-pedro", "backend-pedro"}


# ── US-6 acceptance tests ─────────────────────────────────────────────────────


@pytest.fixture
def us6_repo(tmp_path: Path) -> AgentProfileRepository:
    """Fixture for US-6 inheritance and excluding scenarios."""
    shipped = tmp_path / "shipped"
    shipped.mkdir()

    (shipped / "base.agent.yaml").write_text(
        """profile-id: base
name: Base
purpose: Base profile
routing-priority: 50
specialization:
  primary-focus: general
directive-references:
  - code: "D010"
    name: Directive D010
    rationale: first base directive
  - code: "D020"
    name: Directive D020
    rationale: second base directive
capabilities:
  - base-cap-1
  - base-cap-2
mode-defaults:
  - mode: analysis
    description: Analyze
    use-case: plan
initialization-declaration: hello
""",
        encoding="utf-8",
    )

    (shipped / "child.agent.yaml").write_text(
        """profile-id: child
name: Child
purpose: Child profile
specializes-from: base
specialization:
  primary-focus: child focus
directive-references:
  - code: "D030"
    name: Directive D030
    rationale: child directive
capabilities:
  - child-cap-1
mode-defaults:
  - mode: creative
    description: Explore
    use-case: spike
""",
        encoding="utf-8",
    )

    (shipped / "grandchild.agent.yaml").write_text(
        """profile-id: grandchild
name: Grandchild
purpose: Grandchild profile
specializes-from: child
specialization:
  primary-focus: grandchild focus
""",
        encoding="utf-8",
    )

    (shipped / "child-excluding.agent.yaml").write_text(
        """profile-id: child-excluding
name: Child Excluding
purpose: Child that excludes a directive value
specializes-from: base
specialization:
  primary-focus: excluding focus
directive-references:
  - code: "D030"
    name: Directive D030
    rationale: child directive
excluding:
  directive-references:
    - "D010"
""",
        encoding="utf-8",
    )

    return AgentProfileRepository(shipped_dir=shipped, project_dir=None)


def test_unspecified_fields_inherited(us6_repo: AgentProfileRepository) -> None:
    """US-6 S1: child with specializes-from=base, unspecified fields come from parent."""
    resolved = us6_repo.resolve_profile("child")

    # initialization-declaration not set on child → inherited from base
    assert resolved.initialization_declaration == "hello"
    # routing-priority not set on child → inherited from base
    assert resolved.routing_priority == 50


def test_child_overrides_scalar_field(us6_repo: AgentProfileRepository) -> None:
    """US-6 S2: child's primary_focus overrides parent's."""
    resolved = us6_repo.resolve_profile("child")

    assert resolved.specialization.primary_focus == "child focus"


def test_list_fields_merged_by_union(us6_repo: AgentProfileRepository) -> None:
    """US-6 S3: child adding one directive → resolved has parent + child directives, no duplicates."""
    resolved = us6_repo.resolve_profile("child")

    directive_codes = [ref.code for ref in resolved.directive_references]
    # Parent has D010 and D020; child adds D030 → all three present
    assert "D010" in directive_codes
    assert "D020" in directive_codes
    assert "D030" in directive_codes
    assert len(directive_codes) == 3

    cap_names = resolved.capabilities
    # Parent has base-cap-1, base-cap-2; child adds child-cap-1 → all three present
    assert "base-cap-1" in cap_names
    assert "base-cap-2" in cap_names
    assert "child-cap-1" in cap_names
    assert len(cap_names) == 3


def test_excluding_value_removed(us6_repo: AgentProfileRepository) -> None:
    """US-6 S4: excluding: {directive-references: [D010]} → D010 omitted from merged directives."""
    resolved = us6_repo.resolve_profile("child-excluding")

    directive_codes = [ref.code for ref in resolved.directive_references]
    # D020 from parent still present; D010 excluded; D030 from child
    assert "D010" not in directive_codes
    assert "D020" in directive_codes
    assert "D030" in directive_codes


def test_multi_level_chain(us6_repo: AgentProfileRepository) -> None:
    """US-6 S5: grandchild → child → base; inheritance cascades correctly."""
    resolved = us6_repo.resolve_profile("grandchild")

    # grandchild overrides primary_focus
    assert resolved.specialization.primary_focus == "grandchild focus"
    # initialization-declaration comes from base (2 levels up)
    assert resolved.initialization_declaration == "hello"
    # directive-references merged across all 3 levels (base + child → grandchild inherits)
    directive_codes = [ref.code for ref in resolved.directive_references]
    assert "D010" in directive_codes
    assert "D020" in directive_codes
    assert "D030" in directive_codes


def test_missing_parent_raises_key_error(tmp_path: Path) -> None:
    """US-6 S6: profile with specializes-from=nonexistent → KeyError with clear message."""
    shipped = tmp_path / "shipped"
    shipped.mkdir()
    (shipped / "orphan.agent.yaml").write_text(
        """profile-id: orphan
name: Orphan
purpose: orphan
specializes-from: nonexistent-parent
specialization:
  primary-focus: orphan
""",
        encoding="utf-8",
    )

    repo = AgentProfileRepository(shipped_dir=shipped, project_dir=None)

    with pytest.raises(KeyError, match="nonexistent-parent"):
        repo.resolve_profile("orphan")

"""Integration: a real mission of each type resolves domain-appropriate
governance with ZERO software-dev doctrine (contract C5 / WP12).

Where ``tests/doctrine/test_mission_type_governance_isolation.py`` asserts the
isolation invariant on the resolver in isolation, this test stages a **real
mission on disk** — a ``kitty-specs/<slug>/meta.json`` declaring the mission
type — and drives the resolution through the same ``meta.json`` read path a live
mission uses (``resolve_mission_type_context(repo_root, feature_dir=...)``). It
pins three acceptance criteria end-to-end:

* **SC-001** — a documentation / research / plan mission resolves its
  domain-appropriate governance and gates with **zero** software-dev doctrine.
* **SC-002** — a mission whose ``meta.json`` declares an unknown type surfaces a
  clear, remediable error (never a silent software-dev fallback).
* **SC-004** — each type's resolved *(type ⊕ action)* set is a **superset** of
  the domain's authored + referenced governance ids, making "covers the domain"
  a checkable positive assertion rather than a vibe.

WP03 wired the live action-grain union into ``bundle.governance`` itself
(lazily, via :func:`charter.action_grain.aggregate_action_grain` — covering
EVERY action the mission type ships). WP05 reconciled
``_resolve_union_from_mission`` onto that single source (C-002 / FR-006): it
used to independently re-union ``load_action_index`` over the type's own
actions after already reading ``bundle.governance`` — a second, competing
implementation of the same union. That loop is deleted; the helper now reads
``bundle.governance`` directly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from charter.mission_type_profiles import (
    ResolvedGovernance,
    UnknownMissionTypeError,
    resolve_mission_type_context,
)
from charter.resolution import ResolutionTier
from specify_cli.runtime.resolver import (
    TemplateConfigurationError,
    resolve_configured_template,
)

pytestmark = [pytest.mark.integration]


_KIND_SINGULAR: dict[str, str] = {
    "directives": "directive",
    "tactics": "tactic",
    "paradigms": "paradigm",
    "styleguides": "styleguide",
    "toolguides": "toolguide",
    "procedures": "procedure",
    "agent_profiles": "agent_profile",
}

#: Same software-dev-only denylist as the doctrine isolation test — the TDD /
#: git-flow / refactoring doctrine homed in software-dev/actions/implement.
SOFTWARE_DEV_ONLY_DENYLIST: frozenset[str] = frozenset(
    {
        "paradigm:git-flow",
        "paradigm:trunk-based",
        "paradigm:shared-branch-ci",
        "directive:034-test-first-development",
        "tactic:tdd-red-green-refactor",
        "tactic:acceptance-test-first",
        "procedure:refactoring",
        "procedure:test-first-bug-fixing",
    }
)

#: Per-type positive-membership expectation (SC-004): the authored + referenced
#: governance ids that a mission of this type MUST resolve. These are the
#: domain-defining artifacts from each shipped ``governance-profile.yaml`` — a
#: subset chosen to be unambiguous and stable, not the exhaustive set.
EXPECTED_DOMAIN_MEMBERSHIP: dict[str, frozenset[str]] = {
    "documentation": frozenset(
        {
            "directive:042-common-docs",
            "styleguide:divio-type-discipline",
            "styleguide:plain-language",
            "styleguide:docs-accessibility",
            "styleguide:publication-authority",
            "styleguide:docs-freshness-sla",
        }
    ),
    "research": frozenset(
        {
            "styleguide:research-citation-discipline",
            "procedure:spike-timebox-policy",
            "tactic:dialectic-research",
        }
    ),
    "plan": frozenset(
        {
            "directive:031-context-aware-design",
            "styleguide:planning-and-tracking",
            "paradigm:domain-driven-design",
        }
    ),
}

_DOMAIN_TYPES: tuple[str, ...] = ("documentation", "research", "plan")


def _canonical_urn(kind_plural: str, raw: str) -> str:
    text = raw.strip().lower()
    if text.startswith("urn:"):
        segments = text.split(":")
        return f"{segments[1]}:{segments[-1]}"
    return f"{_KIND_SINGULAR[kind_plural]}:{text}"


def _governance_urns(governance: ResolvedGovernance | None) -> set[str]:
    if governance is None:
        return set()
    urns: set[str] = set()
    for kind_plural in _KIND_SINGULAR:
        for raw in getattr(governance, f"selected_{kind_plural}"):
            urns.add(_canonical_urn(kind_plural, raw))
    return urns


def _stage_mission(repo_root: Path, mission_type: str) -> Path:
    """Stage a real ``kitty-specs/<slug>/meta.json`` declaring ``mission_type``.

    Returns the mission ``feature_dir`` — the source of truth the resolver reads
    the mission type from. No project-level ``selected_*`` overrides are written,
    so the shipped mission-type governance profile is the sole authority.
    """
    mission_slug = f"777-{mission_type}-resolution-integration"
    feature_dir = repo_root / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    feature_dir.joinpath("meta.json").write_text(
        json.dumps({"mission_type": mission_type, "mission_slug": mission_slug}),
        encoding="utf-8",
    )
    return feature_dir


def _resolve_union_from_mission(repo_root: Path, feature_dir: Path, mission_type: str) -> set[str]:
    """Resolve the *(type ⊕ action)* URN set via the live meta.json path.

    Reads ``bundle.governance`` directly — post-WP03 it already carries the
    FR-013 union of the type grain with the FULL action grain (every action
    the mission type ships). No independent ``load_action_index`` re-union is
    performed here (C-002 / FR-006).
    """
    bundle = resolve_mission_type_context(repo_root, feature_dir=feature_dir)
    assert bundle.mission_type == mission_type
    return _governance_urns(bundle.governance)


# ---------------------------------------------------------------------------
# SC-001 — zero software-dev doctrine for a real domain mission
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mission_type", _DOMAIN_TYPES)
def test_domain_mission_resolves_zero_software_dev_doctrine(mission_type: str, tmp_path: Path) -> None:
    feature_dir = _stage_mission(tmp_path, mission_type)
    union = _resolve_union_from_mission(tmp_path, feature_dir, mission_type)

    leaked = union & SOFTWARE_DEV_ONLY_DENYLIST
    assert not leaked, f"SC-001: a real {mission_type} mission (meta.json → resolver) resolved software-dev-only doctrine {sorted(leaked)}."
    bundle = resolve_mission_type_context(tmp_path, feature_dir=feature_dir)
    assert "software-dev-default" not in bundle.governance_text.lower()
    assert bundle.template_set is None


# ---------------------------------------------------------------------------
# SC-004 — resolved set covers the domain's authored + referenced ids
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mission_type", _DOMAIN_TYPES)
def test_domain_mission_covers_expected_membership(mission_type: str, tmp_path: Path) -> None:
    feature_dir = _stage_mission(tmp_path, mission_type)
    union = _resolve_union_from_mission(tmp_path, feature_dir, mission_type)

    expected = EXPECTED_DOMAIN_MEMBERSHIP[mission_type]
    missing = expected - union
    assert not missing, (
        f"SC-004: a {mission_type} mission failed to resolve its expected "
        f"domain governance {sorted(missing)}. The type is not covering the "
        "domain it was authored for."
    )


# ---------------------------------------------------------------------------
# SC-002 — unknown type surfaces a clear error, never software-dev
# ---------------------------------------------------------------------------


def test_unknown_type_mission_raises_clear_error(tmp_path: Path) -> None:
    misleading_template = tmp_path / ".kittify" / "overrides" / "templates" / "spec-template.md"
    misleading_template.parent.mkdir(parents=True)
    misleading_template.write_text("# Must not activate an unknown type\n", encoding="utf-8")
    feature_dir = _stage_mission(tmp_path, "quantum-astrology")
    with pytest.raises(UnknownMissionTypeError) as exc:
        resolve_mission_type_context(tmp_path, feature_dir=feature_dir)
    # The error names the offending type so an operator can fix the meta.json.
    assert "quantum-astrology" in str(exc.value)


# ---------------------------------------------------------------------------
# Templates-as-configuration — live activated context to content consumer
# ---------------------------------------------------------------------------


def test_software_development_mission_resolves_exact_configured_templates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Own every tier this assertion constrains. Earlier e2e tests intentionally
    # materialize a user-global software-development template home, so relying
    # on the session's shared home makes PACKAGE_DEFAULT order-dependent.
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "empty-global-home"))
    feature_dir = _stage_mission(tmp_path, "software-dev")
    bundle = resolve_mission_type_context(tmp_path, feature_dir=feature_dir)

    assert bundle.template_set == {
        "spec": "spec-template.md",
        "plan": "plan-template.md",
    }
    for artifact_kind, expected_filename in bundle.template_set.items():
        result = resolve_configured_template(artifact_kind, tmp_path, bundle)
        assert result.path.name == expected_filename
        assert result.tier is ResolutionTier.PACKAGE_DEFAULT
        assert result.mission == "software-dev"
        assert result.path.read_bytes()


@pytest.mark.parametrize("mission_type", _DOMAIN_TYPES)
def test_null_template_mapping_fails_closed_with_stable_diagnostics(
    mission_type: str,
    tmp_path: Path,
) -> None:
    feature_dir = _stage_mission(tmp_path, mission_type)
    bundle = resolve_mission_type_context(tmp_path, feature_dir=feature_dir)

    with pytest.raises(TemplateConfigurationError) as exc_info:
        resolve_configured_template("spec", tmp_path, bundle)

    error = exc_info.value
    assert error.mission_type == mission_type
    assert error.artifact_kind == "spec"
    assert error.mapped_filename is None
    assert "has no configured template mapping" in str(error)

"""Tests for ``resolve_generic_fallback`` — the WP02/#3064 empty-charter routing seam.

The composite predicate (Decision 3, research.md) requires ALL charter-activatable
dimensions to be empty before the executor pins ``generic-agent``:

- ``charter_activated_urns(repo_root) == set()`` (the 6 URN kinds: directives,
  tactics, toolguides, procedures, paradigms, styleguides)
- ``PackContext.activated_agent_profiles is None``
- ``PackContext.activated_mission_step_contracts is None``
- ``PackContext.activated_glossary_packs is None``
- ``PackContext.org_roots == ()``

A narrower predicate would false-fallback on a repo that activated only a
glossary pack, a step contract, or an org pack — exactly the defect the
post-plan squad caught (research.md Decision 3). Every row of the truth table
below MUST be covered.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from specify_cli.invocation.empty_charter import GENERIC_AGENT_ID, resolve_generic_fallback
from specify_cli.invocation.router import RouterDecision

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _write_config(repo_root: Path, data: dict[str, object]) -> None:
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    with (kittify / "config.yaml").open("w", encoding="utf-8") as fh:
        YAML().dump(data, fh)


# ---------------------------------------------------------------------------
# Truth table — fallback fires
# ---------------------------------------------------------------------------


def test_no_config_at_all_returns_fallback_decision(tmp_path: Path) -> None:
    """No ``.kittify/config.yaml`` at all is the maximally-empty case."""
    decision = resolve_generic_fallback(tmp_path, "implement the payment module")

    assert decision is not None
    assert isinstance(decision, RouterDecision)
    assert decision.profile_id == GENERIC_AGENT_ID == "generic-agent"
    assert decision.confidence == "generic_fallback"
    assert decision.action == "implement"


def test_empty_config_file_returns_fallback_decision(tmp_path: Path) -> None:
    """An explicit-but-empty config.yaml (no activation keys at all) is empty."""
    _write_config(tmp_path, {})

    decision = resolve_generic_fallback(tmp_path, "review the diff")

    assert decision is not None
    assert decision.profile_id == GENERIC_AGENT_ID
    assert decision.confidence == "generic_fallback"
    assert decision.action == "review"


def test_action_falls_back_to_implementer_default_when_no_verb_matches(tmp_path: Path) -> None:
    """No canonical-verb token present -> derive from the IMPLEMENTER role default."""
    decision = resolve_generic_fallback(tmp_path, "please help me with this")

    assert decision is not None
    # DEFAULT_ROLE_CAPABILITIES[Role.IMPLEMENTER].canonical_verbs[0] == "generate"
    assert decision.action == "generate"


# ---------------------------------------------------------------------------
# Truth table — fallback does NOT fire (composite predicate dimensions)
# ---------------------------------------------------------------------------


def test_urn_kind_activated_returns_none(tmp_path: Path) -> None:
    """A single activated directive (one of the 6 URN kinds) is a configured repo."""
    _write_config(tmp_path, {"activated_directives": ["028-efficient-local-tooling"]})

    assert resolve_generic_fallback(tmp_path, "implement the feature") is None


def test_agent_profiles_activated_with_entries_returns_none(tmp_path: Path) -> None:
    _write_config(tmp_path, {"activated_agent_profiles": ["architect-alphonso"]})

    assert resolve_generic_fallback(tmp_path, "implement the feature") is None


def test_agent_profiles_activated_with_empty_list_returns_none(tmp_path: Path) -> None:
    """Three-state semantics: an explicit empty list is still 'key present' (not empty-charter)."""
    _write_config(tmp_path, {"activated_agent_profiles": []})

    assert resolve_generic_fallback(tmp_path, "implement the feature") is None


def test_glossary_packs_activated_returns_none(tmp_path: Path) -> None:
    _write_config(tmp_path, {"activated_glossary_packs": ["core-glossary"]})

    assert resolve_generic_fallback(tmp_path, "implement the feature") is None


def test_glossary_packs_activated_with_empty_list_returns_none(tmp_path: Path) -> None:
    _write_config(tmp_path, {"activated_glossary_packs": []})

    assert resolve_generic_fallback(tmp_path, "implement the feature") is None


def test_mission_step_contracts_activated_returns_none(tmp_path: Path) -> None:
    _write_config(tmp_path, {"activated_mission_step_contracts": ["software-dev-implement"]})

    assert resolve_generic_fallback(tmp_path, "implement the feature") is None


def test_mission_step_contracts_activated_with_empty_list_returns_none(tmp_path: Path) -> None:
    _write_config(tmp_path, {"activated_mission_step_contracts": []})

    assert resolve_generic_fallback(tmp_path, "implement the feature") is None


def test_org_pack_present_returns_none(tmp_path: Path) -> None:
    """An org/project pack registered in config.yaml is a configured repo, even
    with zero activation keys set — org_roots != () alone must block the fallback.
    """
    pack_root = tmp_path / "org-packs" / "orgzilla-governance-pack"
    pack_root.mkdir(parents=True)
    _write_config(
        tmp_path,
        {"doctrine": {"org": {"packs": [{"name": "orgzilla-governance-pack", "local_path": str(pack_root)}]}}},
    )

    assert resolve_generic_fallback(tmp_path, "implement the feature") is None

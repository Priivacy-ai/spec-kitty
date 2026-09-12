"""Every built-in ``operating-procedures`` entry must resolve to a procedure node.

Empty-set architectural gate (WP09 ``test_no_authored_applies_edge`` archetype):
the set of built-in ``collaboration.operating-procedures`` entries that do NOT
resolve to a real ``procedure:`` DRG node must be empty. A fictional entry (names
no node) or a wrong-kind entry (names, e.g., a tactic) fails this gate loudly,
instead of loading clean and reaching no consumer.

The gate is non-vacuous: it self-mutates a profile to add a fictional entry and
asserts the resolver reports it, so an accidentally-empty input universe cannot
make the gate pass by construction.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from charter.offering.agent_profiles.operating_procedures import (
    collect_operating_procedure_entries,
    node_universe,
    resolve_operating_procedure_entries,
)
from charter.offering.drg.loader import load_built_in_graph

pytestmark = pytest.mark.architectural

_BUILT_IN = Path(__file__).resolve().parents[2] / "packs" / "built-in"
_PROFILES_DIR = _BUILT_IN / "agent_profiles"


def _built_in_operating_procedures() -> dict[str, list[str]]:
    """Map ``profile_id -> operating-procedures`` for every built-in profile."""
    return collect_operating_procedure_entries(_PROFILES_DIR)


def test_built_in_operating_procedures_all_resolve_to_a_procedure_node() -> None:
    procedure_urns, urns_by_kind = node_universe(load_built_in_graph().nodes)
    entries = _built_in_operating_procedures()

    unresolved = resolve_operating_procedure_entries(entries, procedure_urns, urns_by_kind)

    assert unresolved == [], "operating-procedures entries that do not resolve to a real procedure node:\n" + "\n".join(
        f"  {u.profile_id}: {u.entry} ({u.reason}" + (f" -> {u.resolved_kind}" if u.resolved_kind else "") + ")" for u in unresolved
    )


def test_gate_is_non_vacuous_fictional_entry_is_reported() -> None:
    """Injecting a fictional entry must be reported (self-mutation check)."""
    procedure_urns, urns_by_kind = node_universe(load_built_in_graph().nodes)

    injected = resolve_operating_procedure_entries(
        {"synthetic-profile": ["this-procedure-does-not-exist"]},
        procedure_urns,
        urns_by_kind,
    )

    assert len(injected) == 1
    assert injected[0].profile_id == "synthetic-profile"
    assert injected[0].entry == "this-procedure-does-not-exist"
    assert injected[0].reason == "no_node"


def test_wrong_kind_entry_is_reported_as_wrong_kind() -> None:
    """A real tactic id in operating-procedures resolves as wrong_kind, not valid."""
    procedure_urns, urns_by_kind = node_universe(load_built_in_graph().nodes)

    result = resolve_operating_procedure_entries(
        {"synthetic-profile": ["tdd-red-green-refactor"]},
        procedure_urns,
        urns_by_kind,
    )

    assert len(result) == 1
    assert result[0].reason == "wrong_kind"
    assert result[0].resolved_kind == "tactic"

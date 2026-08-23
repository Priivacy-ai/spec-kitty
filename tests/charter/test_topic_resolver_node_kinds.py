"""Behaviour drift-guard for the DRG node-kind membership gate (WP01 / #3608).

``topic_resolver._DRG_NODE_KINDS`` must be *derived* from the canonical
``NodeKind`` enum, not a hand-maintained literal. A literal drifts silently and
drops legitimate DRG-URN selectors at the membership gate
(``topic_resolver.py`` ``_resolve_drg_urn``).

These tests pin the boundary two ways:

* **Behaviour pin (T002).** Extend ``NodeKind`` with a synthetic member, reload
  the resolver, and assert a URN carrying the new value is recognized at the
  gate. This fails if the derivation is ever reverted to a literal — a literal
  cannot know about a member declared after it was written. It is deliberately
  *not* a ``_DRG_NODE_KINDS == {k.value for k in NodeKind}`` tautology.
* **Dropped-kinds gate (T003).** Every ``NodeKind`` value — including the six
  that the old hand-copy dropped (``anti_pattern``, ``asset``, ``glossary``,
  ``glossary_pack``, ``mission_step_contract``, ``template``) — resolves at the
  gate. Parametrized over the live enum so new members are covered for free.
"""

from __future__ import annotations

import enum
import importlib

import pytest

from charter.synthesizer import topic_resolver
from doctrine.drg.models import NodeKind

#: The six kinds the retired hand-literal in ``topic_resolver`` dropped.
_PREVIOUSLY_DROPPED: tuple[str, ...] = (
    "anti_pattern",
    "asset",
    "glossary",
    "glossary_pack",
    "mission_step_contract",
    "template",
)


def _drg_with(urn: str) -> dict[str, list[dict[str, str]]]:
    """A minimal merged-DRG payload containing exactly one node ``urn``."""
    return {"nodes": [{"urn": urn}]}


def _make_extended_nodekind(
    base: type[enum.StrEnum], synthetic_value: str
) -> type[enum.StrEnum]:
    """Return a StrEnum mirroring ``base`` plus one synthetic member."""
    members = {member.name: member.value for member in base}
    members["SYNTHETIC_KIND"] = synthetic_value
    return enum.StrEnum("NodeKind", members)


def test_synthetic_nodekind_member_is_recognized_at_gate() -> None:
    """Behaviour pin: a NodeKind member added after import resolves at the gate.

    Reverting ``_DRG_NODE_KINDS`` to a hand literal makes this fail — a literal
    cannot contain a member that did not exist when it was written.
    """
    models_mod = importlib.import_module("doctrine.drg.models")
    real = models_mod.NodeKind
    fake = _make_extended_nodekind(real, "synthetic_kind")
    urn = "synthetic_kind:demo"
    try:
        models_mod.NodeKind = fake
        importlib.reload(topic_resolver)
        result = topic_resolver._resolve_drg_urn(urn, _drg_with(urn), [])
        # not None => the kind passed the membership gate; None would mean the
        # gate rejected it (the revert-to-literal regression).
        assert result is not None, (
            "resolver rejected a freshly-declared NodeKind member; "
            "_DRG_NODE_KINDS is not derived from NodeKind"
        )
        assert "synthetic_kind" in topic_resolver._DRG_NODE_KINDS
    finally:
        models_mod.NodeKind = real
        importlib.reload(topic_resolver)


@pytest.mark.parametrize("kind_value", [k.value for k in NodeKind])
def test_every_nodekind_value_resolves_at_gate(kind_value: str) -> None:
    """Every canonical NodeKind value passes the membership gate."""
    urn = f"{kind_value}:demo-id"
    result = topic_resolver._resolve_drg_urn(urn, _drg_with(urn), [])
    assert result is not None, f"{kind_value!r} rejected at the DRG membership gate"


@pytest.mark.parametrize("kind_value", _PREVIOUSLY_DROPPED)
def test_previously_dropped_kind_resolves_at_gate(kind_value: str) -> None:
    """The six kinds the old hand-copy dropped now resolve (red-first: glossary_pack)."""
    urn = f"{kind_value}:demo-id"
    result = topic_resolver._resolve_drg_urn(urn, _drg_with(urn), [])
    # Kind recognized at the gate and URN present in the DRG, but no
    # project-local artifact references it -> empty match list, not None.
    assert result == []


def test_resolver_set_matches_merge_twin() -> None:
    """Cross-module SSOT pin: both derivations of the kind set agree."""
    merge_mod = importlib.import_module("doctrine.drg.merge")
    assert topic_resolver._DRG_NODE_KINDS == merge_mod._NODE_KIND_PREFIXES

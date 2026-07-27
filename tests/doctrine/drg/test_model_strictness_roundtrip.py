"""Strict DRG/profile models + field-derived writers (WP04, FR-004 / C-001 / SC-003).

Two silences, and they only close together
------------------------------------------
A field can go missing at either end of the same trip, and closing one end alone
ships a worse bug than leaving both open:

**Read end.** ``DRGNode``, ``DRGEdge`` and ``AgentProfile`` declared no
``extra`` policy, so Pydantic v2's ``extra="ignore"`` default applied: an
authored key the model does not declare was dropped on load with no warning.
Every sibling model under ``src/doctrine/**/models.py`` already declares
``extra="forbid"`` (``tactics``, ``directives``, ``procedures``, ``paradigms``,
``missions``, ``styleguides``, ``toolguides``, ``assets``, ``glossary_packs``,
``model_task_routing``, ``import_candidates``) and ``ContextSources`` does too —
``drg/models.py`` and ``AgentProfile`` were the outliers, not the innovation.

**Write end.** The extractor's ``_node_to_dict`` / ``_edge_to_dict`` restated
their model's field names by hand. A field added to the model but not to the
writer loads fine, is reachable in memory, and is deleted the next time the
graph is written.

C-009 requires the model change and the writer change in one commit for exactly
that reason. Landing ``extra="forbid"`` alone would make an authored ``impacts``
key *load* — and still vanish on the next regeneration, now with a passing model
test to vouch for it. That is a strictly worse failure than today's, because it
buys a green assertion.

What the round-trip test actually proves
----------------------------------------
"A new field survives write→read" is only meaningful if the new field is *new*.
Asserting on ``when`` or ``reason`` proves nothing: a hand-written writer that
names them passes. So this module attacks it from both sides:

1. :func:`test_every_declared_edge_field_is_emitted_unless_explicitly_withheld`
   pins the *real* ``DRGEdge``: the emitted key set must equal
   ``model_fields`` minus a named withholding set. That is total over the model,
   so a field added tomorrow must either be emitted or be explicitly withheld —
   there is no third outcome where it is quietly absent.
2. :class:`_DRGEdgeWithNewField` adds a genuinely undeclared-today field and
   drives it through ``_edge_to_dict`` → YAML → re-validate. This is the
   behavioural half; it fails against a writer that restates field names, which
   :func:`test_the_hand_written_writer_shape_would_drop_the_new_field` proves by
   running the replaced writer shape against the same edge (T022 — the
   round-trip must not be green for free).

The withholding set is not an escape hatch
------------------------------------------
``provenance`` is deliberately not serialised: it is a merge-time marker
(FR-013) that is ``None`` for every extractor-built node, and emitting it would
churn the shipped graph. That exclusion is a *declaration*, not a silence — it
lives in one named frozenset, every member is asserted to be a real model field
(so it cannot rot into a typo that silently withholds nothing), and the
withholding itself is asserted rather than assumed.

Why ``_KIND_MAP`` is here and not in WP03
-----------------------------------------
``_KIND_MAP`` mapped 11 of ``NodeKind``'s 16 members, dropping ``anti_pattern``,
``asset``, ``glossary``, ``glossary_pack`` and ``glossary_scope``. It is
``str``-keyed, which is why the ``NodeKind``-keyed totality guard in
``test_kind_mapping_totality.py`` could not see it — a hand-restated table one
step outside the gate that exists to catch hand-restated tables. Closing it by
*deriving* the table from ``NodeKind`` removes the restatement rather than
lengthening it.

Measured graph-neutral on this branch: regenerating with the total map moves the
extractor graph by zero nodes and zero edges (305/757 before and after; the
shipped 311/774 adds the hand-authored ``anti_pattern`` fragment the extractor
does not produce). The gap is latent, not live — it goes live when mission C
authors anti-patterns and assets that other artefacts *reference*. The shipped
311/774 invariant is pinned once, by WP03's
``test_unknown_kind_fails_loudly.py``; it is deliberately not restated here.

Why extractor symbols are reached through the module
----------------------------------------------------
``from ... extractor import _KIND_MAP, ...`` would make this module fail to
*import* on the planning base, and a collection error is a poor ATDD red: it
says "one of these names is missing" and nothing about which behaviours are
broken. Reaching them as ``extractor.<name>`` keeps the module importable, so
the red-first commit produces a per-test failure map that names each defect
separately.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError
from ruamel.yaml import YAML

from doctrine.agent_profiles.profile import AgentProfile
from doctrine.drg.migration import extractor
from doctrine.drg.models import DRGEdge, DRGNode, NodeKind, Relation

pytestmark = [pytest.mark.doctrine, pytest.mark.fast]

_SRC_DOCTRINE = Path(__file__).resolve().parents[3] / "src" / "doctrine"

#: Floors for the shipped-tree scans below. Every assertion that walks the tree
#: is satisfied by an empty walk, so relocating ``src/doctrine`` or renaming the
#: fragment/profile conventions would leave those tests green while covering
#: nothing. Counts as measured on this branch: 14 fragments, 18 profiles.
_MINIMUM_SHIPPED_FRAGMENTS = 14
_MINIMUM_SHIPPED_PROFILES = 18

_VALID_NODE: dict[str, Any] = {"urn": "tactic:some-tactic", "kind": "tactic"}
_VALID_EDGE: dict[str, Any] = {
    "source": "tactic:some-tactic",
    "target": "directive:DIRECTIVE_001",
    "relation": "requires",
}
_VALID_PROFILE: dict[str, Any] = {
    "profile-id": "test-profile",
    "name": "Test Profile",
    "purpose": "Exercise the model.",
    "specialization": {"primary-focus": "Testing"},
    "roles": ["implementer"],
}

#: A field name no model declares today — the probe for "undeclared key".
_UNDECLARED_KEY = "a_key_no_model_declares"


class _DRGEdgeWithNewField(DRGEdge):
    """``DRGEdge`` plus one field — B1's ``impacts`` / ``is_symmetric`` in miniature.

    Declaring the extra field on a subclass rather than mutating the shipped
    model keeps this test from having to edit production code to run, and it
    exercises precisely the mechanism under test: a writer that reads
    ``type(model).model_fields`` picks the field up, and a writer that restates
    names does not. The complementary half — that the *real* ``DRGEdge``'s
    emitted keys are derived from its own ``model_fields`` — is asserted
    separately, so neither test stands alone.
    """

    audit_note: str | None = None


def _hand_written_edge_dict(edge: DRGEdge) -> dict[str, Any]:
    """The writer shape WP04 replaces, restated verbatim as the self-mutation foil.

    Kept here rather than in the extractor so the round-trip assertion has
    something to fail against. If this and ``_edge_to_dict`` ever agree on an
    edge carrying an undeclared-today field, the round-trip test has gone
    vacuous.
    """
    out: dict[str, Any] = {
        "source": edge.source,
        "target": edge.target,
        "relation": edge.relation.value,
    }
    if edge.when is not None:
        out["when"] = edge.when.strip()
    if edge.reason is not None:
        out["reason"] = edge.reason.strip()
    return out


# ---------------------------------------------------------------------------
# T018-T020 -- an undeclared field is a load error, on all three models
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        pytest.param(DRGNode, _VALID_NODE, id="DRGNode"),
        pytest.param(DRGEdge, _VALID_EDGE, id="DRGEdge"),
        pytest.param(AgentProfile, _VALID_PROFILE, id="AgentProfile"),
    ],
)
def test_an_undeclared_field_is_a_load_error(
    model: type[BaseModel], payload: dict[str, Any]
) -> None:
    """SC-003. The positive control runs first so a red here cannot be a broken payload.

    Without the control, a typo in ``payload`` would make the ``raises`` block
    pass for the wrong reason and this test would vouch for nothing.
    """
    model.model_validate(payload)

    with pytest.raises(ValidationError, match="[Ee]xtra"):
        model.model_validate({**payload, _UNDECLARED_KEY: "a value"})


def test_a_stale_scalar_role_alongside_roles_is_a_load_error() -> None:
    """The one behaviour ``extra="forbid"`` on ``AgentProfile`` actually changes.

    ``role:``-alone still coerces to ``roles:`` with a DeprecationWarning (the
    documented migration path, unchanged). Authoring *both* used to resolve
    silently in favour of ``roles`` — a contradictory profile whose discarded
    half nobody was ever told about. Measured: no shipped or fixture profile
    authors both, so nothing in the tree depends on the old resolution.
    """
    with pytest.raises(ValidationError) as excinfo:
        AgentProfile.model_validate(
            {**_VALID_PROFILE, "roles": ["architect"], "role": "implementer"}
        )

    message = str(excinfo.value)
    assert "role" in message
    assert "roles" in message


def test_the_documented_scalar_role_migration_path_still_works() -> None:
    """Guard against over-tightening: ``role:`` alone must keep coercing."""
    payload = {k: v for k, v in _VALID_PROFILE.items() if k != "roles"}

    with pytest.deprecated_call():
        profile = AgentProfile.model_validate({**payload, "role": "implementer"})

    assert [str(role) for role in profile.roles] == ["implementer"]


# ---------------------------------------------------------------------------
# Blast radius -- the shipped tree must still load under the strict models
# ---------------------------------------------------------------------------


def test_every_shipped_drg_fragment_still_loads_under_the_strict_models() -> None:
    """``extra="forbid"`` is only correct if nothing shipped relies on the silence."""
    fragments = sorted(_SRC_DOCTRINE.glob("*.graph.yaml"))
    assert len(fragments) >= _MINIMUM_SHIPPED_FRAGMENTS, (
        f"expected at least {_MINIMUM_SHIPPED_FRAGMENTS} shipped graph fragments; "
        f"found {len(fragments)} -- this assertion passes vacuously on an empty walk"
    )

    yaml_safe = YAML(typ="safe")
    for fragment in fragments:
        document = yaml_safe.load(fragment.read_text(encoding="utf-8")) or {}
        for raw in document.get("nodes") or []:
            DRGNode.model_validate(raw)
        for raw in document.get("edges") or []:
            DRGEdge.model_validate(raw)


def test_every_shipped_agent_profile_still_loads_under_the_strict_model() -> None:
    """Same check for the 18 built-in profiles."""
    profiles = sorted((_SRC_DOCTRINE / "agent_profiles" / "built-in").glob("*.agent.yaml"))
    assert len(profiles) >= _MINIMUM_SHIPPED_PROFILES, (
        f"expected at least {_MINIMUM_SHIPPED_PROFILES} built-in profiles; "
        f"found {len(profiles)} -- this assertion passes vacuously on an empty walk"
    )

    yaml_safe = YAML(typ="safe")
    for profile in profiles:
        AgentProfile.model_validate(yaml_safe.load(profile.read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# T016 -- the writers are derived from the model, not restated
# ---------------------------------------------------------------------------


def test_every_declared_edge_field_is_emitted_unless_explicitly_withheld() -> None:
    """Total over ``DRGEdge.model_fields``: a new field is emitted or declared withheld."""
    edge = DRGEdge(
        source="tactic:a",
        target="tactic:b",
        relation=Relation.REQUIRES,
        when="a condition",
        reason="a rationale",
        provenance="org:acme",
    )

    emitted = set(extractor._edge_to_dict(edge))

    assert emitted == set(DRGEdge.model_fields) - extractor._FIELDS_WITHHELD_FROM_GRAPH_OUTPUT


def test_every_declared_node_field_is_emitted_unless_explicitly_withheld() -> None:
    """Same totality for ``DRGNode``."""
    node = DRGNode(
        urn="anti_pattern:big-ball-of-mud",
        kind=NodeKind.ANTI_PATTERN,
        label="Big Ball of Mud",
        provenance="org:acme",
        tags=["smell"],
    )

    emitted = set(extractor._node_to_dict(node))

    assert emitted == set(DRGNode.model_fields) - extractor._FIELDS_WITHHELD_FROM_GRAPH_OUTPUT


def test_the_withholding_set_names_only_real_model_fields() -> None:
    """Anti-rot: a typo in the withholding set withholds nothing and says nothing."""
    declared = set(DRGNode.model_fields) | set(DRGEdge.model_fields)

    assert extractor._FIELDS_WITHHELD_FROM_GRAPH_OUTPUT
    assert declared >= extractor._FIELDS_WITHHELD_FROM_GRAPH_OUTPUT


def test_the_withholding_set_is_exactly_provenance_and_nothing_else() -> None:
    """Shrink-only: the withholding set is an allowlist, so it must not be paddable.

    Without this, the totality assertion above has a free escape. An author who
    adds a field to :class:`DRGEdge` meets a red
    ``test_every_declared_edge_field_is_emitted_unless_explicitly_withheld`` and
    has two ways to answer it: emit the field (correct), or name it here (which
    silently reinstates the exact write-side drop this module exists to close).
    Review found that padding the set with a *new* field passed all 277 tests in
    ``tests/doctrine/drg/`` — the second answer was free, and the module docstring
    legitimises it as one of two valid responses without saying it reinstates the
    bug.

    Pinning the content makes that answer cost a deliberate, diff-visible edit to
    this assertion with a written rationale, which is what Standing Order 5's
    shrink-only allowlist requires. ``provenance`` is the only legitimate member:
    no shipped node or edge carries the key, and no writer reachable from
    ``_dump_graph_document`` sets it, so withholding it is lossless today.
    """
    assert frozenset({"provenance"}) == extractor._FIELDS_WITHHELD_FROM_GRAPH_OUTPUT, (
        "The withholding set is an allowlist against silent write-side field "
        "drops. Adding a member here re-opens that hole for the named field — "
        "if that is genuinely intended, change this assertion in the same commit "
        "and say why the field must never reach *.graph.yaml."
    )


def test_provenance_is_withheld_so_graph_output_stays_stable() -> None:
    """FR-013's merge-time marker must not leak into ``*.graph.yaml``."""
    node = DRGNode(urn="tactic:a", kind=NodeKind.TACTIC, provenance="org:acme")
    edge = DRGEdge(
        source="tactic:a",
        target="tactic:b",
        relation=Relation.REQUIRES,
        provenance="org:acme",
    )

    assert "provenance" not in extractor._node_to_dict(node)
    assert "provenance" not in extractor._edge_to_dict(edge)


def test_the_writers_still_omit_unset_optionals_and_empty_lists() -> None:
    """Field-derived does not mean field-dumping: the output shape is unchanged."""
    node = DRGNode(urn="tactic:a", kind=NodeKind.TACTIC)
    edge = DRGEdge(source="tactic:a", target="tactic:b", relation=Relation.REQUIRES)

    assert extractor._node_to_dict(node) == {"urn": "tactic:a", "kind": "tactic"}
    assert extractor._edge_to_dict(edge) == {
        "source": "tactic:a",
        "target": "tactic:b",
        "relation": "requires",
    }


def test_the_writers_still_strip_surrounding_whitespace() -> None:
    """Wrapped YAML scalars arrive padded; the shipped graph carries them trimmed."""
    node = DRGNode(urn="tactic:a", kind=NodeKind.TACTIC, label="  Padded Label\n")
    edge = DRGEdge(
        source="tactic:a",
        target="tactic:b",
        relation=Relation.REQUIRES,
        when="  padded when\n",
        reason="\n padded reason ",
    )

    assert extractor._node_to_dict(node)["label"] == "Padded Label"
    assert extractor._edge_to_dict(edge)["when"] == "padded when"
    assert extractor._edge_to_dict(edge)["reason"] == "padded reason"


def test_the_field_derived_writers_reproduce_the_shipped_graph_exactly() -> None:
    """NFR-004: deriving from ``model_fields`` must not move one key of the graph.

    Runs the replaced hand-written shape against every shipped edge and requires
    agreement. This is the graph-neutrality claim as an executable assertion
    rather than a sentence in the PR body.
    """
    fragments = sorted(_SRC_DOCTRINE.glob("*.graph.yaml"))
    assert len(fragments) >= _MINIMUM_SHIPPED_FRAGMENTS

    yaml_safe = YAML(typ="safe")
    compared = 0
    for fragment in fragments:
        document = yaml_safe.load(fragment.read_text(encoding="utf-8")) or {}
        for raw in document.get("edges") or []:
            edge = DRGEdge.model_validate(raw)
            assert extractor._edge_to_dict(edge) == _hand_written_edge_dict(edge)
            compared += 1

    assert compared > 0, "no shipped edges were compared -- the walk found nothing"


# ---------------------------------------------------------------------------
# T021/T022 -- a newly declared field survives write -> read, non-vacuously
# ---------------------------------------------------------------------------


def _new_field_edge() -> _DRGEdgeWithNewField:
    return _DRGEdgeWithNewField(
        source="tactic:a",
        target="tactic:b",
        relation=Relation.REQUIRES,
        audit_note="ledger-42",
    )


def test_a_newly_declared_edge_field_survives_write_then_read(tmp_path: Path) -> None:
    """SC-003, through the real transport: writer → YAML file → loader → model."""
    fragment = tmp_path / "planted.graph.yaml"
    written = extractor._edge_to_dict(_new_field_edge())

    yaml_writer = YAML()
    yaml_writer.default_flow_style = False
    with fragment.open("w", encoding="utf-8") as handle:
        yaml_writer.dump({"edges": [written]}, handle)

    reloaded = YAML(typ="safe").load(fragment.read_text(encoding="utf-8"))
    restored = _DRGEdgeWithNewField.model_validate(reloaded["edges"][0])

    assert restored.audit_note == "ledger-42"
    assert restored == _new_field_edge()


def test_the_hand_written_writer_shape_would_drop_the_new_field() -> None:
    """T022: the round-trip above must be able to fail.

    The replaced writer shape is run against the same edge. It drops the field —
    so the round-trip assertion is testing the change, not the language.
    """
    edge = _new_field_edge()

    assert "audit_note" not in _hand_written_edge_dict(edge)
    assert extractor._edge_to_dict(edge)["audit_note"] == "ledger-42"


def test_the_strict_model_rejects_what_the_hand_written_writer_left_behind() -> None:
    """The two halves interlock — this is why C-009 puts them in one commit.

    Read the hand-written writer's output back into the model that declares the
    field and the value is simply gone: no error, no warning, a silently
    downgraded edge. That is the outcome ``extra="forbid"`` alone cannot prevent,
    because there is nothing extra left to forbid.
    """
    dropped = _DRGEdgeWithNewField.model_validate(
        _hand_written_edge_dict(_new_field_edge())
    )

    assert dropped.audit_note is None

    with pytest.raises(ValidationError, match="[Ee]xtra"):
        DRGEdge.model_validate(extractor._edge_to_dict(_new_field_edge()))


# ---------------------------------------------------------------------------
# T015 -- _KIND_MAP is total, and its subscript read sites are safe
# ---------------------------------------------------------------------------


def test_kind_map_names_every_node_kind() -> None:
    """Derived from ``NodeKind``, so a new member cannot be dropped by omission."""
    assert set(extractor._KIND_MAP) == {kind.value for kind in NodeKind}
    assert all(extractor._KIND_MAP[kind.value] is kind for kind in NodeKind)


def test_kind_for_type_resolves_every_node_kind() -> None:
    """The five previously-dropped kinds resolve through the public helper."""
    assert [extractor._kind_for_type(kind.value) for kind in NodeKind] == list(NodeKind)


def test_kind_for_type_still_returns_none_for_an_unrecognised_type() -> None:
    """Totality closes the kind hole without turning an authoring typo into a crash.

    Inherited from ``test_extractor_asset.py``, which used ``asset`` as its
    "unknown type" probe. ``asset`` is a ``NodeKind`` and now resolves, so the
    probe moved to a string that is genuinely not a kind — the contract it was
    guarding (``.get``-based, never a raising subscript) is unchanged.
    """
    assert extractor._kind_for_type("some-future-kind-not-yet-registered") is None
    assert extractor._kind_for_type("") is None


def test_every_action_scope_field_kind_resolves_to_a_node_kind() -> None:
    """The scope-field walk subscripts ``_KIND_MAP``; prove the subscript is safe.

    The read site used ``.get(kind, NodeKind.GLOSSARY_SCOPE)``, so an unmapped
    scope-field kind produced a *wrongly-kinded* node instead of an error — a
    silent corruption rather than a silent omission. It is now a subscript, and
    this derives the safety from the declaration rather than restating the seven
    kinds.
    """
    assert extractor._ACTION_SCOPE_FIELDS
    unmapped = [kind for _, kind in extractor._ACTION_SCOPE_FIELDS if kind not in extractor._KIND_MAP]

    assert unmapped == []


# ---------------------------------------------------------------------------
# T023a -- the retired-relationship error must name a path that exists
# ---------------------------------------------------------------------------


def test_the_retired_relationship_error_does_not_point_at_a_dead_path() -> None:
    """``src/doctrine/graph.yaml`` was retired for per-kind fragments (DD-7/DD-8).

    An error message whose "do this instead" names a file that does not exist
    sends the reader looking for it. Pinned against the filesystem rather than
    against the message text, so the assertion tracks the layout instead of the
    wording.
    """
    assert not (_SRC_DOCTRINE / "graph.yaml").exists()
    assert sorted(_SRC_DOCTRINE.glob("*.graph.yaml"))

    with pytest.raises(ValidationError) as excinfo:
        AgentProfile.model_validate({**_VALID_PROFILE, "specializes-from": "other"})

    message = str(excinfo.value)
    assert "src/doctrine/graph.yaml" not in message
    assert ".graph.yaml" in message

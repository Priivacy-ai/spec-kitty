"""WP03 (#3488, FR-008) — bind the DRG-emit seam to the profile-delivery seam.

**C-004 context (verify-first — no shipped delivery code changed here).**
Grounding confirmed the rc1 #3488 delivery gaps are already fixed on current
main: operating-procedures is data-driven into the DRG
(``_emit_operating_procedure_edges``,
``src/doctrine/drg/migration/extractor.py``) with a fail-closed doctor check
(``_run_operating_procedures_check``,
``src/specify_cli/cli/commands/_doctrine_collect.py``); step ``description``
renders (``format_inline_named_body``,
``src/charter/context_renderers/profile_sections.py``); styleguide/toolguide
pointer-only delivery is a *documented, deliberate* NFR-001 token-budget
choice (``_STYLEGUIDE_TOOLGUIDE_POINTER_ONLY_REASON``, same module). The
residual this file closes is structural, not a code fix: no test previously
bound the DRG-emit side (a profile-selector field really is projected into
the graph) to the delivery side (that same channel reaches the agent, either
as an inline body or as an *attested* pointer-only fetch stanza) — so the two
seams could silently re-diverge (e.g. a new channel wired into DRG
projection but never wired into ``_render_profile_sections``'s renderer
list, or wired pointer-only with no documented reason).

**FR-008 anti-divergence test design.** The five profile-selector channels
``_render_profile_sections`` composes are grouped into two buckets:

* **body-delivering** — ``directive`` (``directive-references`` →
  ``_render_profile_directives``), ``tactic`` (``tactic-references`` →
  ``_render_profile_tactics``), and ``operating-procedures`` (the
  ``collaboration.operating-procedures`` field → an
  ``agent_profile --requires--> procedure`` DRG edge → the profile channel →
  ``render_profile_procedures``). Each renders the artifact's verbatim body
  inline.
* **attested pointer-only** — ``styleguide`` / ``toolguide``
  (``styleguide-references`` / ``toolguide-references`` →
  ``render_profile_styleguides`` / ``render_profile_toolguides``, both
  ``body_fn=None`` by design). Never an inline body; always the fetch
  stanza, and the *reason* for that choice is a named, importable constant
  rather than only a docstring aside.

``test_directive_tactic_operating_procedures_are_emitted_as_drg_edges`` binds
the **emit** half: it runs the single-authority extractor
(``extract_artifact_edges``, mirroring the tmp_path pack-fixture pattern used
throughout ``tests/doctrine/drg/migration/test_extractor.py``) over a minimal
fixture pack and asserts the three body-delivering channels really do land as
``agent_profile --requires--> {directive,tactic,procedure}`` DRG edges — not
merely assumed from reading the source.

``test_real_projected_channels_are_delivered_or_attested_pointer_only`` binds
the **delivery** half: it renders one synthetic profile citing all five
channels through the real ``_render_profile_sections`` entry point and
classifies each channel's rendered output as ``"body"``, ``"pointer_only"``,
or ``"undelivered"`` (an inline body is present XOR the fetch-stanza selector
is present; anything else — neither, or ambiguously both — is a divergence).
The FR-008 invariant, ``_is_consistent``, accepts ``"body"`` outright and
accepts ``"pointer_only"`` only when the channel carries a non-empty attested
reason; ``"undelivered"`` is always a failure.

**Red-first proof.** The classifier and invariant are generic — they do not
special-case the five real channel names — so the two synthetic-channel tests
below (``test_synthetic_undelivered_channel_is_caught`` and
``test_synthetic_unattested_pointer_only_channel_is_caught``) exercise the
*same* ``_classify_delivery`` / ``_is_consistent`` pair against a fabricated
channel that mimics exactly what a future one-seam-only divergence would look
like: a channel projected into the DRG whose delivery renderer was either
never wired up (renders neither a body nor its own fetch stanza) or wired
``body_fn=None`` with no attestation (silent pointer-only, the pre-#3488-fix
defect class). Both synthetic cases fail the invariant; the five real
channels, exercised through the identical mechanism in the test just above,
currently pass — proving the check is live, not a tautology.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

import pytest

from charter.context_renderers.profile_sections import (
    _STYLEGUIDE_TOOLGUIDE_POINTER_ONLY_REASON,
    _render_profile_sections,
)
from doctrine.agent_profiles import AgentProfile
from doctrine.drg.migration.extractor import extract_artifact_edges
from doctrine.drg.migration.id_normalizer import artifact_to_urn
from doctrine.drg.models import Relation

pytestmark = pytest.mark.fast

_DeliveryMode = Literal["body", "pointer_only", "undelivered"]


# ---------------------------------------------------------------------------
# Delivery-side fixture: one synthetic profile exercising all five channels
# through the real ``_render_profile_sections`` entry point.
# ---------------------------------------------------------------------------


class _StubCatalogRepo:
    """Minimal ``_CatalogRepoLike`` stand-in: a fixed id -> artifact mapping."""

    def __init__(self, items: dict[str, object]) -> None:
        self._items = items

    def get(self, item_id: str) -> object | None:
        return self._items.get(item_id)


class _StubProcedureChannel:
    """Stubs the slice of ``AgentProfileRepository`` ``render_profile_procedures``
    depends on (WP08's ``requires``/``specializes_from`` walk) without needing a
    real, materialized DRG. ``render_profile_suggested_doctrine`` also probes
    ``agent_profiles`` for ``profile_channel_reached``; that method is
    deliberately absent here, so the lookup raises ``AttributeError`` and the
    renderer's own broad ``except Exception: return []`` degrades it to no
    section — the fixture only needs to speak the one surface under test.
    """

    def __init__(self, procedure_ids: list[str]) -> None:
        self._procedure_ids = procedure_ids

    def profile_channel_procedure_ids(self, profile_id: str) -> list[str]:
        return self._procedure_ids


def _fixture_profile() -> AgentProfile:
    """A profile citing all four direct-citation channels (T010/T011)."""
    return AgentProfile.model_validate(
        {
            "profile-id": "fr008-bind-fixture",
            "name": "FR-008 Bind Fixture",
            "roles": ["implementer"],
            "purpose": "test fixture for the FR-008 emit<->delivery bind",
            "specialization": {"primary-focus": "testing"},
            "directive-references": [
                {
                    "code": "DIRECTIVE_999",
                    "name": "Fixture Directive",
                    "rationale": "bind test",
                }
            ],
            "tactic-references": [
                {"id": "fixture-tactic", "rationale": "bind test"}
            ],
            "styleguide-references": [
                {"id": "fixture-styleguide", "rationale": "bind test"}
            ],
            "toolguide-references": [
                {"id": "fixture-toolguide", "rationale": "bind test"}
            ],
        }
    )


def _fixture_service() -> SimpleNamespace:
    """A ``DoctrineService``-shaped stub: every catalog resolves, deterministically."""
    return SimpleNamespace(
        directives=_StubCatalogRepo(
            {"DIRECTIVE_999": SimpleNamespace(intent="Do the fixture thing.")}
        ),
        tactics=_StubCatalogRepo(
            {
                "fixture-tactic": SimpleNamespace(
                    name="Fixture Tactic", purpose="A fixture tactic body.", steps=[]
                )
            }
        ),
        styleguides=_StubCatalogRepo(
            {"fixture-styleguide": SimpleNamespace(title="Fixture Styleguide")}
        ),
        toolguides=_StubCatalogRepo(
            {"fixture-toolguide": SimpleNamespace(title="Fixture Toolguide")}
        ),
        procedures=_StubCatalogRepo(
            {
                "fixture-procedure": SimpleNamespace(
                    name="Fixture Procedure",
                    purpose="A fixture procedure body.",
                    steps=[],
                )
            }
        ),
        agent_profiles=_StubProcedureChannel(["fixture-procedure"]),
    )


# ---------------------------------------------------------------------------
# The FR-008 classifier + invariant — generic over any channel, real or
# synthetic (no per-name special-casing), which is what makes the
# undelivered/unattested tests below a genuine red-first proof rather than a
# hand-tuned assertion.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ProjectedChannel:
    """One profile-selector channel projected into the DRG.

    ``body_marker`` is a string that only appears in the rendered block when
    the channel's artifact body was inlined. ``fetch_selector`` is the
    ``<kind>:<id>`` selector the canonical fetch stanza
    (``Run: spec-kitty charter context --include <selector>``) would carry if
    the channel rendered pointer-only. ``attested_reason`` is the documented,
    non-empty rationale for pointer-only delivery when that is the design
    (``None`` for channels that are never meant to be pointer-only).
    """

    name: str
    body_marker: str | None
    fetch_selector: str
    attested_reason: str | None


def _fetch_stanza_line(selector: str) -> str:
    return f"Run: spec-kitty charter context --include {selector}"


def _classify_delivery(block: str, channel: _ProjectedChannel) -> _DeliveryMode:
    """Classify how *channel* actually reached the rendered *block*.

    ``"undelivered"`` is the FR-008 divergence: a channel that is projected
    into the DRG but whose rendered output carries neither an inline body nor
    its own fetch-stanza pointer — it silently reaches no agent.
    """
    has_body = channel.body_marker is not None and channel.body_marker in block
    has_fetch = _fetch_stanza_line(channel.fetch_selector) in block
    if has_body and not has_fetch:
        return "body"
    if has_fetch and not has_body:
        return "pointer_only"
    return "undelivered"


def _is_consistent(channel: _ProjectedChannel, mode: _DeliveryMode) -> bool:
    """FR-008 invariant: every projected channel is body-delivering OR attests
    a documented pointer-only reason. ``"undelivered"`` never satisfies it,
    and ``"pointer_only"`` without a reason does not either — distinguishing a
    *deliberate* NFR-001-style choice from a silent no-op.
    """
    if mode == "body":
        return True
    if mode == "pointer_only":
        return bool(channel.attested_reason)
    return False


_REAL_PROJECTED_CHANNELS: tuple[_ProjectedChannel, ...] = (
    _ProjectedChannel(
        name="directive",
        body_marker="Intent: Do the fixture thing.",
        fetch_selector="directive:DIRECTIVE_999",
        attested_reason=None,
    ),
    _ProjectedChannel(
        name="tactic",
        body_marker="Name: Fixture Tactic",
        fetch_selector="tactic:fixture-tactic",
        attested_reason=None,
    ),
    _ProjectedChannel(
        name="operating-procedures",
        body_marker="Name: Fixture Procedure",
        fetch_selector="procedure:fixture-procedure",
        attested_reason=None,
    ),
    _ProjectedChannel(
        name="styleguide",
        body_marker=None,
        fetch_selector="styleguide:fixture-styleguide",
        attested_reason=_STYLEGUIDE_TOOLGUIDE_POINTER_ONLY_REASON,
    ),
    _ProjectedChannel(
        name="toolguide",
        body_marker=None,
        fetch_selector="toolguide:fixture-toolguide",
        attested_reason=_STYLEGUIDE_TOOLGUIDE_POINTER_ONLY_REASON,
    ),
)


# ---------------------------------------------------------------------------
# T010 — the FR-008 structural bind.
# ---------------------------------------------------------------------------


def test_real_projected_channels_are_delivered_or_attested_pointer_only() -> None:
    """Every real projected channel is currently body-delivering or attested
    pointer-only — the seam is consistent today (this is the "confirm the
    test currently PASSES for the real channels" half of the red-first proof).
    """
    block = _render_profile_sections(_fixture_profile(), _fixture_service())

    results = {
        channel.name: _classify_delivery(block, channel)
        for channel in _REAL_PROJECTED_CHANNELS
    }

    assert results == {
        "directive": "body",
        "tactic": "body",
        "operating-procedures": "body",
        "styleguide": "pointer_only",
        "toolguide": "pointer_only",
    }
    for channel in _REAL_PROJECTED_CHANNELS:
        assert _is_consistent(channel, results[channel.name]), (
            f"channel {channel.name!r} classified as {results[channel.name]!r} "
            "violates the FR-008 body-or-attested-pointer-only invariant"
        )


def test_synthetic_undelivered_channel_is_caught() -> None:
    """Red-first proof (1/2): a channel projected into the DRG whose delivery
    renderer was never wired up — neither an inline body nor its own fetch
    stanza reaches the rendered block — fails the FR-008 invariant. This is
    exactly what a future channel added to DRG projection but forgotten in
    ``_render_profile_sections``'s renderer list would look like.
    """
    block = _render_profile_sections(_fixture_profile(), _fixture_service())
    ghost_channel = _ProjectedChannel(
        name="hypothetical-new-channel",
        body_marker="Name: Ghost Artifact",
        fetch_selector="ghost-kind:ghost-artifact",
        attested_reason=None,
    )

    mode = _classify_delivery(block, ghost_channel)

    assert mode == "undelivered"
    assert not _is_consistent(ghost_channel, mode)


def test_synthetic_unattested_pointer_only_channel_is_caught() -> None:
    """Red-first proof (2/2): a channel that renders pointer-only but carries
    no attested reason also fails — distinguishing the *documented*
    NFR-001-style design choice (styleguide/toolguide) from an undocumented,
    silent pointer-only drop (the pre-#3488-fix defect class).
    """
    block = _render_profile_sections(_fixture_profile(), _fixture_service())
    # Reuse a real fetch selector so ``has_fetch`` is genuinely True; the only
    # difference from the real ``styleguide`` channel is the missing attestation.
    unattested_channel = _ProjectedChannel(
        name="hypothetical-unattested-pointer-only",
        body_marker=None,
        fetch_selector="styleguide:fixture-styleguide",
        attested_reason=None,
    )

    mode = _classify_delivery(block, unattested_channel)

    assert mode == "pointer_only"
    assert not _is_consistent(unattested_channel, mode)


def test_directive_tactic_operating_procedures_are_emitted_as_drg_edges(
    tmp_path: Path,
) -> None:
    """Emit-side half of the bind: the three body-delivering channels above
    really are projected into the DRG by the single-authority extractor
    (``extract_artifact_edges`` — C-004, no re-implementation), not merely
    assumed from reading the source. Mirrors the tmp_path pack-fixture
    pattern used by ``test_procedure_reference_reason_roundtrips`` et al. in
    ``tests/doctrine/drg/migration/test_extractor.py``.
    """
    doctrine_root = tmp_path / "pack"
    (doctrine_root / "directives").mkdir(parents=True)
    (doctrine_root / "tactics").mkdir(parents=True)
    (doctrine_root / "procedures").mkdir(parents=True)
    (doctrine_root / "agent_profiles").mkdir(parents=True)

    (doctrine_root / "directives" / "bind-fixture.directive.yaml").write_text(
        "schema_version: '1.0'\nid: bind-fixture\ntitle: Bind Fixture Directive\n",
        encoding="utf-8",
    )
    (doctrine_root / "tactics" / "bind-fixture.tactic.yaml").write_text(
        "schema_version: '1.0'\nid: bind-fixture\nname: Bind Fixture Tactic\n",
        encoding="utf-8",
    )
    (doctrine_root / "procedures" / "bind-fixture.procedure.yaml").write_text(
        "schema_version: '1.0'\nid: bind-fixture\nname: Bind Fixture Procedure\npurpose: test\n",
        encoding="utf-8",
    )
    (doctrine_root / "agent_profiles" / "bind-fixture.agent.yaml").write_text(
        "\n".join(
            [
                "profile-id: bind-fixture",
                "name: Bind Fixture Profile",
                "context-sources:",
                "  directives: [bind-fixture]",
                "tactic-references:",
                "  - id: bind-fixture",
                "collaboration:",
                "  operating-procedures: [bind-fixture]",
                "",
            ]
        ),
        encoding="utf-8",
    )

    _nodes, edges = extract_artifact_edges(doctrine_root)
    edge_triples = {(edge.source, edge.target, edge.relation) for edge in edges}
    profile_urn = artifact_to_urn("agent_profile", "bind-fixture")

    assert (
        profile_urn,
        artifact_to_urn("directive", "bind-fixture"),
        Relation.REQUIRES,
    ) in edge_triples
    assert (
        profile_urn,
        artifact_to_urn("tactic", "bind-fixture"),
        Relation.REQUIRES,
    ) in edge_triples
    assert (
        profile_urn,
        artifact_to_urn("procedure", "bind-fixture"),
        Relation.REQUIRES,
    ) in edge_triples


# ---------------------------------------------------------------------------
# T011 — attest the pointer-only reason (AC-006): a test-pinned constant, not
# only a code docstring.
# ---------------------------------------------------------------------------


def test_pointer_only_reason_is_attested_non_empty() -> None:
    """The styleguide/toolguide pointer-only choice is a named, non-empty,
    importable constant — test-attested rather than only a docstring aside.
    """
    assert isinstance(_STYLEGUIDE_TOOLGUIDE_POINTER_ONLY_REASON, str)
    assert _STYLEGUIDE_TOOLGUIDE_POINTER_ONLY_REASON.strip()
    assert "NFR-001" in _STYLEGUIDE_TOOLGUIDE_POINTER_ONLY_REASON

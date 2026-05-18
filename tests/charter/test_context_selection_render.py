"""WP04 unit tests — charter-level global selection renderers.

This module pins the behaviour of the 5 ``_render_selected_<kind>``
helpers introduced by WP04 of mission
``charter-mediated-doctrine-selection-01KRTZCA``.

Coverage (per the WP04 task file → "T021 Unit tests"):

* One-artifact-per-kind: each kind renders its artifact ID + body when
  the budget allows.
* Token-budget overflow: a large body triggers fetch + when-doing
  stanza substitution.
* Org-provenance: a styleguide loaded via the org layer carries
  ``source: org`` in the rendered output.
* Empty selection: no output line emitted (no leading header, no
  trailing artifact section).
* Catalog miss: an ID that the repository does not carry surfaces the
  placeholder body + fetch stanza (no crash).

The renderers are pure functions over a ``DoctrineService``-shaped
object; tests stub the repository surface rather than load the real
shipped tree so failures isolate to the renderer logic.
"""

from __future__ import annotations

from typing import Any

import pytest

from charter.context import (
    _PROFILE_INLINE_BODY_LIMIT_CHARS,
    _SELECTED_AGENT_PROFILES_HEADER,
    _SELECTED_MISSION_STEP_CONTRACTS_HEADER,
    _SELECTED_PROCEDURES_HEADER,
    _SELECTED_STYLEGUIDES_HEADER,
    _SELECTED_TOOLGUIDES_HEADER,
    _collect_org_source_map,
    _provenance_suffix,
    _render_selected_agent_profiles,
    _render_selected_mission_step_contracts,
    _render_selected_procedures,
    _render_selected_styleguides,
    _render_selected_toolguides,
    _render_selection_block,
)
from charter.schemas import DoctrineSelectionConfig


pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Stub doubles for the DoctrineService repositories
# ---------------------------------------------------------------------------


class _StubRepo:
    """Minimal repository stub mirroring :meth:`BaseDoctrineRepository.get`."""

    def __init__(
        self,
        items: dict[str, Any] | None = None,
        provenance: dict[str, str] | None = None,
    ) -> None:
        self._items = items or {}
        self._provenance = provenance or {}

    def get(self, item_id: str) -> Any | None:  # noqa: ANN401 — duck-typed
        return self._items.get(item_id)

    def get_provenance(self, item_id: str) -> str | None:
        return self._provenance.get(item_id)


class _StubService:
    """Minimal DoctrineService stand-in carrying the 5 selection repos."""

    def __init__(
        self,
        *,
        styleguides: _StubRepo | None = None,
        toolguides: _StubRepo | None = None,
        procedures: _StubRepo | None = None,
        agent_profiles: _StubRepo | None = None,
        mission_step_contracts: _StubRepo | None = None,
    ) -> None:
        self.styleguides = styleguides or _StubRepo()
        self.toolguides = toolguides or _StubRepo()
        self.procedures = procedures or _StubRepo()
        self.agent_profiles = agent_profiles or _StubRepo()
        self.mission_step_contracts = mission_step_contracts or _StubRepo()


class _DummyStyleguide:
    def __init__(self, *, title: str, principles: list[str], scope: str = "code") -> None:
        self.title = title
        self.scope = scope
        self.principles = principles


class _DummyToolguide:
    def __init__(self, *, title: str, tool: str, summary: str) -> None:
        self.title = title
        self.tool = tool
        self.summary = summary


class _DummyProcedure:
    def __init__(
        self,
        *,
        name: str,
        purpose: str,
        entry: str,
        exit_: str,
        steps: list[Any],
    ) -> None:
        self.name = name
        self.purpose = purpose
        self.entry_condition = entry
        self.exit_condition = exit_
        self.steps = steps


class _DummyStep:
    def __init__(self, *, title: str, id_: str | None = None, description: str = "") -> None:
        self.title = title
        self.id = id_
        self.description = description


class _DummyAgentProfile:
    def __init__(self, *, name: str, purpose: str, roles: list[str]) -> None:
        self.name = name
        self.purpose = purpose
        self.roles = roles


class _DummyContract:
    def __init__(
        self,
        *,
        action: str,
        mission: str,
        steps: list[_DummyStep],
    ) -> None:
        self.action = action
        self.mission = mission
        self.steps = steps


# ---------------------------------------------------------------------------
# Empty-selection contract — no header, no body
# ---------------------------------------------------------------------------


class TestEmptySelection:
    """An empty selection MUST NOT emit a header, body line, or stray block."""

    def test_render_selected_styleguides_returns_empty_when_no_selection(self) -> None:
        assert _render_selected_styleguides([], _StubService()) == []

    def test_render_selected_toolguides_returns_empty_when_no_selection(self) -> None:
        assert _render_selected_toolguides([], _StubService()) == []

    def test_render_selected_procedures_returns_empty_when_no_selection(self) -> None:
        assert _render_selected_procedures([], _StubService()) == []

    def test_render_selected_agent_profiles_returns_empty_when_no_selection(self) -> None:
        assert _render_selected_agent_profiles([], _StubService()) == []

    def test_render_selected_mission_step_contracts_returns_empty_when_no_selection(
        self,
    ) -> None:
        assert _render_selected_mission_step_contracts([], _StubService()) == []

    def test_selection_block_returns_empty_string_when_all_empty(self) -> None:
        selection = DoctrineSelectionConfig()
        assert _render_selection_block(selection, _StubService()) == ""


# ---------------------------------------------------------------------------
# Inline-body rendering (one artifact per kind, budget allows)
# ---------------------------------------------------------------------------


class TestInlineBodyRendering:
    """Each renderer emits the ID + verbatim body when under the budget."""

    def test_styleguide_inline_body(self) -> None:
        sg = _DummyStyleguide(
            title="Caveman Comments",
            principles=["UGG STYLE", "VERBS ONLY"],
        )
        service = _StubService(styleguides=_StubRepo(items={"caveman-comments": sg}))
        lines = _render_selected_styleguides(["caveman-comments"], service)
        joined = "\n".join(lines)
        assert _SELECTED_STYLEGUIDES_HEADER in joined
        assert "caveman-comments" in joined
        assert "Caveman Comments" in joined
        assert "UGG STYLE" in joined
        # No fetch stanza when body fits.
        assert "spec-kitty charter context --include" not in joined

    def test_toolguide_inline_body(self) -> None:
        tg = _DummyToolguide(title="Pytest Runner", tool="pytest", summary="Run the suite.")
        service = _StubService(toolguides=_StubRepo(items={"runner": tg}))
        lines = _render_selected_toolguides(["runner"], service)
        joined = "\n".join(lines)
        assert _SELECTED_TOOLGUIDES_HEADER in joined
        assert "runner" in joined
        assert "Pytest Runner" in joined
        assert "Run the suite." in joined

    def test_procedure_inline_body(self) -> None:
        proc = _DummyProcedure(
            name="Onboarding",
            purpose="Bring a new contributor up to speed.",
            entry="Contributor opens repo",
            exit_="Contributor merges first PR",
            steps=[_DummyStep(title="Clone repo"), _DummyStep(title="Read CONTRIBUTING")],
        )
        service = _StubService(procedures=_StubRepo(items={"onboarding": proc}))
        lines = _render_selected_procedures(["onboarding"], service)
        joined = "\n".join(lines)
        assert _SELECTED_PROCEDURES_HEADER in joined
        assert "onboarding" in joined
        assert "Onboarding" in joined
        assert "Clone repo" in joined

    def test_agent_profile_inline_body(self) -> None:
        ap = _DummyAgentProfile(
            name="Python Pedro",
            purpose="Implement Python work with TDD discipline.",
            roles=["implementer"],
        )
        service = _StubService(agent_profiles=_StubRepo(items={"python-pedro": ap}))
        lines = _render_selected_agent_profiles(["python-pedro"], service)
        joined = "\n".join(lines)
        assert _SELECTED_AGENT_PROFILES_HEADER in joined
        assert "python-pedro" in joined
        assert "Python Pedro" in joined
        assert "implementer" in joined

    def test_mission_step_contract_inline_body(self) -> None:
        contract = _DummyContract(
            action="implement",
            mission="software-dev",
            steps=[_DummyStep(title="t", id_="s1", description="First step")],
        )
        service = _StubService(
            mission_step_contracts=_StubRepo(items={"impl-contract": contract})
        )
        lines = _render_selected_mission_step_contracts(["impl-contract"], service)
        joined = "\n".join(lines)
        assert _SELECTED_MISSION_STEP_CONTRACTS_HEADER in joined
        assert "impl-contract" in joined
        assert "implement" in joined
        assert "s1" in joined


# ---------------------------------------------------------------------------
# Token-budget overflow — body too large triggers fetch + when-doing stanza
# ---------------------------------------------------------------------------


class TestTokenBudgetOverflow:
    """Bodies above ``_PROFILE_INLINE_BODY_LIMIT_CHARS`` collapse to fetch."""

    def test_oversized_styleguide_body_emits_fetch_stanza(self) -> None:
        # Build a styleguide whose principle text alone blows the budget.
        bloat = "X" * (_PROFILE_INLINE_BODY_LIMIT_CHARS + 100)
        sg = _DummyStyleguide(title="Big Styleguide", principles=[bloat])
        service = _StubService(styleguides=_StubRepo(items={"big-sg": sg}))
        lines = _render_selected_styleguides(["big-sg"], service)
        joined = "\n".join(lines)
        assert "big-sg" in joined
        # The body line should NOT appear; the fetch stanza should.
        assert bloat not in joined
        assert "spec-kitty charter context --include styleguide:big-sg" in joined
        assert "When you are about to write a code comment" in joined

    def test_oversized_procedure_body_emits_fetch_stanza(self) -> None:
        # Many steps each rendered as one line — pushes total over budget.
        steps = [_DummyStep(title="X" * 80) for _ in range(60)]
        proc = _DummyProcedure(
            name="Bloated", purpose="bloat", entry="in", exit_="out", steps=steps
        )
        service = _StubService(procedures=_StubRepo(items={"bloated-proc": proc}))
        lines = _render_selected_procedures(["bloated-proc"], service)
        joined = "\n".join(lines)
        assert "spec-kitty charter context --include procedure:bloated-proc" in joined


# ---------------------------------------------------------------------------
# Org-provenance — org-sourced artifacts carry a suffix; project does not
# ---------------------------------------------------------------------------


class TestOrgProvenance:
    """``(source: org, pack: <name>)`` MUST appear ONLY for org-sourced IDs."""

    def test_org_sourced_styleguide_carries_source_suffix(self) -> None:
        sg = _DummyStyleguide(title="Caveman", principles=["UGG"])
        repo = _StubRepo(
            items={"caveman-comments": sg},
            provenance={"caveman-comments": "org"},
        )
        service = _StubService(styleguides=repo)
        org_map = _collect_org_source_map(repo, ["caveman-comments"])
        lines = _render_selected_styleguides(
            ["caveman-comments"], service, org_source_map=org_map
        )
        joined = "\n".join(lines)
        assert "source: org" in joined

    def test_org_source_map_with_pack_name_emits_pack_suffix(self) -> None:
        # Direct check of the suffix helper — the pack-name path collapses
        # to "(source: org, pack: <name>)" when the map carries a pack.
        suffix = _provenance_suffix(
            "caveman-comments", {"caveman-comments": "very-serious-developers"}
        )
        assert suffix == " (source: org, pack: very-serious-developers)"

    def test_project_sourced_styleguide_carries_no_suffix(self) -> None:
        sg = _DummyStyleguide(title="Caveman", principles=["UGG"])
        repo = _StubRepo(
            items={"caveman-comments": sg},
            provenance={"caveman-comments": "project"},
        )
        service = _StubService(styleguides=repo)
        # Project sources are NOT in the org map.
        org_map = _collect_org_source_map(repo, ["caveman-comments"])
        assert org_map == {}
        lines = _render_selected_styleguides(
            ["caveman-comments"], service, org_source_map=org_map
        )
        joined = "\n".join(lines)
        assert "source: org" not in joined
        assert "source: project" not in joined

    def test_builtin_sourced_styleguide_carries_no_suffix(self) -> None:
        sg = _DummyStyleguide(title="Built-in", principles=["BI"])
        repo = _StubRepo(
            items={"builtin-sg": sg},
            provenance={"builtin-sg": "builtin"},
        )
        org_map = _collect_org_source_map(repo, ["builtin-sg"])
        assert org_map == {}


# ---------------------------------------------------------------------------
# Catalog miss — unknown ID does not crash, renders fetch stanza
# ---------------------------------------------------------------------------


class TestCatalogMiss:
    """An ID that the repository does not carry MUST surface a placeholder."""

    def test_unknown_styleguide_id_emits_placeholder_and_fetch(self) -> None:
        service = _StubService(styleguides=_StubRepo(items={}))
        lines = _render_selected_styleguides(["does-not-exist"], service)
        joined = "\n".join(lines)
        assert "does-not-exist" in joined
        assert "catalog entry not found" in joined
        assert "spec-kitty charter context --include styleguide:does-not-exist" in joined


# ---------------------------------------------------------------------------
# Deduplication — same ID twice in a selection renders once
# ---------------------------------------------------------------------------


class TestDeduplication:
    """R-4 mitigation: duplicate IDs in a selection MUST render once."""

    def test_duplicate_styleguide_id_rendered_once(self) -> None:
        sg = _DummyStyleguide(title="Caveman", principles=["UGG"])
        service = _StubService(styleguides=_StubRepo(items={"caveman-comments": sg}))
        lines = _render_selected_styleguides(
            ["caveman-comments", "caveman-comments"], service
        )
        joined = "\n".join(lines)
        # The ID + body should appear exactly once even though it was listed twice.
        assert joined.count("- caveman-comments") == 1


# ---------------------------------------------------------------------------
# Combined block — all 5 sections compose correctly
# ---------------------------------------------------------------------------


class TestCombinedSelectionBlock:
    """``_render_selection_block`` composes all 5 sections in fixed order."""

    def test_all_five_kinds_appear_in_order(self) -> None:
        sg = _DummyStyleguide(title="SG", principles=["a"])
        tg = _DummyToolguide(title="TG", tool="t", summary="s")
        proc = _DummyProcedure(
            name="P", purpose="p", entry="i", exit_="o", steps=[_DummyStep(title="s")]
        )
        ap = _DummyAgentProfile(name="A", purpose="p", roles=["implementer"])
        contract = _DummyContract(
            action="implement",
            mission="software-dev",
            steps=[_DummyStep(title="t", id_="s1", description="d")],
        )
        service = _StubService(
            styleguides=_StubRepo(items={"sg-id": sg}),
            toolguides=_StubRepo(items={"tg-id": tg}),
            procedures=_StubRepo(items={"proc-id": proc}),
            agent_profiles=_StubRepo(items={"ap-id": ap}),
            mission_step_contracts=_StubRepo(items={"msc-id": contract}),
        )
        selection = DoctrineSelectionConfig(
            selected_styleguides=["sg-id"],
            selected_toolguides=["tg-id"],
            selected_procedures=["proc-id"],
            selected_agent_profiles=["ap-id"],
            selected_mission_step_contracts=["msc-id"],
        )
        block = _render_selection_block(selection, service)
        # Stable section order: styleguides → toolguides → procedures →
        # agent_profiles → mission_step_contracts.
        idx_sg = block.index(_SELECTED_STYLEGUIDES_HEADER)
        idx_tg = block.index(_SELECTED_TOOLGUIDES_HEADER)
        idx_proc = block.index(_SELECTED_PROCEDURES_HEADER)
        idx_ap = block.index(_SELECTED_AGENT_PROFILES_HEADER)
        idx_msc = block.index(_SELECTED_MISSION_STEP_CONTRACTS_HEADER)
        assert idx_sg < idx_tg < idx_proc < idx_ap < idx_msc

    def test_only_populated_kinds_emit_headers(self) -> None:
        sg = _DummyStyleguide(title="SG", principles=["a"])
        service = _StubService(styleguides=_StubRepo(items={"sg-id": sg}))
        selection = DoctrineSelectionConfig(selected_styleguides=["sg-id"])
        block = _render_selection_block(selection, service)
        assert _SELECTED_STYLEGUIDES_HEADER in block
        assert _SELECTED_TOOLGUIDES_HEADER not in block
        assert _SELECTED_PROCEDURES_HEADER not in block
        assert _SELECTED_AGENT_PROFILES_HEADER not in block
        assert _SELECTED_MISSION_STEP_CONTRACTS_HEADER not in block

"""Tests for SPDD/REASONS charter activation and context injection.

Covers:

- ``TestActivation`` — the seven cases from contracts/activation.md.
- ``TestCharterContextInactive`` — NFR-001 byte-identical guarantee for the
  inactive baseline across all five actions.
- ``TestCharterContextActive`` — action-scoped subsection presence and the
  NFR-002 <2s performance budget.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from ruamel.yaml.error import YAMLError

from doctrine.spdd_reasons import (
    append_spdd_reasons_guidance,
    clear_activation_cache,
    is_spdd_reasons_active,
)


pytestmark = [pytest.mark.unit]

ACTIONS = ("specify", "plan", "tasks", "implement", "review")


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _charter_yaml_path(tmp_path: Path) -> Path:
    charter_dir = tmp_path / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    return charter_dir / "charter.yaml"


def _write_governance(tmp_path: Path, body: str) -> Path:
    """Merge a governance YAML body into charter.yaml's ``governance:`` section.

    consolidate-charter-bundle (IC-04 / WP04, T028c):
    ``is_spdd_reasons_active`` reads ``charter.yaml``'s ``governance:`` /
    ``directives:`` sections now, not the retired ``governance.yaml`` /
    ``directives.yaml`` files. *body* is the same bare-YAML fixture shape
    these tests always used; it is parsed and nested under ``governance:``
    rather than written as its own top-level file.
    """
    from ruamel.yaml import YAML

    yaml = YAML()
    governance_data = yaml.load(body)
    path = _charter_yaml_path(tmp_path)
    document = yaml.load(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(document, dict):
        document = {}
    document["governance"] = governance_data
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(document, fh)
    return path


def _write_directives(tmp_path: Path, body: str) -> Path:
    """Merge a directives YAML body into charter.yaml's ``directives:`` section."""
    from ruamel.yaml import YAML

    yaml = YAML()
    directives_data = yaml.load(body)
    path = _charter_yaml_path(tmp_path)
    document = yaml.load(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(document, dict):
        document = {}
    document["directives"] = directives_data
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(document, fh)
    return path


def _empty_governance() -> str:
    return (
        "doctrine:\n"
        "  selected_paradigms: []\n"
        "  selected_directives: []\n"
        "  available_tools: []\n"
        "  template_set: software-dev-default\n"
    )


# ---------------------------------------------------------------------------
# TestActivation — 7 cases from contracts/activation.md
# ---------------------------------------------------------------------------


class TestActivation:
    """The seven activation cases from contracts/activation.md."""

    def setup_method(self) -> None:
        clear_activation_cache()

    # Case 1
    def test_no_charter_returns_false(self, tmp_path: Path) -> None:
        assert is_spdd_reasons_active(tmp_path) is False

    # Case 2
    def test_unrelated_directives_returns_false(self, tmp_path: Path) -> None:
        _write_governance(
            tmp_path,
            "doctrine:\n"
            "  selected_paradigms: []\n"
            "  selected_directives:\n"
            "    - DIRECTIVE_001\n"
            "    - DIRECTIVE_024\n"
            "  available_tools: []\n",
        )
        _write_directives(
            tmp_path,
            "directives:\n"
            "  - id: DIRECTIVE_001\n"
            "    title: Some other directive\n",
        )
        assert is_spdd_reasons_active(tmp_path) is False

    # Case 3
    def test_paradigm_selected_returns_true(self, tmp_path: Path) -> None:
        _write_governance(
            tmp_path,
            "doctrine:\n"
            "  selected_paradigms:\n"
            "    - structured-prompt-driven-development\n"
            "  selected_directives: []\n"
            "  available_tools: []\n",
        )
        assert is_spdd_reasons_active(tmp_path) is True

    # Case 4
    def test_only_tactic_fill_returns_true(self, tmp_path: Path) -> None:
        _write_governance(
            tmp_path,
            "doctrine:\n"
            "  selected_paradigms: []\n"
            "  selected_directives: []\n"
            "  selected_tactics:\n"
            "    - reasons-canvas-fill\n"
            "  available_tools: []\n",
        )
        assert is_spdd_reasons_active(tmp_path) is True

    # Case 5
    def test_only_tactic_review_returns_true(self, tmp_path: Path) -> None:
        _write_governance(
            tmp_path,
            "doctrine:\n"
            "  selected_paradigms: []\n"
            "  selected_directives: []\n"
            "  selected_tactics:\n"
            "    - reasons-canvas-review\n"
            "  available_tools: []\n",
        )
        assert is_spdd_reasons_active(tmp_path) is True

    # Case 6
    def test_only_directive_038_returns_true(self, tmp_path: Path) -> None:
        _write_governance(
            tmp_path,
            "doctrine:\n"
            "  selected_paradigms: []\n"
            "  selected_directives:\n"
            "    - DIRECTIVE_038\n"
            "  available_tools: []\n",
        )
        assert is_spdd_reasons_active(tmp_path) is True

    # Case 6b — directive recorded only in directives.yaml entry list
    def test_directive_038_via_directives_yaml(self, tmp_path: Path) -> None:
        _write_governance(tmp_path, _empty_governance())
        _write_directives(
            tmp_path,
            "directives:\n"
            "  - id: DIRECTIVE_038\n"
            "    title: Structured Prompt Boundary\n",
        )
        assert is_spdd_reasons_active(tmp_path) is True

    # Case 7
    def test_malformed_governance_raises(self, tmp_path: Path) -> None:
        # A structurally-invalid charter.yaml (not just a malformed governance
        # sub-block, which _write_governance's own YAML.load would refuse to
        # persist) -- the loader exception propagates unchanged (FR-007).
        path = _charter_yaml_path(tmp_path)
        path.write_text("governance:\n  doctrine: [this: is: not: valid\n", encoding="utf-8")
        with pytest.raises(YAMLError):
            is_spdd_reasons_active(tmp_path)


# ---------------------------------------------------------------------------
# Inactive baseline (NFR-001)
# ---------------------------------------------------------------------------


class TestCharterContextInactive:
    """When inactive, charter context output MUST NOT carry the new subsection.

    The contract phrases this as "byte-or-semantic identical" to the pre-feature
    output. The simplest enforceable invariant is that the inactive output
    contains no SPDD/REASONS substring — because the conditional gate is what
    decides whether ``append_spdd_reasons_guidance`` runs at all.
    """

    def setup_method(self) -> None:
        clear_activation_cache()

    @pytest.mark.parametrize("action", ACTIONS)
    def test_inactive_output_omits_guidance(self, action: str) -> None:
        # We do not invoke build_charter_context here (it touches a live
        # charter bundle); instead we exercise the gate directly: the only
        # caller of append_spdd_reasons_guidance is guarded by
        # is_spdd_reasons_active, and that helper returns False on an empty
        # repo. So the inactive code path produces zero new lines.
        lines: list[str] = ["existing line"]
        baseline = list(lines)

        # Simulate what context.py does: gate on activation.
        # Empty repo_root → inactive.
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            if is_spdd_reasons_active(Path(td)):
                append_spdd_reasons_guidance(lines, "demo-mission", action)

        assert lines == baseline, (
            f"inactive baseline must not gain SPDD/REASONS lines for action={action}; "
            f"got: {lines!r}"
        )
        assert "SPDD/REASONS Guidance" not in "\n".join(lines)


# ---------------------------------------------------------------------------
# Active output and performance (NFR-002)
# ---------------------------------------------------------------------------


class TestCharterContextActive:
    """Active fixture must produce action-scoped REASONS subsection."""

    def setup_method(self) -> None:
        clear_activation_cache()

    @pytest.mark.parametrize("action", ACTIONS)
    def test_active_output_contains_action_subsection(self, action: str) -> None:
        lines: list[str] = []
        append_spdd_reasons_guidance(lines, "demo-mission", action)

        joined = "\n".join(lines)
        assert f"SPDD/REASONS Guidance (action: {action}):" in joined
        # Reference link present.
        assert "kitty-specs/demo-mission/reasons-canvas.md" in joined

    def test_active_specify_contains_requirements_entities(self) -> None:
        lines: list[str] = []
        append_spdd_reasons_guidance(lines, "demo", "specify")
        joined = "\n".join(lines)
        assert "Requirements" in joined
        assert "Entities" in joined

    def test_active_plan_contains_approach_structure(self) -> None:
        lines: list[str] = []
        append_spdd_reasons_guidance(lines, "demo", "plan")
        joined = "\n".join(lines)
        assert "Approach" in joined
        assert "Structure" in joined

    def test_active_tasks_contains_operations_wp_boundaries(self) -> None:
        lines: list[str] = []
        append_spdd_reasons_guidance(lines, "demo", "tasks")
        joined = "\n".join(lines)
        assert "Operations" in joined
        assert "WP boundaries" in joined or "WP " in joined

    def test_active_implement_references_full_canvas(self) -> None:
        lines: list[str] = []
        append_spdd_reasons_guidance(lines, "demo", "implement")
        joined = "\n".join(lines)
        # All seven canonical canvas section names (REASONS) MUST appear in
        # the implement bullets — Requirements, Entities, Approach, Structure,
        # Operations, Norms, Safeguards. These match FR-005, the canvas
        # template, DIRECTIVE_038, and docs/doctrine/spdd-reasons.md.
        for token in (
            "Requirements",
            "Entities",
            "Approach",
            "Structure",
            "Operations",
            "Norms",
            "Safeguards",
        ):
            assert token in joined, f"implement guidance missing canonical token {token!r}"

    def test_active_implement_uses_canonical_section_names(self) -> None:
        """Locked-in regression check: legacy non-canonical names must NOT appear."""
        lines: list[str] = []
        append_spdd_reasons_guidance(lines, "demo", "implement")
        joined = "\n".join(lines)
        # Drift guard: the pre-fix bullets used "Non-functionals" / "Steps".
        # Those names are not part of the canonical REASONS canvas.
        assert "Non-functionals" not in joined
        assert "Non-functional" not in joined

    def test_active_review_contains_comparison_surface(self) -> None:
        lines: list[str] = []
        append_spdd_reasons_guidance(lines, "demo", "review")
        joined = "\n".join(lines)
        # Review canvas comparison surface is the canonical R, O, N, S
        # quartet — Requirements, Operations, Norms, Safeguards.
        for token in ("Requirements", "Operations", "Norms", "Safeguards"):
            assert token in joined, f"review guidance missing canonical token {token!r}"
        # Legacy non-canonical names must NOT leak into the review surface.
        assert "Non-functionals" not in joined

    def test_performance_under_2s_active(self, tmp_path: Path) -> None:
        # NFR-002: one render call must complete well under 2s. The renderer
        # is in-memory and trivially fast; this guards against accidental
        # algorithmic regressions (e.g. someone adding a YAML round-trip).
        _write_governance(
            tmp_path,
            "doctrine:\n"
            "  selected_paradigms:\n"
            "    - structured-prompt-driven-development\n"
            "  selected_directives: []\n"
            "  available_tools: []\n",
        )
        clear_activation_cache()

        start = time.perf_counter()
        for action in ACTIONS:
            assert is_spdd_reasons_active(tmp_path) is True
            lines: list[str] = []
            append_spdd_reasons_guidance(lines, "demo-mission", action)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"active render budget exceeded: {elapsed:.3f}s"


# ---------------------------------------------------------------------------
# T010 — paradigm round-trip verification
# ---------------------------------------------------------------------------


class TestParadigmRoundTrip:
    """Verify that a charter selection of paradigm flows through to governance.yaml.

    This is a smoke test for the existing synthesizer plumbing, not a change
    in T010. ``selected_paradigms`` is already a first-class field on
    ``DoctrineSelectionConfig`` (src/charter/schemas.py) and is wired through
    interview → extractor → governance.yaml. The check below confirms the
    activation helper sees the paradigm when written to governance.yaml.
    """

    def setup_method(self) -> None:
        clear_activation_cache()

    def test_paradigm_in_governance_activates_pack(self, tmp_path: Path) -> None:
        from charter.charter_yaml_io import save_charter_yaml
        from charter.schemas import DoctrineSelectionConfig, GovernanceConfig

        # Build a minimal GovernanceConfig with the paradigm selected, then
        # write it into charter.yaml's governance: section the way the
        # hand-authored charter would carry it.
        gov = GovernanceConfig(
            doctrine=DoctrineSelectionConfig(
                selected_paradigms=["structured-prompt-driven-development"],
            )
        )
        charter_yaml_path = _charter_yaml_path(tmp_path)
        save_charter_yaml(
            charter_yaml_path, {"governance": gov.model_dump(mode="json")}
        )

        assert is_spdd_reasons_active(tmp_path) is True


# ---------------------------------------------------------------------------
# D-2 — selected_tactics round-trip through the charter pipeline
# ---------------------------------------------------------------------------


class TestSelectedTacticsRoundTrip:
    """End-to-end coverage for tactic-only activation (FR-007, contracts/activation.md cases 4-5).

    Pre-fix, ``selected_tactics`` was read by the activation helper but never
    written by the charter compiler. This test exercises the full pipeline:
    config activation carrying a single tactic -> compiled charter.md ->
    re-extracted governance.yaml -> activation helper recognising the pack.

    WP03 re-pin (T028): the activation input moved from
    ``interview.selected_tactics`` (``apply_answer_overrides``) to
    ``config.activated_tactics`` (a ``PackContext``) -- WP02 (FR-001/FR-002)
    retired ``interview.selected_*`` as an activation source, so driving this
    scenario through the interview no longer reaches the compiler's
    activation selection at all. The underlying invariant this test protects
    -- a single directly-activated tactic reaches the markdown Governance
    Activation block, round-trips through extraction into governance.yaml,
    and the SPDD activation helper recognises it from disk -- is still real
    and still worth pinning, so it is re-pinned rather than deleted.
    """

    def setup_method(self) -> None:
        clear_activation_cache()

    def test_tactic_only_selection_round_trips_to_governance_and_activates(
        self, tmp_path: Path
    ) -> None:
        from charter.charter_yaml_io import save_charter_yaml
        from charter.compiler import compile_charter
        from charter.interview import default_interview
        from charter.pack_context import PackContext
        from charter.schemas import DoctrineSelectionConfig, GovernanceConfig

        # 1. Build a PackContext that activates ONLY the canvas-fill tactic
        #    (every other kind explicitly narrowed to empty so nothing else
        #    contributes a selector -- isolates this one activation path).
        pack_context = PackContext(
            activated_kinds=frozenset(
                {
                    "directives",
                    "tactics",
                    "styleguides",
                    "toolguides",
                    "paradigms",
                    "procedures",
                    "agent_profiles",
                    "mission_step_contracts",
                }
            ),
            activated_mission_types=frozenset({"software-dev"}),
            pack_roots=(),
            org_pack_names=(),
            repo_root=tmp_path,
            activated_directives=frozenset(),
            activated_tactics=frozenset({"reasons-canvas-fill"}),
            activated_styleguides=frozenset(),
            activated_toolguides=frozenset(),
            activated_paradigms=frozenset(),
            activated_procedures=frozenset(),
            activated_agent_profiles=frozenset(),
        )
        interview = default_interview(mission="software-dev")

        # 2. Compile the charter — selected_tactics must reach the markdown
        #    Governance Activation block AND the CompiledCharter dataclass.
        compiled = compile_charter(mission="software-dev", interview=interview, pack_context=pack_context)
        assert "reasons-canvas-fill" in compiled.selected_tactics
        assert "selected_tactics: [reasons-canvas-fill]" in compiled.markdown

        # 3. WP02 (charter-deadcode-noop-campsite): charter.extractor is
        #    retired, so the round-trip is reconstructed directly from the
        #    already-available ``compiled`` selection fields instead of
        #    re-parsing ``compiled.markdown`` via ``Extractor().extract()``
        #    -- this is the same data the extractor used to scrape back out
        #    of the rendered markdown.
        governance = GovernanceConfig(
            doctrine=DoctrineSelectionConfig(
                selected_paradigms=compiled.selected_paradigms,
                selected_directives=compiled.selected_directives,
                selected_tactics=compiled.selected_tactics,
                available_tools=compiled.available_tools,
                template_set=compiled.template_set,
            )
        )
        assert "reasons-canvas-fill" in governance.doctrine.selected_tactics

        # 4. Write charter.yaml's governance: section the way the
        #    hand-authored charter would carry it, then let the activation
        #    helper read it back from disk.
        charter_yaml_path = _charter_yaml_path(tmp_path)
        save_charter_yaml(
            charter_yaml_path,
            {"governance": governance.model_dump(mode="json")},
        )

        clear_activation_cache()
        assert is_spdd_reasons_active(tmp_path) is True

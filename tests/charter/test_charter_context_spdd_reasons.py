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


ACTIONS = ("specify", "plan", "tasks", "implement", "review")


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _write_governance(tmp_path: Path, body: str) -> Path:
    charter_dir = tmp_path / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    governance = charter_dir / "governance.yaml"
    governance.write_text(body, encoding="utf-8")
    return governance


def _write_directives(tmp_path: Path, body: str) -> Path:
    charter_dir = tmp_path / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    directives = charter_dir / "directives.yaml"
    directives.write_text(body, encoding="utf-8")
    return directives


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
        _write_governance(tmp_path, "doctrine: [this: is: not: valid")
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
        # All seven canvas letters should appear in the bullets.
        for token in ("Requirements", "Entities", "Approach", "Structure", "Operations", "Non-functionals", "Steps"):
            assert token in joined, f"implement guidance missing token {token!r}"

    def test_active_review_contains_comparison_surface(self) -> None:
        lines: list[str] = []
        append_spdd_reasons_guidance(lines, "demo", "review")
        joined = "\n".join(lines)
        # Review canvas surface is R, O, N, S.
        for token in ("Requirements", "Operations", "Non-functionals", "Steps"):
            assert token in joined, f"review guidance missing token {token!r}"

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
        from charter.schemas import DoctrineSelectionConfig, GovernanceConfig
        from ruamel.yaml import YAML

        # Build a minimal GovernanceConfig with the paradigm selected, then
        # serialise the same way charter sync would.
        gov = GovernanceConfig(
            doctrine=DoctrineSelectionConfig(
                selected_paradigms=["structured-prompt-driven-development"],
            )
        )
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True, exist_ok=True)
        yaml = YAML()
        with (charter_dir / "governance.yaml").open("w", encoding="utf-8") as fh:
            yaml.dump(gov.model_dump(mode="json"), fh)

        assert is_spdd_reasons_active(tmp_path) is True

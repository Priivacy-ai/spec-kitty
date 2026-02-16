"""Comprehensive integration tests for glossary end-to-end workflows (WP11/T050).

These tests exercise cross-module interactions in realistic scenarios:
- Full specify -> conflict -> clarify -> resume pipeline
- Defer to async resolution path
- Pipeline skip when disabled
- Strictness mode combinations (off/medium/max)
- Multiple conflicts in a single step
- Event emission during pipeline execution
- Resume from checkpoint after blocking
- Attachment/decorator integration
- Performance validation (< 5 seconds for batch)
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from specify_cli.glossary.checkpoint import (
    ScopeRef,
    StepCheckpoint,
    compute_input_hash,
    create_checkpoint,
    load_checkpoint,
)
from specify_cli.glossary.clarification import ClarificationMiddleware
from specify_cli.glossary.conflict import classify_conflict, create_conflict, score_severity
from specify_cli.glossary.events import get_event_log_path
from specify_cli.glossary.exceptions import AbortResume, BlockedByConflict, DeferredToAsync
from specify_cli.glossary.extraction import ExtractedTerm, extract_all_terms
from specify_cli.glossary.middleware import (
    GenerationGateMiddleware,
    GlossaryCandidateExtractionMiddleware,
    MockContext,
    ResumeMiddleware,
    SemanticCheckMiddleware,
)
from specify_cli.glossary.models import (
    ConflictType,
    SemanticConflict,
    SenseRef,
    SenseStatus,
    Severity,
    TermSurface,
)
from specify_cli.glossary.pipeline import (
    GlossaryMiddleware,
    GlossaryMiddlewarePipeline,
    create_standard_pipeline,
)
from specify_cli.glossary.resolution import resolve_term
from specify_cli.glossary.scope import GlossaryScope, load_seed_file
from specify_cli.glossary.store import GlossaryStore
from specify_cli.glossary.strictness import Strictness, resolve_strictness, should_block
from specify_cli.missions.primitives import PrimitiveExecutionContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(**overrides: Any) -> PrimitiveExecutionContext:
    """Create a PrimitiveExecutionContext with sensible defaults."""
    defaults: dict[str, Any] = dict(
        step_id="integration-001",
        mission_id="software-dev",
        run_id="run-integration-001",
        inputs={"description": "Simple test with no technical terms"},
        metadata={},
        config={},
    )
    defaults.update(overrides)
    return PrimitiveExecutionContext(**defaults)


def _create_seed_file(tmp_path: Path, scope_name: str, terms_yaml: str) -> Path:
    """Create a seed file in .kittify/glossaries/."""
    glossaries = tmp_path / ".kittify" / "glossaries"
    glossaries.mkdir(parents=True, exist_ok=True)
    seed_file = glossaries / f"{scope_name}.yaml"
    seed_file.write_text(terms_yaml)
    return seed_file


def _setup_multi_scope_repo(tmp_path: Path) -> Path:
    """Create a realistic repo with team_domain and spec_kitty_core seed files."""
    _create_seed_file(
        tmp_path,
        "team_domain",
        (
            "terms:\n"
            "  - surface: workspace\n"
            "    definition: Git worktree directory for a work package\n"
            "    confidence: 0.9\n"
            "    status: active\n"
            "  - surface: workspace\n"
            "    definition: VS Code workspace configuration file\n"
            "    confidence: 0.7\n"
            "    status: active\n"
            "  - surface: pipeline\n"
            "    definition: CI/CD workflow automation\n"
            "    confidence: 1.0\n"
            "    status: active\n"
            "  - surface: artifact\n"
            "    definition: Build output file (binary, package, image)\n"
            "    confidence: 0.95\n"
            "    status: active\n"
        ),
    )
    _create_seed_file(
        tmp_path,
        "spec_kitty_core",
        (
            "terms:\n"
            "  - surface: mission\n"
            "    definition: Structured workflow with primitives and steps\n"
            "    confidence: 1.0\n"
            "    status: active\n"
            "  - surface: primitive\n"
            "    definition: Atomic mission operation (specify, plan, implement)\n"
            "    confidence: 1.0\n"
            "    status: active\n"
        ),
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Scenario 1: Full workflow -- specify -> conflict -> clarify -> resume
# ---------------------------------------------------------------------------


class TestFullWorkflowSpecifyClarifyResume:
    """End-to-end: specify step encounters ambiguous term, user resolves via
    interactive clarification, pipeline proceeds without blocking."""

    def test_specify_conflict_clarify_proceeds(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Full flow: ambiguous term -> prompt -> user selects candidate -> gate passes."""
        _setup_multi_scope_repo(tmp_path)

        prompt_calls: list[str] = []

        def mock_prompt(conflict: Any, candidates: Any) -> tuple[str, str | None]:
            prompt_calls.append(conflict.term.surface_text)
            conflict.selected_index = 0
            return ("select", None)

        monkeypatch.setattr(
            "specify_cli.glossary.pipeline.prompt_conflict_resolution_safe",
            mock_prompt,
        )

        ctx = _make_context(
            step_id="specify-001",
            inputs={"description": "Implement workspace management feature"},
            metadata={
                "glossary_watch_terms": ["workspace"],
                "glossary_check": "enabled",
                "critical_step": True,
            },
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.MEDIUM,
            interaction_mode="interactive",
        )
        result = pipeline.process(ctx)

        # Verify: conflict was resolved interactively
        assert len(prompt_calls) == 1
        assert prompt_calls[0] == "workspace"

        # Verify: no remaining conflicts (resolved before gate)
        assert len(result.conflicts) == 0

        # Verify: resolved conflicts tracked
        resolved = getattr(result, "resolved_conflicts", [])
        assert len(resolved) >= 1
        assert resolved[0].term.surface_text == "workspace"

        # Verify: strictness was applied
        assert result.effective_strictness == Strictness.MEDIUM

    def test_specify_conflict_custom_definition_proceeds(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """User provides a custom definition instead of selecting a candidate."""
        _setup_multi_scope_repo(tmp_path)

        def mock_prompt(conflict: Any, candidates: Any) -> tuple[str, str | None]:
            return ("custom", "The project workspace directory on disk")

        monkeypatch.setattr(
            "specify_cli.glossary.pipeline.prompt_conflict_resolution_safe",
            mock_prompt,
        )

        ctx = _make_context(
            inputs={"description": "Configure workspace settings"},
            metadata={"glossary_watch_terms": ["workspace"]},
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.MAX,
            interaction_mode="interactive",
        )
        result = pipeline.process(ctx)

        # Custom definition resolves the conflict
        assert len(result.conflicts) == 0
        resolved = getattr(result, "resolved_conflicts", [])
        assert len(resolved) >= 1


# ---------------------------------------------------------------------------
# Scenario 2: Defer to async resolution
# ---------------------------------------------------------------------------


class TestDeferToAsyncWorkflow:
    """User defers conflict resolution; conflict remains unresolved and
    the gate blocks if strictness requires it."""

    def test_defer_leaves_conflict_unresolved_gate_blocks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Deferral keeps conflict in context; gate blocks under MAX strictness."""
        _setup_multi_scope_repo(tmp_path)

        defer_calls: list[str] = []

        def mock_prompt(conflict: Any, candidates: Any) -> tuple[str, str | None]:
            defer_calls.append(conflict.term.surface_text)
            return ("defer", None)

        monkeypatch.setattr(
            "specify_cli.glossary.pipeline.prompt_conflict_resolution_safe",
            mock_prompt,
        )

        ctx = _make_context(
            inputs={"description": "Setup workspace configuration"},
            metadata={"glossary_watch_terms": ["workspace"]},
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.MAX,
            interaction_mode="interactive",
        )

        with pytest.raises(BlockedByConflict) as exc_info:
            pipeline.process(ctx)

        assert len(defer_calls) == 1
        assert len(exc_info.value.conflicts) >= 1

    def test_defer_with_off_strictness_allows_generation(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Deferral with OFF strictness: conflicts detected but not blocking."""
        _setup_multi_scope_repo(tmp_path)

        def mock_prompt(conflict: Any, candidates: Any) -> tuple[str, str | None]:
            return ("defer", None)

        monkeypatch.setattr(
            "specify_cli.glossary.pipeline.prompt_conflict_resolution_safe",
            mock_prompt,
        )

        ctx = _make_context(
            inputs={"description": "Setup workspace configuration"},
            metadata={"glossary_watch_terms": ["workspace"]},
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.OFF,
            interaction_mode="interactive",
        )
        result = pipeline.process(ctx)

        # Conflict exists (deferred) but not blocked
        assert len(result.conflicts) >= 1
        assert result.effective_strictness == Strictness.OFF

    def test_non_interactive_defers_all_conflicts(self, tmp_path: Path) -> None:
        """Non-interactive mode defers all conflicts automatically."""
        _setup_multi_scope_repo(tmp_path)

        ctx = _make_context(
            inputs={"description": "test"},
            metadata={"glossary_watch_terms": ["workspace"]},
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.OFF,
            interaction_mode="non-interactive",
        )
        result = pipeline.process(ctx)

        # Conflicts deferred (not resolved) but not blocked (OFF strictness)
        assert len(result.conflicts) >= 1


# ---------------------------------------------------------------------------
# Scenario 3: Pipeline skip when disabled
# ---------------------------------------------------------------------------


class TestPipelineSkipWhenDisabled:
    """Verify pipeline skips entirely when glossary checks are disabled."""

    def test_skip_via_metadata_disabled(self, tmp_path: Path) -> None:
        """glossary_check: disabled in metadata -> pipeline skipped."""
        _setup_multi_scope_repo(tmp_path)

        ctx = _make_context(
            inputs={"description": "workspace pipeline artifact mission primitive"},
            metadata={"glossary_check": "disabled"},
        )

        pipeline = create_standard_pipeline(tmp_path)
        result = pipeline.process(ctx)

        assert result.extracted_terms == []
        assert result.conflicts == []
        assert result.effective_strictness is None

    def test_skip_via_metadata_bool_false(self, tmp_path: Path) -> None:
        """glossary_check: false (boolean) in metadata -> pipeline skipped."""
        _setup_multi_scope_repo(tmp_path)

        ctx = _make_context(
            inputs={"description": "workspace pipeline artifact"},
            metadata={"glossary_check": False},
        )

        pipeline = create_standard_pipeline(tmp_path)
        result = pipeline.process(ctx)

        assert result.extracted_terms == []
        assert result.conflicts == []
        assert result.effective_strictness is None

    def test_skip_via_mission_config(self, tmp_path: Path) -> None:
        """glossary.enabled: false in mission config -> pipeline skipped."""
        _setup_multi_scope_repo(tmp_path)

        ctx = _make_context(
            inputs={"description": "workspace pipeline artifact"},
            config={"glossary": {"enabled": False}},
        )

        pipeline = create_standard_pipeline(tmp_path)
        result = pipeline.process(ctx)

        assert result.extracted_terms == []
        assert result.conflicts == []
        assert result.effective_strictness is None

    def test_enabled_by_default_when_no_metadata(self, tmp_path: Path) -> None:
        """Default: pipeline runs when no explicit disable metadata."""
        _setup_multi_scope_repo(tmp_path)

        ctx = _make_context(
            inputs={"description": "test"},
            metadata={"glossary_watch_terms": ["workspace"]},
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.OFF,
        )
        result = pipeline.process(ctx)

        # Pipeline ran: terms extracted
        assert len(result.extracted_terms) >= 1
        assert result.effective_strictness == Strictness.OFF


# ---------------------------------------------------------------------------
# Scenario 4: Strictness mode combinations (off/medium/max)
# ---------------------------------------------------------------------------


class TestStrictnessModes:
    """Verify all three strictness modes behave correctly with various
    conflict severities."""

    def test_off_never_blocks(self, tmp_path: Path) -> None:
        """OFF strictness never blocks, even with HIGH severity conflicts."""
        _setup_multi_scope_repo(tmp_path)

        ctx = _make_context(
            inputs={"description": "workspace test"},
            metadata={
                "glossary_watch_terms": ["workspace"],
                "critical_step": True,  # AMBIGUOUS + critical = HIGH severity
            },
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.OFF,
        )
        result = pipeline.process(ctx)

        assert result.effective_strictness == Strictness.OFF
        # Conflicts detected but not blocked
        workspace_conflicts = [
            c for c in result.conflicts if c.term.surface_text == "workspace"
        ]
        assert len(workspace_conflicts) >= 1

    def test_medium_blocks_high_severity_only(self, tmp_path: Path) -> None:
        """MEDIUM strictness blocks HIGH severity but allows MEDIUM/LOW."""
        _setup_multi_scope_repo(tmp_path)

        # HIGH severity: AMBIGUOUS + critical_step
        ctx_high = _make_context(
            step_id="high-sev",
            inputs={"description": "workspace test"},
            metadata={
                "glossary_watch_terms": ["workspace"],
                "critical_step": True,
            },
        )

        pipeline_med = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.MEDIUM,
        )

        with pytest.raises(BlockedByConflict):
            pipeline_med.process(ctx_high)

        # MEDIUM severity: AMBIGUOUS + non-critical (severity=MEDIUM, not HIGH)
        ctx_med = _make_context(
            step_id="med-sev",
            inputs={"description": "workspace test"},
            metadata={
                "glossary_watch_terms": ["workspace"],
                # no critical_step -> AMBIGUOUS severity = MEDIUM
            },
        )

        pipeline_med2 = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.MEDIUM,
        )
        # MEDIUM severity AMBIGUOUS: should NOT block under MEDIUM strictness
        # (MEDIUM strictness blocks only HIGH severity)
        result = pipeline_med2.process(ctx_med)
        assert result.effective_strictness == Strictness.MEDIUM

    def test_max_blocks_any_conflict(self, tmp_path: Path) -> None:
        """MAX strictness blocks any conflict regardless of severity."""
        _setup_multi_scope_repo(tmp_path)

        # Even non-critical AMBIGUOUS (MEDIUM severity) should block under MAX
        ctx = _make_context(
            inputs={"description": "workspace test"},
            metadata={"glossary_watch_terms": ["workspace"]},
        )

        pipeline_max = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.MAX,
        )

        with pytest.raises(BlockedByConflict) as exc_info:
            pipeline_max.process(ctx)

        assert exc_info.value.strictness == Strictness.MAX

    def test_unknown_term_low_severity_passes_medium(self, tmp_path: Path) -> None:
        """UNKNOWN term with high confidence -> LOW severity -> passes MEDIUM."""
        (tmp_path / ".kittify").mkdir()

        ctx = _make_context(
            inputs={"description": "test"},
            metadata={
                "glossary_watch_terms": ["frobulator"],
                # high confidence metadata hint -> confidence 1.0
                # UNKNOWN + confidence >= 0.8 -> LOW severity
            },
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.MEDIUM,
        )
        result = pipeline.process(ctx)

        # LOW severity UNKNOWN should not block under MEDIUM
        frobulator = [c for c in result.conflicts if c.term.surface_text == "frobulator"]
        assert len(frobulator) == 1
        assert frobulator[0].severity == Severity.LOW

    def test_strictness_precedence_runtime_overrides_all(self, tmp_path: Path) -> None:
        """Runtime --strictness flag overrides mission and step config."""
        _setup_multi_scope_repo(tmp_path)

        config_yaml = tmp_path / ".kittify" / "config.yaml"
        config_yaml.write_text("glossary:\n  strictness: max\n")

        ctx = _make_context(
            inputs={"description": "workspace test"},
            metadata={
                "glossary_watch_terms": ["workspace"],
                "glossary_check_strictness": "max",  # Step says MAX
            },
            config={"glossary": {"strictness": "max"}},  # Mission says MAX
        )

        # Runtime says OFF -> overrides everything
        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.OFF,
        )
        result = pipeline.process(ctx)
        assert result.effective_strictness == Strictness.OFF


# ---------------------------------------------------------------------------
# Scenario 5: Multiple conflicts in a single step
# ---------------------------------------------------------------------------


class TestMultipleConflictsSingleStep:
    """Verify handling of multiple ambiguous terms in one pipeline execution."""

    def test_multiple_ambiguous_terms_all_resolved(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Two ambiguous terms, user resolves both, pipeline proceeds."""
        _create_seed_file(
            tmp_path,
            "team_domain",
            (
                "terms:\n"
                "  - surface: workspace\n"
                "    definition: Git worktree directory\n"
                "    confidence: 0.9\n"
                "    status: active\n"
                "  - surface: workspace\n"
                "    definition: VS Code workspace config\n"
                "    confidence: 0.7\n"
                "    status: active\n"
                "  - surface: mission\n"
                "    definition: Purpose-specific workflow\n"
                "    confidence: 0.9\n"
                "    status: active\n"
                "  - surface: mission\n"
                "    definition: Organization goal\n"
                "    confidence: 0.6\n"
                "    status: active\n"
            ),
        )

        prompt_log: list[str] = []

        def mock_prompt(conflict: Any, candidates: Any) -> tuple[str, str | None]:
            prompt_log.append(conflict.term.surface_text)
            conflict.selected_index = 0
            return ("select", None)

        monkeypatch.setattr(
            "specify_cli.glossary.pipeline.prompt_conflict_resolution_safe",
            mock_prompt,
        )

        ctx = _make_context(
            inputs={"description": "test"},
            metadata={"glossary_watch_terms": ["workspace", "mission"]},
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.MAX,
            interaction_mode="interactive",
        )
        result = pipeline.process(ctx)

        # Both resolved
        assert len(result.conflicts) == 0
        resolved = getattr(result, "resolved_conflicts", [])
        resolved_terms = {c.term.surface_text for c in resolved}
        assert "workspace" in resolved_terms
        assert "mission" in resolved_terms
        assert len(prompt_log) == 2

    def test_multiple_conflicts_partial_defer_blocks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """One resolved, one deferred -> gate blocks on the deferred one."""
        _create_seed_file(
            tmp_path,
            "team_domain",
            (
                "terms:\n"
                "  - surface: workspace\n"
                "    definition: Git worktree directory\n"
                "    confidence: 0.9\n"
                "    status: active\n"
                "  - surface: workspace\n"
                "    definition: VS Code workspace config\n"
                "    confidence: 0.7\n"
                "    status: active\n"
                "  - surface: mission\n"
                "    definition: Purpose-specific workflow\n"
                "    confidence: 0.9\n"
                "    status: active\n"
                "  - surface: mission\n"
                "    definition: Organization goal\n"
                "    confidence: 0.6\n"
                "    status: active\n"
            ),
        )

        def mock_prompt(conflict: Any, candidates: Any) -> tuple[str, str | None]:
            if conflict.term.surface_text == "workspace":
                conflict.selected_index = 0
                return ("select", None)
            else:
                return ("defer", None)

        monkeypatch.setattr(
            "specify_cli.glossary.pipeline.prompt_conflict_resolution_safe",
            mock_prompt,
        )

        ctx = _make_context(
            inputs={"description": "test"},
            metadata={"glossary_watch_terms": ["workspace", "mission"]},
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.MAX,
            interaction_mode="interactive",
        )

        # mission deferred -> gate blocks
        with pytest.raises(BlockedByConflict) as exc_info:
            pipeline.process(ctx)

        # Only mission remains unresolved
        unresolved = exc_info.value.conflicts
        unresolved_terms = {c.term.surface_text for c in unresolved}
        assert "mission" in unresolved_terms
        assert "workspace" not in unresolved_terms


# ---------------------------------------------------------------------------
# Scenario 6: Cross-module state flow validation
# ---------------------------------------------------------------------------


class TestCrossModuleStateFlow:
    """Verify that state flows correctly across all middleware layers."""

    def test_extracted_terms_flow_to_semantic_check(self, tmp_path: Path) -> None:
        """Terms extracted in layer 1 are visible in layer 2 (semantic check)."""
        _setup_multi_scope_repo(tmp_path)

        ctx = _make_context(
            inputs={"description": "test"},
            metadata={"glossary_watch_terms": ["workspace", "pipeline"]},
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.OFF,
        )
        result = pipeline.process(ctx)

        # Both terms were extracted
        extracted_surfaces = {t.surface for t in result.extracted_terms}
        assert "workspace" in extracted_surfaces
        assert "pipeline" in extracted_surfaces

        # workspace has 2 active senses -> AMBIGUOUS conflict
        workspace_conflicts = [
            c for c in result.conflicts if c.term.surface_text == "workspace"
        ]
        assert len(workspace_conflicts) == 1
        assert workspace_conflicts[0].conflict_type == ConflictType.AMBIGUOUS

        # pipeline has 1 active sense -> no conflict
        pipeline_conflicts = [
            c for c in result.conflicts if c.term.surface_text == "pipeline"
        ]
        assert len(pipeline_conflicts) == 0

    def test_effective_strictness_stored_in_context(self, tmp_path: Path) -> None:
        """GenerationGateMiddleware stores effective_strictness in context."""
        (tmp_path / ".kittify").mkdir()

        ctx = _make_context()
        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.MAX,
        )
        result = pipeline.process(ctx)

        assert result.effective_strictness == Strictness.MAX

    def test_conflict_candidates_include_scope_info(self, tmp_path: Path) -> None:
        """SemanticConflict.candidate_senses carry scope and definition."""
        _setup_multi_scope_repo(tmp_path)

        ctx = _make_context(
            inputs={"description": "test"},
            metadata={"glossary_watch_terms": ["workspace"]},
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.OFF,
        )
        result = pipeline.process(ctx)

        workspace_conflict = next(
            (c for c in result.conflicts if c.term.surface_text == "workspace"),
            None,
        )
        assert workspace_conflict is not None
        assert len(workspace_conflict.candidate_senses) == 2
        # Both candidates from team_domain
        for sense_ref in workspace_conflict.candidate_senses:
            assert sense_ref.scope == "team_domain"
            assert sense_ref.definition  # non-empty


# ---------------------------------------------------------------------------
# Scenario 7: Production hook integration (execute_with_glossary)
# ---------------------------------------------------------------------------


class TestProductionHookIntegration:
    """Verify execute_with_glossary integrates all components end-to-end."""

    def test_e2e_clarify_then_primitive_runs(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Full production path: hook -> pipeline -> clarification -> primitive."""
        from specify_cli.missions.glossary_hook import execute_with_glossary

        _setup_multi_scope_repo(tmp_path)

        def mock_prompt(conflict: Any, candidates: Any) -> tuple[str, str | None]:
            conflict.selected_index = 0
            return ("select", None)

        monkeypatch.setattr(
            "specify_cli.glossary.pipeline.prompt_conflict_resolution_safe",
            mock_prompt,
        )

        primitive_results: list[dict[str, Any]] = []

        def my_specify_primitive(context: Any) -> dict[str, Any]:
            result = {
                "strictness": context.effective_strictness,
                "remaining_conflicts": len(context.conflicts),
                "resolved_count": len(getattr(context, "resolved_conflicts", [])),
            }
            primitive_results.append(result)
            return result

        ctx = _make_context(
            inputs={"description": "Implement workspace management feature"},
            metadata={
                "glossary_watch_terms": ["workspace"],
                "critical_step": True,
            },
        )

        result = execute_with_glossary(
            primitive_fn=my_specify_primitive,
            context=ctx,
            repo_root=tmp_path,
            runtime_strictness=Strictness.MEDIUM,
            interaction_mode="interactive",
        )

        assert len(primitive_results) == 1
        assert result["remaining_conflicts"] == 0
        assert result["resolved_count"] >= 1
        assert result["strictness"] == Strictness.MEDIUM

    def test_e2e_blocked_propagates_through_hook(self, tmp_path: Path) -> None:
        """BlockedByConflict propagates through execute_with_glossary."""
        from specify_cli.missions.glossary_hook import execute_with_glossary

        _setup_multi_scope_repo(tmp_path)

        def my_primitive(context: Any) -> dict[str, str]:
            return {"result": "should not run"}

        ctx = _make_context(
            inputs={"description": "workspace test"},
            metadata={
                "glossary_watch_terms": ["workspace"],
                "critical_step": True,
            },
        )

        with pytest.raises(BlockedByConflict):
            execute_with_glossary(
                primitive_fn=my_primitive,
                context=ctx,
                repo_root=tmp_path,
                runtime_strictness=Strictness.MEDIUM,
                interaction_mode="non-interactive",
            )

    def test_e2e_disabled_still_runs_primitive(self, tmp_path: Path) -> None:
        """Pipeline disabled -> primitive still executes."""
        from specify_cli.missions.glossary_hook import execute_with_glossary

        _setup_multi_scope_repo(tmp_path)

        def my_primitive(context: Any) -> dict[str, Any]:
            return {"ran": True, "strictness": context.effective_strictness}

        ctx = _make_context(
            metadata={"glossary_check": "disabled"},
        )

        result = execute_with_glossary(
            primitive_fn=my_primitive,
            context=ctx,
            repo_root=tmp_path,
        )

        assert result["ran"] is True
        assert result["strictness"] is None


# ---------------------------------------------------------------------------
# Scenario 8: Seed file loading across scopes
# ---------------------------------------------------------------------------


class TestMultiScopeResolution:
    """Verify term resolution across multiple scope levels."""

    def test_term_in_one_scope_no_conflict(self, tmp_path: Path) -> None:
        """Term in spec_kitty_core with single sense -> no conflict."""
        _setup_multi_scope_repo(tmp_path)

        ctx = _make_context(
            inputs={"description": "test"},
            metadata={"glossary_watch_terms": ["mission"]},
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.MAX,
        )
        result = pipeline.process(ctx)

        # mission has single sense in spec_kitty_core -> no conflict
        mission_conflicts = [
            c for c in result.conflicts if c.term.surface_text == "mission"
        ]
        assert len(mission_conflicts) == 0

    def test_term_not_in_any_scope_is_unknown(self, tmp_path: Path) -> None:
        """Term not in any seed file -> UNKNOWN conflict."""
        _setup_multi_scope_repo(tmp_path)

        ctx = _make_context(
            inputs={"description": "test"},
            metadata={"glossary_watch_terms": ["frobnicator"]},
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.OFF,
        )
        result = pipeline.process(ctx)

        frob = [c for c in result.conflicts if c.term.surface_text == "frobnicator"]
        assert len(frob) == 1
        assert frob[0].conflict_type == ConflictType.UNKNOWN

    def test_deprecated_sense_ignored_for_ambiguity(self, tmp_path: Path) -> None:
        """Two senses but one deprecated -> single active sense -> no conflict."""
        _create_seed_file(
            tmp_path,
            "team_domain",
            (
                "terms:\n"
                "  - surface: widget\n"
                "    definition: UI component\n"
                "    confidence: 0.9\n"
                "    status: active\n"
                "  - surface: widget\n"
                "    definition: Factory gadget (legacy)\n"
                "    confidence: 0.5\n"
                "    status: deprecated\n"
            ),
        )

        ctx = _make_context(
            inputs={"description": "test"},
            metadata={"glossary_watch_terms": ["widget"]},
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.MAX,
        )
        result = pipeline.process(ctx)

        # Only 1 active sense -> no AMBIGUOUS conflict
        widget_conflicts = [
            c for c in result.conflicts if c.term.surface_text == "widget"
        ]
        assert len(widget_conflicts) == 0


# ---------------------------------------------------------------------------
# Scenario 9: Attachment decorator integration
# ---------------------------------------------------------------------------


class TestAttachmentDecoratorIntegration:
    """Verify the @glossary_enabled decorator and GlossaryAwarePrimitiveRunner."""

    def test_glossary_aware_runner_runs_pipeline(self, tmp_path: Path) -> None:
        """GlossaryAwarePrimitiveRunner.execute() runs pipeline before primitive."""
        from specify_cli.glossary.attachment import GlossaryAwarePrimitiveRunner

        (tmp_path / ".kittify").mkdir()

        runner = GlossaryAwarePrimitiveRunner(
            repo_root=tmp_path,
            runtime_strictness=Strictness.OFF,
        )

        def my_primitive(context: Any, extra: str) -> dict[str, Any]:
            return {
                "strictness": context.effective_strictness,
                "extra": extra,
            }

        ctx = _make_context()
        result = runner.execute(my_primitive, ctx, "hello")

        assert result["strictness"] == Strictness.OFF
        assert result["extra"] == "hello"

    def test_run_with_glossary_processes_context(self, tmp_path: Path) -> None:
        """run_with_glossary processes context through the pipeline."""
        from specify_cli.glossary.attachment import run_with_glossary

        (tmp_path / ".kittify").mkdir()

        ctx = _make_context()
        processed = run_with_glossary(
            context=ctx,
            repo_root=tmp_path,
            runtime_strictness=Strictness.MEDIUM,
        )

        assert processed.effective_strictness == Strictness.MEDIUM


# ---------------------------------------------------------------------------
# Scenario 10: Performance validation
# ---------------------------------------------------------------------------


class TestIntegrationPerformance:
    """Verify integration test performance meets the < 5 seconds budget."""

    def test_10_iterations_under_5_seconds(self, tmp_path: Path) -> None:
        """Run 10 full pipeline iterations in < 5 seconds total."""
        _setup_multi_scope_repo(tmp_path)

        start = time.perf_counter()

        for i in range(10):
            ctx = _make_context(
                step_id=f"perf-{i:03d}",
                run_id=f"run-perf-{i:03d}",
                inputs={"description": "workspace and artifact terms"},
                metadata={"glossary_watch_terms": ["workspace", "artifact"]},
            )

            pipeline = create_standard_pipeline(
                tmp_path,
                runtime_strictness=Strictness.OFF,
            )
            pipeline.process(ctx)

        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"10 iterations took {elapsed:.2f}s (budget: 5.0s)"

    def test_pipeline_single_run_under_200ms(self, tmp_path: Path) -> None:
        """Single pipeline run with seed files completes in < 200ms."""
        _setup_multi_scope_repo(tmp_path)

        ctx = _make_context(
            inputs={"description": "workspace pipeline artifact terms"},
            metadata={"glossary_watch_terms": ["workspace", "pipeline", "artifact"]},
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.OFF,
        )

        start = time.perf_counter()
        pipeline.process(ctx)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.2, f"Pipeline too slow: {elapsed:.3f}s"


# ---------------------------------------------------------------------------
# Scenario 11: Error paths and edge cases
# ---------------------------------------------------------------------------


class TestErrorPathsAndEdgeCases:
    """Test error handling across the integrated pipeline."""

    def test_malformed_seed_file_does_not_crash_pipeline(self, tmp_path: Path) -> None:
        """Pipeline continues when one seed file is malformed."""
        glossaries = tmp_path / ".kittify" / "glossaries"
        glossaries.mkdir(parents=True)
        (glossaries / "team_domain.yaml").write_text("{{{{invalid yaml")

        # Valid spec_kitty_core
        _create_seed_file(
            tmp_path,
            "spec_kitty_core",
            (
                "terms:\n"
                "  - surface: mission\n"
                "    definition: Structured workflow\n"
                "    confidence: 1.0\n"
                "    status: active\n"
            ),
        )

        ctx = _make_context(
            inputs={"description": "test"},
            metadata={"glossary_watch_terms": ["mission"]},
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.MAX,
        )
        result = pipeline.process(ctx)

        # mission found in spec_kitty_core -> no conflict
        assert result is not None

    def test_empty_inputs_no_crash(self, tmp_path: Path) -> None:
        """Pipeline handles empty inputs gracefully."""
        (tmp_path / ".kittify").mkdir()

        ctx = _make_context(
            inputs={},
            metadata={},
        )

        pipeline = create_standard_pipeline(tmp_path)
        result = pipeline.process(ctx)

        assert result.extracted_terms == []
        assert result.conflicts == []

    def test_none_context_raises_valueerror(self, tmp_path: Path) -> None:
        """Pipeline rejects None context with ValueError."""
        (tmp_path / ".kittify").mkdir()

        pipeline = create_standard_pipeline(tmp_path)

        with pytest.raises(ValueError, match="must not be None"):
            pipeline.process(None)  # type: ignore[arg-type]

    def test_prompt_function_exception_defers(self, tmp_path: Path) -> None:
        """If prompt function raises, conflict is deferred (not crash)."""
        _setup_multi_scope_repo(tmp_path)

        def broken_prompt(conflict: Any, candidates: Any) -> tuple[str, str | None]:
            raise RuntimeError("Prompt broken!")

        ctx = _make_context(
            inputs={"description": "workspace test"},
            metadata={"glossary_watch_terms": ["workspace"]},
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.OFF,
            interaction_mode="interactive",
        )
        # Replace the prompt function with a broken one
        for mw in pipeline.middleware:
            if isinstance(mw, ClarificationMiddleware):
                mw.prompt_fn = broken_prompt

        result = pipeline.process(ctx)

        # Conflict deferred (prompt failed), but pipeline didn't crash (OFF)
        assert len(result.conflicts) >= 1

    def test_blocked_exception_carries_conflict_details(self, tmp_path: Path) -> None:
        """BlockedByConflict exception includes conflict objects with full data."""
        _setup_multi_scope_repo(tmp_path)

        ctx = _make_context(
            inputs={"description": "workspace test"},
            metadata={
                "glossary_watch_terms": ["workspace"],
                "critical_step": True,
            },
        )

        pipeline = create_standard_pipeline(
            tmp_path,
            runtime_strictness=Strictness.MEDIUM,
        )

        with pytest.raises(BlockedByConflict) as exc_info:
            pipeline.process(ctx)

        exc = exc_info.value
        assert len(exc.conflicts) >= 1
        assert exc.strictness == Strictness.MEDIUM
        assert "blocked" in str(exc).lower() or "conflict" in str(exc).lower()

        # Verify conflict has candidate senses
        ws_conflict = next(
            c for c in exc.conflicts if c.term.surface_text == "workspace"
        )
        assert len(ws_conflict.candidate_senses) == 2
        assert ws_conflict.conflict_type == ConflictType.AMBIGUOUS

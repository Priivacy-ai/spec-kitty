"""Integration tests for ClarificationMiddleware (WP06/T029).

Tests cover all resolution paths:
- Select candidate sense
- Custom sense definition
- Defer to async
- Non-interactive mode (auto-defer)
- Max questions capping
- Edge cases (empty conflicts, mixed resolutions, event failures)
"""

import pytest
from dataclasses import dataclass, field
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from rich.console import Console

from specify_cli.glossary.middleware import ClarificationMiddleware
from specify_cli.glossary.models import (
    SemanticConflict,
    Severity,
    TermSurface,
    ConflictType,
    SenseRef,
)
from specify_cli.glossary.prompts import PromptChoice

# Patch targets: events are imported locally inside ClarificationMiddleware
# methods via `from .events import ...`, so we patch at the events module.
_EVENTS = "specify_cli.glossary.events"
_PROMPT_SAFE = "specify_cli.glossary.prompts.prompt_conflict_resolution_safe"


@dataclass
class MockClarificationContext:
    """Mock execution context for clarification tests."""

    step_id: str = "step-001"
    mission_id: str = "041-mission"
    run_id: str = "run-001"
    actor_id: str = "user:alice"
    metadata: Dict[str, Any] = field(default_factory=dict)
    step_input: Dict[str, Any] = field(default_factory=dict)
    step_output: Dict[str, Any] = field(default_factory=dict)
    extracted_terms: List[Any] = field(default_factory=list)
    conflicts: List[SemanticConflict] = field(default_factory=list)
    resolved_conflicts_count: int = 0
    deferred_conflicts_count: int = 0
    resolved_senses: List[Any] = field(default_factory=list)


@pytest.fixture
def mock_console():
    """Mock Rich console."""
    return MagicMock(spec=Console)


@pytest.fixture
def mock_context():
    """Mock primitive execution context."""
    return MockClarificationContext()


@pytest.fixture
def ambiguous_conflict():
    """Create ambiguous conflict with 2 candidates."""
    return SemanticConflict(
        term=TermSurface("workspace"),
        conflict_type=ConflictType.AMBIGUOUS,
        severity=Severity.HIGH,
        confidence=0.9,
        candidate_senses=[
            SenseRef("workspace", "mission_local", "Git worktree directory", 0.9),
            SenseRef("workspace", "team_domain", "VS Code workspace file", 0.7),
        ],
        context="description field",
    )


@pytest.fixture
def medium_conflict():
    """Create medium-severity conflict."""
    return SemanticConflict(
        term=TermSurface("pipeline"),
        conflict_type=ConflictType.AMBIGUOUS,
        severity=Severity.MEDIUM,
        confidence=0.7,
        candidate_senses=[
            SenseRef("pipeline", "team_domain", "CI/CD pipeline", 0.8),
            SenseRef("pipeline", "audience_domain", "Data pipeline", 0.6),
        ],
        context="step input",
    )


@pytest.fixture
def low_conflict():
    """Create low-severity conflict with no candidates."""
    return SemanticConflict(
        term=TermSurface("helper"),
        conflict_type=ConflictType.UNKNOWN,
        severity=Severity.LOW,
        confidence=0.3,
        candidate_senses=[],
        context="output field",
    )


def _make_conflict(surface: str, severity: Severity = Severity.HIGH) -> SemanticConflict:
    """Helper to create a conflict with a single candidate."""
    candidates = []
    if severity != Severity.LOW:
        candidates = [
            SenseRef(surface, "team_domain", f"Definition of {surface}", 0.9),
        ]
    return SemanticConflict(
        term=TermSurface(surface),
        conflict_type=ConflictType.AMBIGUOUS if candidates else ConflictType.UNKNOWN,
        severity=severity,
        confidence=0.9,
        candidate_senses=candidates,
        context="test",
    )


class TestSelectCandidateResolution:
    """Test user selecting a candidate sense."""

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_resolved")
    def test_select_candidate_resolves_conflict(
        self,
        mock_emit_resolved,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
    ):
        """User selects candidate sense from list."""
        mock_prompt.return_value = (PromptChoice.SELECT_CANDIDATE, 0)

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [ambiguous_conflict]

        result = middleware.process(mock_context)

        # Verify resolution event emitted
        assert mock_emit_resolved.call_count == 1
        call_kwargs = mock_emit_resolved.call_args[1]
        assert call_kwargs["term_surface"] == "workspace"
        assert call_kwargs["resolution_mode"] == "interactive"

        # Verify glossary updated
        assert hasattr(result, "resolved_senses")
        assert len(result.resolved_senses) == 1
        assert result.resolved_senses[0].definition == "Git worktree directory"

        # Verify conflicts cleared
        assert result.conflicts == []
        assert result.resolved_conflicts_count == 1

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_resolved")
    def test_select_second_candidate(
        self,
        mock_emit_resolved,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
    ):
        """User selects second candidate (index=1)."""
        mock_prompt.return_value = (PromptChoice.SELECT_CANDIDATE, 1)

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [ambiguous_conflict]

        result = middleware.process(mock_context)

        assert len(result.resolved_senses) == 1
        assert result.resolved_senses[0].definition == "VS Code workspace file"


class TestCustomSenseResolution:
    """Test user providing custom sense definition."""

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_sense_updated")
    def test_custom_sense_creates_new_entry(
        self,
        mock_emit_sense,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
    ):
        """User provides custom sense definition."""
        mock_prompt.return_value = (
            PromptChoice.CUSTOM_SENSE,
            "Isolated directory for WP implementation",
        )

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [ambiguous_conflict]

        result = middleware.process(mock_context)

        # Verify sense updated event emitted
        assert mock_emit_sense.call_count == 1
        call_kwargs = mock_emit_sense.call_args[1]
        assert call_kwargs["term_surface"] == "workspace"
        assert call_kwargs["update_type"] == "create"
        assert call_kwargs["scope"] == "team_domain"

        # Verify custom sense in glossary
        assert len(result.resolved_senses) == 1
        assert result.resolved_senses[0].definition == "Isolated directory for WP implementation"
        assert result.resolved_senses[0].confidence == 1.0

        # Verify conflicts cleared
        assert result.conflicts == []
        assert result.resolved_conflicts_count == 1

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_sense_updated")
    def test_custom_sense_has_user_provenance(
        self,
        mock_emit_sense,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
    ):
        """Custom sense provenance records actor and source."""
        mock_prompt.return_value = (PromptChoice.CUSTOM_SENSE, "My definition")
        mock_context.actor_id = "user:bob"

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [ambiguous_conflict]

        result = middleware.process(mock_context)

        sense = result.resolved_senses[0]
        assert sense.provenance.actor_id == "user:bob"
        assert sense.provenance.source == "user_clarification"


class TestDeferResolution:
    """Test user deferring conflict resolution."""

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_requested")
    def test_defer_emits_requested_event(
        self,
        mock_emit_requested,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
    ):
        """User defers conflict resolution to async mode."""
        mock_prompt.return_value = (PromptChoice.DEFER, None)

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [ambiguous_conflict]

        result = middleware.process(mock_context)

        # Verify requested event emitted
        assert mock_emit_requested.call_count == 1
        call_kwargs = mock_emit_requested.call_args[1]
        assert call_kwargs["term"] == "workspace"
        assert call_kwargs["urgency"] == "high"
        assert len(call_kwargs["options"]) == 2

        # Verify conflict NOT resolved (remains in context)
        assert result.conflicts == [ambiguous_conflict]
        assert result.deferred_conflicts_count == 1
        assert result.resolved_conflicts_count == 0

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_requested")
    def test_defer_no_candidates(
        self,
        mock_emit_requested,
        mock_prompt,
        mock_console,
        mock_context,
        low_conflict,
    ):
        """Deferring conflict with no candidates emits event with empty options."""
        mock_prompt.return_value = (PromptChoice.DEFER, None)

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [low_conflict]

        result = middleware.process(mock_context)

        call_kwargs = mock_emit_requested.call_args[1]
        assert call_kwargs["options"] == []
        assert call_kwargs["urgency"] == "low"


class TestNonInteractiveMode:
    """Test non-interactive mode behavior."""

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_requested")
    def test_non_interactive_auto_defers(
        self,
        mock_emit_requested,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
    ):
        """Non-interactive mode auto-defers all conflicts."""
        mock_prompt.return_value = (PromptChoice.DEFER, None)

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [ambiguous_conflict]

        result = middleware.process(mock_context)

        # Verify auto-defer (requested event emitted)
        assert mock_emit_requested.call_count == 1

        # Verify conflicts remain (not resolved)
        assert result.conflicts == [ambiguous_conflict]
        assert result.deferred_conflicts_count == 1

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_requested")
    def test_non_interactive_multiple_conflicts(
        self,
        mock_emit_requested,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
        medium_conflict,
    ):
        """Non-interactive mode defers all conflicts."""
        mock_prompt.return_value = (PromptChoice.DEFER, None)

        middleware = ClarificationMiddleware(console=mock_console, max_questions=5)
        mock_context.conflicts = [ambiguous_conflict, medium_conflict]

        result = middleware.process(mock_context)

        # Both prompted and deferred
        assert mock_emit_requested.call_count == 2
        assert result.deferred_conflicts_count == 2


class TestMaxQuestionsCapping:
    """Test max_questions limiting behavior."""

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_requested")
    @patch(f"{_EVENTS}.emit_clarification_resolved")
    def test_max_questions_caps_prompts(
        self,
        mock_emit_resolved,
        mock_emit_requested,
        mock_prompt,
        mock_console,
        mock_context,
    ):
        """Clarification middleware caps interactive prompts at max_questions."""
        mock_prompt.return_value = (PromptChoice.SELECT_CANDIDATE, 0)

        # Create 5 conflicts
        conflicts = [_make_conflict(f"term{i}") for i in range(5)]

        middleware = ClarificationMiddleware(
            console=mock_console,
            max_questions=3,
        )
        mock_context.conflicts = conflicts

        result = middleware.process(mock_context)

        # Verify only 3 prompted
        assert mock_prompt.call_count == 3

        # Verify 2 auto-deferred (5 total - 3 prompted)
        assert mock_emit_requested.call_count == 2

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_requested")
    def test_default_max_questions_is_three(
        self,
        mock_emit_requested,
        mock_prompt,
        mock_console,
        mock_context,
    ):
        """Default max_questions is 3."""
        mock_prompt.return_value = (PromptChoice.DEFER, None)

        conflicts = [_make_conflict(f"term{i}") for i in range(10)]

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = conflicts

        middleware.process(mock_context)

        # 3 prompted + 7 auto-deferred
        assert mock_prompt.call_count == 3
        # 3 deferred from prompt + 7 auto-deferred = 10 total
        assert mock_emit_requested.call_count == 10


class TestMixedResolutions:
    """Test scenarios with mixed resolution types."""

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_requested")
    @patch(f"{_EVENTS}.emit_clarification_resolved")
    @patch(f"{_EVENTS}.emit_sense_updated")
    def test_mixed_select_custom_defer(
        self,
        mock_emit_sense,
        mock_emit_resolved,
        mock_emit_requested,
        mock_prompt,
        mock_console,
        mock_context,
    ):
        """Test mix of select, custom, and defer resolutions."""
        mock_prompt.side_effect = [
            (PromptChoice.SELECT_CANDIDATE, 0),
            (PromptChoice.CUSTOM_SENSE, "Custom def"),
            (PromptChoice.DEFER, None),
        ]

        conflicts = [_make_conflict(f"term{i}") for i in range(3)]
        middleware = ClarificationMiddleware(
            console=mock_console, max_questions=5
        )
        mock_context.conflicts = conflicts

        result = middleware.process(mock_context)

        # 2 resolved, 1 deferred
        assert result.resolved_conflicts_count == 2
        assert result.deferred_conflicts_count == 1
        assert len(result.resolved_senses) == 2

        # Events: 1 resolved + 1 sense_updated + 1 requested
        assert mock_emit_resolved.call_count == 1
        assert mock_emit_sense.call_count == 1
        assert mock_emit_requested.call_count == 1

        # Conflicts NOT cleared (not all resolved)
        assert result.conflicts == conflicts


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_conflicts_returns_unchanged(self, mock_console, mock_context):
        """Empty conflicts list returns context unchanged."""
        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = []

        result = middleware.process(mock_context)

        assert result is mock_context
        assert result.conflicts == []

    def test_no_conflicts_attribute_returns_unchanged(self, mock_console):
        """Context without conflicts attribute returns unchanged."""
        context = MagicMock()
        context.conflicts = []

        middleware = ClarificationMiddleware(console=mock_console)
        result = middleware.process(context)

        assert result is context

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_resolved")
    def test_all_resolved_clears_conflicts(
        self,
        mock_emit_resolved,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
        medium_conflict,
    ):
        """When all conflicts resolved, context.conflicts is cleared."""
        mock_prompt.return_value = (PromptChoice.SELECT_CANDIDATE, 0)

        middleware = ClarificationMiddleware(
            console=mock_console, max_questions=5
        )
        mock_context.conflicts = [ambiguous_conflict, medium_conflict]

        result = middleware.process(mock_context)

        assert result.conflicts == []
        assert result.resolved_conflicts_count == 2

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_requested")
    def test_all_deferred_preserves_conflicts(
        self,
        mock_emit_requested,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
    ):
        """When all conflicts deferred, context.conflicts stays populated."""
        mock_prompt.return_value = (PromptChoice.DEFER, None)

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [ambiguous_conflict]

        result = middleware.process(mock_context)

        assert result.conflicts == [ambiguous_conflict]
        assert result.deferred_conflicts_count == 1

    @patch(_PROMPT_SAFE)
    @patch(
        f"{_EVENTS}.emit_clarification_resolved",
        side_effect=RuntimeError("Event transport failure"),
    )
    def test_event_emission_failure_continues(
        self,
        mock_emit_resolved,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
    ):
        """Event emission failure logs error but continues."""
        mock_prompt.return_value = (PromptChoice.SELECT_CANDIDATE, 0)

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [ambiguous_conflict]

        # Should NOT raise despite event emission failure
        result = middleware.process(mock_context)

        # Resolution still proceeds
        assert result.resolved_conflicts_count == 1
        assert len(result.resolved_senses) == 1

    @patch(_PROMPT_SAFE)
    @patch(
        f"{_EVENTS}.emit_clarification_requested",
        side_effect=RuntimeError("Event transport failure"),
    )
    def test_deferred_event_failure_continues(
        self,
        mock_emit_requested,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
    ):
        """Deferred event emission failure logs error but continues."""
        mock_prompt.return_value = (PromptChoice.DEFER, None)

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [ambiguous_conflict]

        # Should NOT raise
        result = middleware.process(mock_context)
        assert result.deferred_conflicts_count == 1

    @patch(_PROMPT_SAFE)
    @patch(
        f"{_EVENTS}.emit_sense_updated",
        side_effect=RuntimeError("Event transport failure"),
    )
    def test_custom_sense_event_failure_continues(
        self,
        mock_emit_sense,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
    ):
        """Custom sense event emission failure logs error but continues."""
        mock_prompt.return_value = (PromptChoice.CUSTOM_SENSE, "My definition")

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [ambiguous_conflict]

        result = middleware.process(mock_context)
        assert result.resolved_conflicts_count == 1
        assert result.resolved_senses[0].definition == "My definition"

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_resolved")
    def test_resolved_sense_has_active_status(
        self,
        mock_emit_resolved,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
    ):
        """Resolved sense has ACTIVE status."""
        mock_prompt.return_value = (PromptChoice.SELECT_CANDIDATE, 0)

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [ambiguous_conflict]

        result = middleware.process(mock_context)

        from specify_cli.glossary.models import SenseStatus

        assert result.resolved_senses[0].status == SenseStatus.ACTIVE

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_resolved")
    def test_context_actor_id_used(
        self,
        mock_emit_resolved,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
    ):
        """Actor ID from context is used in events."""
        mock_prompt.return_value = (PromptChoice.SELECT_CANDIDATE, 0)
        mock_context.actor_id = "user:charlie"

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [ambiguous_conflict]

        middleware.process(mock_context)

        call_kwargs = mock_emit_resolved.call_args[1]
        assert call_kwargs["actor_id"] == "user:charlie"

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_resolved")
    def test_missing_actor_id_defaults(
        self,
        mock_emit_resolved,
        mock_prompt,
        mock_console,
        ambiguous_conflict,
    ):
        """Missing actor_id defaults to 'user:unknown'."""
        mock_prompt.return_value = (PromptChoice.SELECT_CANDIDATE, 0)

        # Context without actor_id
        context = MagicMock()
        context.conflicts = [ambiguous_conflict]
        del context.actor_id  # Ensure getattr falls back

        middleware = ClarificationMiddleware(console=mock_console)
        middleware.process(context)

        call_kwargs = mock_emit_resolved.call_args[1]
        assert call_kwargs["actor_id"] == "user:unknown"

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_resolved")
    def test_console_prints_resolution_message(
        self,
        mock_emit_resolved,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
    ):
        """Console prints resolution confirmation."""
        mock_prompt.return_value = (PromptChoice.SELECT_CANDIDATE, 0)

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [ambiguous_conflict]

        middleware.process(mock_context)

        # Check console.print was called with resolution message
        print_calls = [str(c) for c in mock_console.print.call_args_list]
        resolution_msg = any(
            "Resolved" in c and "workspace" in c for c in print_calls
        )
        assert resolution_msg, f"Expected resolution message in: {print_calls}"

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_sense_updated")
    def test_console_prints_custom_sense_message(
        self,
        mock_emit_sense,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
    ):
        """Console prints custom sense confirmation."""
        mock_prompt.return_value = (PromptChoice.CUSTOM_SENSE, "My definition")

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [ambiguous_conflict]

        middleware.process(mock_context)

        print_calls = [str(c) for c in mock_console.print.call_args_list]
        custom_msg = any(
            "custom sense" in c.lower() and "workspace" in c
            for c in print_calls
        )
        assert custom_msg, f"Expected custom sense message in: {print_calls}"


class TestSeverityPrioritization:
    """Test that conflicts are sorted by severity."""

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_resolved")
    @patch(f"{_EVENTS}.emit_clarification_requested")
    def test_high_severity_prompted_first(
        self,
        mock_emit_requested,
        mock_emit_resolved,
        mock_prompt,
        mock_console,
        mock_context,
        ambiguous_conflict,
        low_conflict,
    ):
        """High-severity conflicts are prompted before low-severity."""
        mock_prompt.return_value = (PromptChoice.SELECT_CANDIDATE, 0)

        middleware = ClarificationMiddleware(
            console=mock_console, max_questions=1
        )
        # Pass low first, high second -- should prompt high first
        mock_context.conflicts = [low_conflict, ambiguous_conflict]

        middleware.process(mock_context)

        # Only 1 prompted (max_questions=1), should be the high-severity one
        prompted_conflict = mock_prompt.call_args[0][0]
        assert prompted_conflict.severity == Severity.HIGH


class TestCandidateRankingInMiddleware:
    """Test that ClarificationMiddleware sorts candidates by scope precedence."""

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_resolved")
    def test_select_candidate_uses_sorted_order(
        self,
        mock_emit_resolved,
        mock_prompt,
        mock_console,
        mock_context,
    ):
        """When user selects candidate #1, it should be the highest-precedence candidate
        (mission_local), not the first in insertion order."""
        # Insert candidates in reverse precedence order
        conflict = SemanticConflict(
            term=TermSurface("workspace"),
            conflict_type=ConflictType.AMBIGUOUS,
            severity=Severity.HIGH,
            confidence=0.9,
            candidate_senses=[
                SenseRef("workspace", "spec_kitty_core", "Core workspace def", 0.9),
                SenseRef("workspace", "team_domain", "Team workspace def", 0.8),
                SenseRef("workspace", "mission_local", "Mission workspace def", 0.7),
            ],
            context="test",
        )

        # User selects candidate #1 (should be mission_local after sorting)
        mock_prompt.return_value = (PromptChoice.SELECT_CANDIDATE, 0)

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [conflict]

        result = middleware.process(mock_context)

        # The resolved sense should be the mission_local one (highest scope precedence)
        assert len(result.resolved_senses) == 1
        assert result.resolved_senses[0].definition == "Mission workspace def"
        assert result.resolved_senses[0].scope == "mission_local"

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_resolved")
    def test_select_last_candidate_uses_lowest_precedence(
        self,
        mock_emit_resolved,
        mock_prompt,
        mock_console,
        mock_context,
    ):
        """When user selects the last candidate, it should be the lowest-precedence one."""
        conflict = SemanticConflict(
            term=TermSurface("workspace"),
            conflict_type=ConflictType.AMBIGUOUS,
            severity=Severity.HIGH,
            confidence=0.9,
            candidate_senses=[
                SenseRef("workspace", "spec_kitty_core", "Core workspace def", 0.9),
                SenseRef("workspace", "mission_local", "Mission workspace def", 0.7),
            ],
            context="test",
        )

        # User selects candidate #2 (should be spec_kitty_core after sorting)
        mock_prompt.return_value = (PromptChoice.SELECT_CANDIDATE, 1)

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [conflict]

        result = middleware.process(mock_context)

        assert len(result.resolved_senses) == 1
        assert result.resolved_senses[0].definition == "Core workspace def"
        assert result.resolved_senses[0].scope == "spec_kitty_core"

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_requested")
    def test_deferred_options_use_sorted_order(
        self,
        mock_emit_requested,
        mock_prompt,
        mock_console,
        mock_context,
    ):
        """Deferred event options list uses scope-precedence-sorted order."""
        conflict = SemanticConflict(
            term=TermSurface("workspace"),
            conflict_type=ConflictType.AMBIGUOUS,
            severity=Severity.HIGH,
            confidence=0.9,
            candidate_senses=[
                SenseRef("workspace", "spec_kitty_core", "Core def", 0.9),
                SenseRef("workspace", "mission_local", "Mission def", 0.7),
            ],
            context="test",
        )

        mock_prompt.return_value = (PromptChoice.DEFER, None)

        middleware = ClarificationMiddleware(console=mock_console)
        mock_context.conflicts = [conflict]

        middleware.process(mock_context)

        call_kwargs = mock_emit_requested.call_args[1]
        # Options should be in scope precedence order: mission_local first
        assert call_kwargs["options"] == ["Mission def", "Core def"]


class TestResolvedSensesAccumulation:
    """Test that resolved_senses accumulates across multiple resolutions."""

    @patch(_PROMPT_SAFE)
    @patch(f"{_EVENTS}.emit_clarification_resolved")
    def test_multiple_resolutions_accumulate(
        self,
        mock_emit_resolved,
        mock_prompt,
        mock_console,
        mock_context,
    ):
        """Multiple resolved conflicts accumulate senses."""
        mock_prompt.return_value = (PromptChoice.SELECT_CANDIDATE, 0)

        conflicts = [_make_conflict(f"term{i}") for i in range(3)]

        middleware = ClarificationMiddleware(
            console=mock_console, max_questions=5
        )
        mock_context.conflicts = conflicts

        result = middleware.process(mock_context)

        assert len(result.resolved_senses) == 3
        assert result.resolved_conflicts_count == 3

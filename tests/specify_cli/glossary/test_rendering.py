"""Tests for conflict rendering with Rich (WP06/T025)."""

import pytest
from unittest.mock import MagicMock, call

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from specify_cli.glossary.models import (
    SemanticConflict,
    Severity,
    TermSurface,
    ConflictType,
    SenseRef,
)
from specify_cli.glossary.rendering import (
    render_conflict,
    render_conflict_batch,
    SEVERITY_COLORS,
    SEVERITY_ICONS,
    _get_severity_color,
    _get_severity_icon,
)


@pytest.fixture
def mock_console():
    """Mock Rich console for capturing output."""
    return MagicMock(spec=Console)


@pytest.fixture
def high_conflict():
    """High-severity ambiguous conflict with 2 candidates."""
    return SemanticConflict(
        term=TermSurface("workspace"),
        conflict_type=ConflictType.AMBIGUOUS,
        severity=Severity.HIGH,
        confidence=0.9,
        candidate_senses=[
            SenseRef(
                surface="workspace",
                scope="mission_local",
                definition="Git worktree directory",
                confidence=0.9,
            ),
            SenseRef(
                surface="workspace",
                scope="team_domain",
                definition="VS Code workspace file",
                confidence=0.7,
            ),
        ],
        context="description field",
    )


@pytest.fixture
def medium_conflict():
    """Medium-severity conflict."""
    return SemanticConflict(
        term=TermSurface("pipeline"),
        conflict_type=ConflictType.AMBIGUOUS,
        severity=Severity.MEDIUM,
        confidence=0.7,
        candidate_senses=[
            SenseRef(
                surface="pipeline",
                scope="team_domain",
                definition="CI/CD pipeline",
                confidence=0.8,
            ),
            SenseRef(
                surface="pipeline",
                scope="audience_domain",
                definition="Data processing pipeline",
                confidence=0.6,
            ),
        ],
        context="step input",
    )


@pytest.fixture
def low_conflict():
    """Low-severity conflict."""
    return SemanticConflict(
        term=TermSurface("helper"),
        conflict_type=ConflictType.UNKNOWN,
        severity=Severity.LOW,
        confidence=0.3,
        candidate_senses=[],
        context="output field",
    )


class TestSeverityMappings:
    """Test severity color and icon mappings."""

    def test_high_severity_color(self):
        assert SEVERITY_COLORS[Severity.HIGH] == "red"

    def test_medium_severity_color(self):
        assert SEVERITY_COLORS[Severity.MEDIUM] == "yellow"

    def test_low_severity_color(self):
        assert SEVERITY_COLORS[Severity.LOW] == "blue"

    def test_high_severity_icon(self):
        assert "HIGH" in SEVERITY_ICONS[Severity.HIGH]

    def test_medium_severity_icon(self):
        assert "MEDIUM" in SEVERITY_ICONS[Severity.MEDIUM]

    def test_low_severity_icon(self):
        assert "LOW" in SEVERITY_ICONS[Severity.LOW]


class TestGetSeverityColor:
    """Test _get_severity_color fallback behavior."""

    def test_known_severity(self):
        assert _get_severity_color(Severity.HIGH) == "red"
        assert _get_severity_color(Severity.MEDIUM) == "yellow"
        assert _get_severity_color(Severity.LOW) == "blue"

    def test_all_enum_values_mapped(self):
        """Every Severity enum member must have a mapping."""
        for sev in Severity:
            color = _get_severity_color(sev)
            assert color in ("red", "yellow", "blue")


class TestGetSeverityIcon:
    """Test _get_severity_icon fallback behavior."""

    def test_known_severity(self):
        assert "HIGH" in _get_severity_icon(Severity.HIGH)
        assert "MEDIUM" in _get_severity_icon(Severity.MEDIUM)
        assert "LOW" in _get_severity_icon(Severity.LOW)

    def test_all_enum_values_mapped(self):
        for sev in Severity:
            icon = _get_severity_icon(sev)
            assert icon != "?"


class TestRenderConflict:
    """Test render_conflict function."""

    def test_renders_high_severity_conflict(self, mock_console, high_conflict):
        """High-severity conflict renders with red panel."""
        render_conflict(mock_console, high_conflict)

        # Verify console.print was called
        assert mock_console.print.call_count == 1
        printed_arg = mock_console.print.call_args[0][0]
        assert isinstance(printed_arg, Panel)

    def test_renders_medium_severity_conflict(self, mock_console, medium_conflict):
        """Medium-severity conflict renders with yellow panel."""
        render_conflict(mock_console, medium_conflict)

        assert mock_console.print.call_count == 1
        printed_arg = mock_console.print.call_args[0][0]
        assert isinstance(printed_arg, Panel)

    def test_renders_low_severity_conflict(self, mock_console, low_conflict):
        """Low-severity conflict renders with blue panel."""
        render_conflict(mock_console, low_conflict)

        assert mock_console.print.call_count == 1
        printed_arg = mock_console.print.call_args[0][0]
        assert isinstance(printed_arg, Panel)

    def test_no_candidates_shows_message(self, mock_console, low_conflict):
        """Conflict with 0 candidates shows 'No candidates available' message."""
        assert low_conflict.candidate_senses == []
        render_conflict(mock_console, low_conflict)

        printed_arg = mock_console.print.call_args[0][0]
        assert isinstance(printed_arg, Panel)
        # The panel body should be the string message, not a table
        assert printed_arg.renderable == "(No candidates available)"

    def test_single_candidate_renders_table(self, mock_console):
        """Conflict with 1 candidate renders a table with one row."""
        conflict = SemanticConflict(
            term=TermSurface("module"),
            conflict_type=ConflictType.UNKNOWN,
            severity=Severity.LOW,
            confidence=0.5,
            candidate_senses=[
                SenseRef(
                    surface="module",
                    scope="team_domain",
                    definition="Python package module",
                    confidence=0.8,
                ),
            ],
            context="test",
        )
        render_conflict(mock_console, conflict)

        printed_arg = mock_console.print.call_args[0][0]
        assert isinstance(printed_arg, Panel)
        # Body should be a Table (not a string)
        assert isinstance(printed_arg.renderable, Table)

    def test_many_candidates_all_shown(self, mock_console):
        """Conflict with 10+ candidates shows all of them."""
        candidates = [
            SenseRef(
                surface="term",
                scope=f"scope{i}",
                definition=f"Definition number {i}",
                confidence=0.9 - i * 0.05,
            )
            for i in range(12)
        ]
        conflict = SemanticConflict(
            term=TermSurface("term"),
            conflict_type=ConflictType.AMBIGUOUS,
            severity=Severity.MEDIUM,
            confidence=0.8,
            candidate_senses=candidates,
            context="test",
        )
        render_conflict(mock_console, conflict)

        printed_arg = mock_console.print.call_args[0][0]
        assert isinstance(printed_arg, Panel)
        assert isinstance(printed_arg.renderable, Table)
        assert printed_arg.renderable.row_count == 12

    def test_panel_border_matches_severity_high(self, mock_console, high_conflict):
        """Panel border color is red for HIGH severity."""
        render_conflict(mock_console, high_conflict)
        printed_arg = mock_console.print.call_args[0][0]
        assert printed_arg.border_style == "red"

    def test_panel_border_matches_severity_medium(self, mock_console, medium_conflict):
        """Panel border color is yellow for MEDIUM severity."""
        render_conflict(mock_console, medium_conflict)
        printed_arg = mock_console.print.call_args[0][0]
        assert printed_arg.border_style == "yellow"

    def test_panel_border_matches_severity_low(self, mock_console, low_conflict):
        """Panel border color is blue for LOW severity."""
        render_conflict(mock_console, low_conflict)
        printed_arg = mock_console.print.call_args[0][0]
        assert printed_arg.border_style == "blue"

    def test_panel_title_contains_term(self, mock_console, high_conflict):
        """Panel title contains the term surface text."""
        render_conflict(mock_console, high_conflict)
        printed_arg = mock_console.print.call_args[0][0]
        assert "workspace" in printed_arg.title

    def test_panel_subtitle_contains_metadata(self, mock_console, high_conflict):
        """Panel subtitle includes term, type, and context."""
        render_conflict(mock_console, high_conflict)
        printed_arg = mock_console.print.call_args[0][0]
        assert "workspace" in printed_arg.subtitle
        assert "ambiguous" in printed_arg.subtitle
        assert "description field" in printed_arg.subtitle

    def test_renders_with_real_console(self, high_conflict):
        """Verify no exceptions with real Console (smoke test)."""
        console = Console(file=MagicMock())
        render_conflict(console, high_conflict)

    def test_long_definition_does_not_crash(self, mock_console):
        """Very long definition text renders without crashing."""
        long_def = "A" * 500
        conflict = SemanticConflict(
            term=TermSurface("test"),
            conflict_type=ConflictType.UNKNOWN,
            severity=Severity.LOW,
            confidence=0.5,
            candidate_senses=[
                SenseRef("test", "team_domain", long_def, 0.8),
            ],
            context="test",
        )
        render_conflict(mock_console, conflict)
        assert mock_console.print.call_count == 1


class TestRenderConflictBatch:
    """Test render_conflict_batch function."""

    def test_sorts_by_severity_high_first(
        self, mock_console, high_conflict, medium_conflict, low_conflict
    ):
        """Conflicts are sorted by severity (high -> medium -> low)."""
        result = render_conflict_batch(
            mock_console,
            [low_conflict, high_conflict, medium_conflict],
            max_questions=3,
        )
        assert result[0].severity == Severity.HIGH
        assert result[1].severity == Severity.MEDIUM
        assert result[2].severity == Severity.LOW

    def test_caps_at_max_questions(self, mock_console):
        """Only max_questions conflicts are returned."""
        conflicts = [
            SemanticConflict(
                term=TermSurface(f"term{i}"),
                conflict_type=ConflictType.UNKNOWN,
                severity=Severity.LOW,
                confidence=0.5,
                candidate_senses=[],
                context="test",
            )
            for i in range(5)
        ]
        result = render_conflict_batch(
            mock_console, conflicts, max_questions=3
        )
        assert len(result) == 3

    def test_truncation_message_shown(self, mock_console):
        """When conflicts exceed max_questions, truncation message is shown."""
        conflicts = [
            SemanticConflict(
                term=TermSurface(f"term{i}"),
                conflict_type=ConflictType.UNKNOWN,
                severity=Severity.LOW,
                confidence=0.5,
                candidate_senses=[],
                context="test",
            )
            for i in range(5)
        ]
        render_conflict_batch(mock_console, conflicts, max_questions=3)

        # Check that a truncation message was printed
        all_calls = mock_console.print.call_args_list
        print_texts = [
            str(c[0][0]) if c[0] else str(c)
            for c in all_calls
        ]
        truncation_found = any("Showing 3 of 5" in t for t in print_texts)
        assert truncation_found, f"Expected truncation message in: {print_texts}"

    def test_no_truncation_message_when_under_limit(
        self, mock_console, high_conflict
    ):
        """No truncation message when conflicts fit within max_questions."""
        result = render_conflict_batch(
            mock_console, [high_conflict], max_questions=3
        )
        assert len(result) == 1

        # Only panel + blank line should be printed, no truncation msg
        print_texts = [
            str(c[0][0]) if c[0] else ""
            for c in mock_console.print.call_args_list
        ]
        truncation_found = any("Showing" in t and "of" in t for t in print_texts)
        assert not truncation_found

    def test_returns_all_when_under_limit(
        self, mock_console, high_conflict, medium_conflict
    ):
        """Returns all conflicts when count <= max_questions."""
        result = render_conflict_batch(
            mock_console, [high_conflict, medium_conflict], max_questions=5
        )
        assert len(result) == 2

    def test_empty_conflicts_list(self, mock_console):
        """Empty conflicts list returns empty result."""
        result = render_conflict_batch(mock_console, [], max_questions=3)
        assert result == []

    def test_deterministic_sort_by_term_text(self, mock_console):
        """Conflicts with same severity are sorted by term text (deterministic)."""
        c1 = SemanticConflict(
            term=TermSurface("zebra"),
            conflict_type=ConflictType.UNKNOWN,
            severity=Severity.MEDIUM,
            confidence=0.5,
            candidate_senses=[],
            context="test",
        )
        c2 = SemanticConflict(
            term=TermSurface("alpha"),
            conflict_type=ConflictType.UNKNOWN,
            severity=Severity.MEDIUM,
            confidence=0.5,
            candidate_senses=[],
            context="test",
        )
        result = render_conflict_batch(
            mock_console, [c1, c2], max_questions=5
        )
        assert result[0].term.surface_text == "alpha"
        assert result[1].term.surface_text == "zebra"

    def test_max_questions_default_is_three(self, mock_console):
        """Default max_questions is 3."""
        conflicts = [
            SemanticConflict(
                term=TermSurface(f"term{i}"),
                conflict_type=ConflictType.UNKNOWN,
                severity=Severity.LOW,
                confidence=0.5,
                candidate_senses=[],
                context="test",
            )
            for i in range(10)
        ]
        result = render_conflict_batch(mock_console, conflicts)
        assert len(result) == 3

    def test_renders_each_conflict_panel(
        self, mock_console, high_conflict, medium_conflict
    ):
        """Each conflict produces a Panel + blank line print call."""
        render_conflict_batch(
            mock_console, [high_conflict, medium_conflict], max_questions=5
        )
        # Each conflict: 1 Panel + 1 blank line = 2 calls per conflict
        # Total: 2 conflicts * 2 calls = 4
        assert mock_console.print.call_count == 4

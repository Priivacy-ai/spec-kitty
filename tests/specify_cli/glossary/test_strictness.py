"""Tests for strictness policy system (WP05)."""

import pytest
from pathlib import Path
from specify_cli.glossary.strictness import (
    Strictness,
    resolve_strictness,
    load_global_strictness,
    should_block,
    categorize_conflicts,
)
from specify_cli.glossary.models import (
    SemanticConflict,
    Severity,
    TermSurface,
    ConflictType,
)


class TestStrictnessEnum:
    """Test Strictness enum definition."""

    def test_strictness_has_three_values(self):
        """Strictness enum has exactly three values: OFF, MEDIUM, MAX."""
        assert len(Strictness) == 3
        assert Strictness.OFF == "off"
        assert Strictness.MEDIUM == "medium"
        assert Strictness.MAX == "max"


class TestResolvePrecedence:
    """Test strictness precedence resolution."""

    def test_all_none_returns_global_default(self):
        """When all overrides are None, returns global_default."""
        result = resolve_strictness(
            global_default=Strictness.MEDIUM,
            mission_override=None,
            step_override=None,
            runtime_override=None,
        )
        assert result == Strictness.MEDIUM

    def test_default_global_is_medium(self):
        """Default global_default parameter is MEDIUM."""
        result = resolve_strictness()
        assert result == Strictness.MEDIUM

    def test_runtime_override_beats_all(self):
        """Runtime override takes precedence over all other settings."""
        result = resolve_strictness(
            global_default=Strictness.MAX,
            mission_override=Strictness.MAX,
            step_override=Strictness.MAX,
            runtime_override=Strictness.OFF,
        )
        assert result == Strictness.OFF

    def test_step_override_beats_mission_and_global(self):
        """Step override takes precedence over mission and global."""
        result = resolve_strictness(
            global_default=Strictness.OFF,
            mission_override=Strictness.OFF,
            step_override=Strictness.MAX,
            runtime_override=None,
        )
        assert result == Strictness.MAX

    def test_mission_override_beats_global(self):
        """Mission override takes precedence over global default."""
        result = resolve_strictness(
            global_default=Strictness.OFF,
            mission_override=Strictness.MEDIUM,
            step_override=None,
            runtime_override=None,
        )
        assert result == Strictness.MEDIUM

    def test_global_default_used_when_no_overrides(self):
        """Global default is used when no overrides are set."""
        result = resolve_strictness(
            global_default=Strictness.MAX,
            mission_override=None,
            step_override=None,
            runtime_override=None,
        )
        assert result == Strictness.MAX

    @pytest.mark.parametrize(
        "global_val,mission_val,step_val,runtime_val,expected",
        [
            # Runtime always wins
            (Strictness.OFF, Strictness.OFF, Strictness.OFF, Strictness.MAX, Strictness.MAX),
            (Strictness.MAX, Strictness.MAX, Strictness.MAX, Strictness.OFF, Strictness.OFF),
            # Step beats mission and global
            (Strictness.OFF, Strictness.OFF, Strictness.MEDIUM, None, Strictness.MEDIUM),
            (Strictness.MAX, Strictness.MAX, Strictness.OFF, None, Strictness.OFF),
            # Mission beats global
            (Strictness.OFF, Strictness.MAX, None, None, Strictness.MAX),
            (Strictness.MAX, Strictness.OFF, None, None, Strictness.OFF),
            # Global used when all None
            (Strictness.OFF, None, None, None, Strictness.OFF),
            (Strictness.MEDIUM, None, None, None, Strictness.MEDIUM),
            (Strictness.MAX, None, None, None, Strictness.MAX),
        ],
    )
    def test_precedence_combinations(
        self, global_val, mission_val, step_val, runtime_val, expected
    ):
        """Test all precedence combinations systematically."""
        result = resolve_strictness(
            global_default=global_val,
            mission_override=mission_val,
            step_override=step_val,
            runtime_override=runtime_val,
        )
        assert result == expected


class TestLoadGlobalStrictness:
    """Test loading strictness from config.yaml."""

    def test_missing_config_file_returns_medium(self, tmp_path):
        """When config file doesn't exist, returns MEDIUM."""
        result = load_global_strictness(tmp_path)
        assert result == Strictness.MEDIUM

    def test_missing_glossary_section_returns_medium(self, tmp_path):
        """When config has no glossary section, returns MEDIUM."""
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text("other_section:\n  key: value\n")

        result = load_global_strictness(tmp_path)
        assert result == Strictness.MEDIUM

    def test_missing_strictness_key_returns_medium(self, tmp_path):
        """When glossary section has no strictness key, returns MEDIUM."""
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text("glossary:\n  other_key: value\n")

        result = load_global_strictness(tmp_path)
        assert result == Strictness.MEDIUM

    def test_valid_strictness_off(self, tmp_path):
        """When config has valid strictness=off, returns OFF."""
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text("glossary:\n  strictness: off\n")

        result = load_global_strictness(tmp_path)
        assert result == Strictness.OFF

    def test_valid_strictness_medium(self, tmp_path):
        """When config has valid strictness=medium, returns MEDIUM."""
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text("glossary:\n  strictness: medium\n")

        result = load_global_strictness(tmp_path)
        assert result == Strictness.MEDIUM

    def test_valid_strictness_max(self, tmp_path):
        """When config has valid strictness=max, returns MAX."""
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text("glossary:\n  strictness: max\n")

        result = load_global_strictness(tmp_path)
        assert result == Strictness.MAX

    def test_invalid_strictness_value_returns_medium(self, tmp_path):
        """When config has invalid strictness value, returns MEDIUM."""
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text("glossary:\n  strictness: invalid\n")

        result = load_global_strictness(tmp_path)
        assert result == Strictness.MEDIUM

    def test_malformed_yaml_returns_medium(self, tmp_path):
        """When config file is malformed YAML, returns MEDIUM."""
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text("glossary:\n  strictness: off\n  - invalid\n")

        result = load_global_strictness(tmp_path)
        assert result == Strictness.MEDIUM


class TestShouldBlock:
    """Test blocking decision logic."""

    @pytest.fixture
    def low_conflict(self):
        """Create a low-severity conflict."""
        return SemanticConflict(
            term=TermSurface(surface_text="helper"),
            conflict_type=ConflictType.UNKNOWN,
            severity=Severity.LOW,
            confidence=0.3,
            candidate_senses=[],
            context="test context",
        )

    @pytest.fixture
    def medium_conflict(self):
        """Create a medium-severity conflict."""
        from specify_cli.glossary.models import SenseRef

        return SemanticConflict(
            term=TermSurface(surface_text="utility"),
            conflict_type=ConflictType.AMBIGUOUS,
            severity=Severity.MEDIUM,
            confidence=0.6,
            candidate_senses=[
                SenseRef(surface="utility", scope="mission", definition="test def 1", confidence=0.8),
                SenseRef(surface="utility", scope="global", definition="test def 2", confidence=0.7),
            ],
            context="test context",
        )

    @pytest.fixture
    def high_conflict(self):
        """Create a high-severity conflict."""
        from specify_cli.glossary.models import SenseRef

        return SemanticConflict(
            term=TermSurface(surface_text="workspace"),
            conflict_type=ConflictType.AMBIGUOUS,
            severity=Severity.HIGH,
            confidence=0.9,
            candidate_senses=[
                SenseRef(surface="workspace", scope="mission", definition="test def 1", confidence=0.9),
                SenseRef(surface="workspace", scope="global", definition="test def 2", confidence=0.8),
            ],
            context="test context",
        )

    def test_off_never_blocks_on_empty(self):
        """OFF mode never blocks, even with empty conflicts list."""
        result = should_block(Strictness.OFF, [])
        assert result is False

    def test_off_never_blocks_on_low(self, low_conflict):
        """OFF mode never blocks on low-severity conflicts."""
        result = should_block(Strictness.OFF, [low_conflict])
        assert result is False

    def test_off_never_blocks_on_medium(self, medium_conflict):
        """OFF mode never blocks on medium-severity conflicts."""
        result = should_block(Strictness.OFF, [medium_conflict])
        assert result is False

    def test_off_never_blocks_on_high(self, high_conflict):
        """OFF mode never blocks even on high-severity conflicts."""
        result = should_block(Strictness.OFF, [high_conflict])
        assert result is False

    def test_medium_allows_empty(self):
        """MEDIUM mode allows generation when no conflicts exist."""
        result = should_block(Strictness.MEDIUM, [])
        assert result is False

    def test_medium_allows_low(self, low_conflict):
        """MEDIUM mode allows generation on low-severity conflicts."""
        result = should_block(Strictness.MEDIUM, [low_conflict])
        assert result is False

    def test_medium_allows_medium(self, medium_conflict):
        """MEDIUM mode allows generation on medium-severity conflicts."""
        result = should_block(Strictness.MEDIUM, [medium_conflict])
        assert result is False

    def test_medium_blocks_high(self, high_conflict):
        """MEDIUM mode blocks generation on high-severity conflicts."""
        result = should_block(Strictness.MEDIUM, [high_conflict])
        assert result is True

    def test_medium_blocks_mixed_with_high(self, low_conflict, medium_conflict, high_conflict):
        """MEDIUM mode blocks if ANY conflict is high-severity."""
        result = should_block(Strictness.MEDIUM, [low_conflict, medium_conflict, high_conflict])
        assert result is True

    def test_medium_allows_mixed_without_high(self, low_conflict, medium_conflict):
        """MEDIUM mode allows if no high-severity conflicts exist."""
        result = should_block(Strictness.MEDIUM, [low_conflict, medium_conflict])
        assert result is False

    def test_max_allows_empty(self):
        """MAX mode allows generation when no conflicts exist."""
        result = should_block(Strictness.MAX, [])
        assert result is False

    def test_max_blocks_low(self, low_conflict):
        """MAX mode blocks even on low-severity conflicts."""
        result = should_block(Strictness.MAX, [low_conflict])
        assert result is True

    def test_max_blocks_medium(self, medium_conflict):
        """MAX mode blocks on medium-severity conflicts."""
        result = should_block(Strictness.MAX, [medium_conflict])
        assert result is True

    def test_max_blocks_high(self, high_conflict):
        """MAX mode blocks on high-severity conflicts."""
        result = should_block(Strictness.MAX, [high_conflict])
        assert result is True

    def test_max_blocks_any_conflict(self, low_conflict):
        """MAX mode blocks if ANY conflict exists."""
        result = should_block(Strictness.MAX, [low_conflict])
        assert result is True

    @pytest.mark.parametrize(
        "strictness,has_low,has_medium,has_high,expected_block",
        [
            # OFF never blocks
            (Strictness.OFF, False, False, False, False),
            (Strictness.OFF, True, False, False, False),
            (Strictness.OFF, False, True, False, False),
            (Strictness.OFF, False, False, True, False),
            (Strictness.OFF, True, True, True, False),
            # MEDIUM blocks only on high
            (Strictness.MEDIUM, False, False, False, False),
            (Strictness.MEDIUM, True, False, False, False),
            (Strictness.MEDIUM, False, True, False, False),
            (Strictness.MEDIUM, False, False, True, True),
            (Strictness.MEDIUM, True, True, True, True),
            # MAX blocks on any
            (Strictness.MAX, False, False, False, False),
            (Strictness.MAX, True, False, False, True),
            (Strictness.MAX, False, True, False, True),
            (Strictness.MAX, False, False, True, True),
            (Strictness.MAX, True, True, True, True),
        ],
    )
    def test_blocking_matrix(
        self,
        strictness,
        has_low,
        has_medium,
        has_high,
        expected_block,
        low_conflict,
        medium_conflict,
        high_conflict,
    ):
        """Test all combinations of strictness modes and severity levels."""
        conflicts = []
        if has_low:
            conflicts.append(low_conflict)
        if has_medium:
            conflicts.append(medium_conflict)
        if has_high:
            conflicts.append(high_conflict)

        result = should_block(strictness, conflicts)
        assert result == expected_block


class TestCategorizeConflicts:
    """Test conflict categorization by severity."""

    def test_empty_conflicts_list(self):
        """Categorizing empty list returns all three severity buckets."""
        result = categorize_conflicts([])

        assert len(result) == 3
        assert Severity.LOW in result
        assert Severity.MEDIUM in result
        assert Severity.HIGH in result
        assert len(result[Severity.LOW]) == 0
        assert len(result[Severity.MEDIUM]) == 0
        assert len(result[Severity.HIGH]) == 0

    def test_single_low_conflict(self):
        """Single low-severity conflict is categorized correctly."""
        conflict = SemanticConflict(
            term=TermSurface(surface_text="test"),
            conflict_type=ConflictType.UNKNOWN,
            severity=Severity.LOW,
            confidence=0.3,
            candidate_senses=[],
            context="test",
        )

        result = categorize_conflicts([conflict])

        assert len(result[Severity.LOW]) == 1
        assert len(result[Severity.MEDIUM]) == 0
        assert len(result[Severity.HIGH]) == 0

    def test_mixed_severity_conflicts(self):
        """Mixed-severity conflicts are categorized into correct buckets."""
        from specify_cli.glossary.models import SenseRef

        low = SemanticConflict(
            term=TermSurface(surface_text="test1"),
            conflict_type=ConflictType.UNKNOWN,
            severity=Severity.LOW,
            confidence=0.3,
            candidate_senses=[],
            context="test",
        )
        medium = SemanticConflict(
            term=TermSurface(surface_text="test2"),
            conflict_type=ConflictType.AMBIGUOUS,
            severity=Severity.MEDIUM,
            confidence=0.6,
            candidate_senses=[
                SenseRef(surface="test2", scope="mission", definition="def1", confidence=0.6),
            ],
            context="test",
        )
        high = SemanticConflict(
            term=TermSurface(surface_text="test3"),
            conflict_type=ConflictType.AMBIGUOUS,
            severity=Severity.HIGH,
            confidence=0.9,
            candidate_senses=[
                SenseRef(surface="test3", scope="mission", definition="def1", confidence=0.9),
            ],
            context="test",
        )

        result = categorize_conflicts([low, medium, high])

        assert len(result[Severity.LOW]) == 1
        assert len(result[Severity.MEDIUM]) == 1
        assert len(result[Severity.HIGH]) == 1
        assert result[Severity.LOW][0] == low
        assert result[Severity.MEDIUM][0] == medium
        assert result[Severity.HIGH][0] == high

    def test_multiple_conflicts_same_severity(self):
        """Multiple conflicts with same severity are all categorized."""
        conflicts = [
            SemanticConflict(
                term=TermSurface(surface_text=f"test{i}"),
                conflict_type=ConflictType.UNKNOWN,
                severity=Severity.LOW,
                confidence=0.3,
                candidate_senses=[],
                context="test",
            )
            for i in range(5)
        ]

        result = categorize_conflicts(conflicts)

        assert len(result[Severity.LOW]) == 5
        assert len(result[Severity.MEDIUM]) == 0
        assert len(result[Severity.HIGH]) == 0

    def test_unknown_severity_bucketed_as_high(self):
        """Unknown/invalid severity is bucketed into HIGH for safety.

        Regression test for review issue 2: a conflict with an unexpected
        severity value must not cause a KeyError in categorize_conflicts
        and must be treated as HIGH.
        """
        # Create a conflict, then forcibly set severity to a non-enum value
        conflict = SemanticConflict(
            term=TermSurface(surface_text="rogue"),
            conflict_type=ConflictType.UNKNOWN,
            severity=Severity.LOW,  # placeholder, overridden below
            confidence=0.5,
            candidate_senses=[],
            context="test",
        )
        # Bypass the enum -- simulate an unexpected severity value
        object.__setattr__(conflict, "severity", "critical")

        result = categorize_conflicts([conflict])

        # Should not KeyError, and the conflict should land in HIGH
        assert len(result[Severity.HIGH]) == 1
        assert result[Severity.HIGH][0] is conflict
        assert len(result[Severity.LOW]) == 0
        assert len(result[Severity.MEDIUM]) == 0


class TestUnknownSeverityBlocking:
    """Test that unknown/invalid severities are treated as HIGH for blocking.

    Regression tests for review issue 2: unknown severities must not silently
    pass through MEDIUM mode, and must not crash categorize_conflicts.
    """

    def test_medium_blocks_unknown_severity(self):
        """MEDIUM mode blocks on a conflict with an unknown severity value.

        In MEDIUM mode, only HIGH severity blocks. Unknown severities must
        be treated as HIGH for safety, so they should trigger blocking.
        """
        conflict = SemanticConflict(
            term=TermSurface(surface_text="rogue"),
            conflict_type=ConflictType.UNKNOWN,
            severity=Severity.LOW,  # placeholder
            confidence=0.5,
            candidate_senses=[],
            context="test",
        )
        # Forcibly set an unrecognised severity
        object.__setattr__(conflict, "severity", "critical")

        result = should_block(Strictness.MEDIUM, [conflict])
        assert result is True, "Unknown severity must be treated as HIGH and block in MEDIUM mode"

    def test_off_does_not_block_unknown_severity(self):
        """OFF mode never blocks, even with unknown severity."""
        conflict = SemanticConflict(
            term=TermSurface(surface_text="rogue"),
            conflict_type=ConflictType.UNKNOWN,
            severity=Severity.LOW,  # placeholder
            confidence=0.5,
            candidate_senses=[],
            context="test",
        )
        object.__setattr__(conflict, "severity", "critical")

        result = should_block(Strictness.OFF, [conflict])
        assert result is False

    def test_max_blocks_unknown_severity(self):
        """MAX mode blocks on any conflict, including unknown severity."""
        conflict = SemanticConflict(
            term=TermSurface(surface_text="rogue"),
            conflict_type=ConflictType.UNKNOWN,
            severity=Severity.LOW,  # placeholder
            confidence=0.5,
            candidate_senses=[],
            context="test",
        )
        object.__setattr__(conflict, "severity", "unknown_val")

        result = should_block(Strictness.MAX, [conflict])
        assert result is True

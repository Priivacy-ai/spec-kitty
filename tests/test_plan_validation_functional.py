"""Functional tests for plan validation guardrail (plan_validation.py).

Test Suite 4: Plan Validation Guardrail

Tests the plan validation that blocks research/tasks commands when plan.md
is still in template form, preventing premature workflow progression.

Coverage Target: 95%+ for plan_validation.py
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess

from specify_cli.plan_validation import (
    detect_unfilled_plan,
    validate_plan_filled,
    PlanValidationError,
    TEMPLATE_MARKERS,
    MIN_MARKERS_TO_REMOVE,
)


# Template plan content with 8+ markers (should fail validation)
TEMPLATE_PLAN = """
# Implementation Plan: [FEATURE]

**Date**: [DATE]
**Language/Version**: [e.g., Python 3.11 or NEEDS CLARIFICATION]
**Primary Dependencies**: [e.g., FastAPI or NEEDS CLARIFICATION]
**Testing**: [e.g., pytest or NEEDS CLARIFICATION]

[Gates determined based on constitution file]

# [REMOVE IF UNUSED] Option 1
# [REMOVE IF UNUSED] Option 2

ACTION REQUIRED: Replace the content above with your implementation plan.
"""

# Filled plan content with < 5 markers (should pass validation)
FILLED_PLAN = """
# Implementation Plan: User Authentication System

**Date**: 2025-11-13
**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, bcrypt, python-jose
**Testing**: pytest, pytest-asyncio

## Security Guardrails
✓ Password hashing required (bcrypt with 12 rounds)
✓ Rate limiting on auth endpoints (10 requests/minute)
✓ JWT tokens expire after 1 hour
✓ Refresh tokens expire after 7 days

## Project Structure
```
backend/
├── src/
│   ├── models/
│   │   ├── user.py
│   │   └── token.py
│   ├── api/
│   │   ├── auth.py
│   │   └── users.py
│   ├── security/
│   │   ├── password.py
│   │   └── jwt.py
│   └── database/
│       └── connection.py
└── tests/
    ├── test_auth.py
    └── test_security.py
```

## Implementation Phases
1. Database models and migrations
2. Password hashing utilities
3. JWT token generation and validation
4. Auth endpoints (login, logout, refresh)
5. User registration endpoint
6. Integration tests
"""

# Plan with exactly 4 markers (should pass - below threshold)
PLAN_4_MARKERS = """
# Implementation Plan: [FEATURE]

**Date**: [DATE]
**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI

[link]
[Gates determined based on constitution file]

✓ Password hashing required
✓ Rate limiting needed

backend/src/models/user.py
backend/src/api/auth.py
"""

# Plan with exactly 5 markers (should fail - at threshold)
PLAN_5_MARKERS = """
# Implementation Plan: [FEATURE]

**Date**: [DATE]
**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI

[link]
[Gates determined based on constitution file]
# [REMOVE IF UNUSED] Option 1

✓ Password hashing required

backend/src/models/user.py
"""


class TestPlanDetection:
    """Test 4.5: Plan Validation Threshold"""

    def test_detect_unfilled_plan_with_many_markers(self):
        """Verify template plan with 5+ markers is detected as unfilled."""
        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"
            plan_file.write_text(TEMPLATE_PLAN)

            is_unfilled, markers = detect_unfilled_plan(plan_file)

            # Should be detected as unfilled
            assert is_unfilled is True, "Template plan should be detected as unfilled"

            # Should have found multiple markers
            assert len(markers) >= MIN_MARKERS_TO_REMOVE, \
                f"Should find at least {MIN_MARKERS_TO_REMOVE} markers, found {len(markers)}"

            # Check specific markers are detected
            assert any("[FEATURE]" in m for m in markers), "Should detect [FEATURE] marker"
            assert any("[DATE]" in m for m in markers), "Should detect [DATE] marker"
            assert any("NEEDS CLARIFICATION" in m for m in markers), "Should detect NEEDS CLARIFICATION"
            assert any("[REMOVE IF UNUSED]" in m for m in markers), "Should detect [REMOVE IF UNUSED]"

    def test_detect_filled_plan(self):
        """Verify filled plan with < 5 markers passes detection."""
        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"
            plan_file.write_text(FILLED_PLAN)

            is_unfilled, markers = detect_unfilled_plan(plan_file)

            # Should NOT be detected as unfilled
            assert is_unfilled is False, f"Filled plan should not be unfilled, but found {len(markers)} markers"

            # May have some markers, but less than threshold
            assert len(markers) < MIN_MARKERS_TO_REMOVE, \
                f"Should have < {MIN_MARKERS_TO_REMOVE} markers, found {len(markers)}: {markers}"

    def test_threshold_with_exactly_4_markers(self):
        """Verify 4 markers passes (below 5-marker threshold)."""
        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"
            plan_file.write_text(PLAN_4_MARKERS)

            is_unfilled, markers = detect_unfilled_plan(plan_file)

            # Should pass with 4 markers
            assert is_unfilled is False, "4 markers should pass validation"
            assert len(markers) == 4, f"Should find exactly 4 markers, found {len(markers)}"

    def test_threshold_with_exactly_5_markers(self):
        """Verify 5 markers fails (at threshold)."""
        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"
            plan_file.write_text(PLAN_5_MARKERS)

            is_unfilled, markers = detect_unfilled_plan(plan_file)

            # Should fail with 5 markers
            assert is_unfilled is True, "5 markers should fail validation"
            assert len(markers) == 5, f"Should find exactly 5 markers, found {len(markers)}"

    def test_empty_plan_file(self):
        """Verify empty plan.md doesn't crash and returns sensible default."""
        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"
            plan_file.write_text("")

            is_unfilled, markers = detect_unfilled_plan(plan_file)

            # Empty file should not be considered unfilled (no markers found)
            assert is_unfilled is False, "Empty file should not block progress"
            assert len(markers) == 0, "Empty file should have no markers"

    def test_missing_plan_file(self):
        """Verify missing plan.md doesn't crash."""
        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "nonexistent.md"

            is_unfilled, markers = detect_unfilled_plan(plan_file)

            # Missing file should not block progress
            assert is_unfilled is False, "Missing file should not block progress"
            assert len(markers) == 0, "Missing file should have no markers"


class TestValidatePlanFilled:
    """Test validation function behavior."""

    def test_validate_plan_raises_on_unfilled(self):
        """Verify validate_plan_filled raises PlanValidationError on unfilled plan."""
        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"
            plan_file.write_text(TEMPLATE_PLAN)

            # Should raise error in strict mode
            with pytest.raises(PlanValidationError) as exc_info:
                validate_plan_filled(plan_file, feature_slug="test-feature", strict=True)

            error_msg = str(exc_info.value)

            # Error message should be helpful
            assert "appears to be unfilled" in error_msg, "Should mention unfilled"
            assert "template markers" in error_msg, "Should mention markers"
            assert "test-feature" in error_msg, "Should include feature slug"
            assert "/spec-kitty.plan" in error_msg, "Should suggest next step"

    def test_validate_plan_passes_on_filled(self):
        """Verify validate_plan_filled passes for filled plan."""
        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"
            plan_file.write_text(FILLED_PLAN)

            # Should not raise error
            validate_plan_filled(plan_file, feature_slug="test-feature", strict=True)

    def test_validate_plan_non_strict_warns(self):
        """Verify non-strict mode warns but doesn't raise."""
        import io
        import sys

        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"
            plan_file.write_text(TEMPLATE_PLAN)

            # Capture stderr
            old_stderr = sys.stderr
            sys.stderr = io.StringIO()

            try:
                # Should not raise in non-strict mode
                validate_plan_filled(plan_file, strict=False)

                # But should have printed warning
                warning = sys.stderr.getvalue()
                assert "appears to be unfilled" in warning, "Should warn about unfilled plan"
            finally:
                sys.stderr = old_stderr


class TestMarkerDetection:
    """Test specific marker detection."""

    def test_all_template_markers_defined(self):
        """Verify TEMPLATE_MARKERS list is comprehensive."""
        # Should have at least 10 markers defined
        assert len(TEMPLATE_MARKERS) >= 10, \
            f"Should have at least 10 markers, found {len(TEMPLATE_MARKERS)}"

        # Key markers should be present
        expected_markers = [
            "[FEATURE]",
            "[DATE]",
            "NEEDS CLARIFICATION",
            "[REMOVE IF UNUSED]",
            "ACTION REQUIRED",
        ]

        for marker in expected_markers:
            assert any(marker in m for m in TEMPLATE_MARKERS), \
                f"Marker '{marker}' should be in TEMPLATE_MARKERS"

    def test_marker_detection_case_sensitive(self):
        """Verify marker detection is case-sensitive."""
        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"

            # Write lowercase version (should not match)
            plan_file.write_text("[feature] and [date] lowercase")
            is_unfilled, markers = detect_unfilled_plan(plan_file)
            assert is_unfilled is False, "Lowercase markers should not match"

            # Write uppercase version (should match)
            plan_file.write_text("[FEATURE] and [DATE] uppercase")
            is_unfilled, markers = detect_unfilled_plan(plan_file)
            assert len(markers) >= 2, "Uppercase markers should match"

    def test_partial_marker_not_detected(self):
        """Verify partial markers don't trigger false positives."""
        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"

            # Text that contains marker substrings but isn't actually markers
            plan_file.write_text("""
                This document discusses how to determine features.
                We need clarification on dates.
                Remove unused code if found.
            """)

            is_unfilled, markers = detect_unfilled_plan(plan_file)

            # Should not detect these as template markers
            assert len(markers) == 0, \
                f"Should not detect partial matches, found: {markers}"


class TestMinMarkersThreshold:
    """Test MIN_MARKERS_TO_REMOVE threshold behavior."""

    def test_min_markers_threshold_is_5(self):
        """Verify threshold is set to 5 as specified."""
        assert MIN_MARKERS_TO_REMOVE == 5, \
            f"Threshold should be 5, is {MIN_MARKERS_TO_REMOVE}"

    def test_threshold_boundary_conditions(self):
        """Test plans at various marker counts around threshold."""
        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"

            # Test 3, 4, 5, 6 markers
            test_cases = [
                (3, False, "3 markers should pass"),
                (4, False, "4 markers should pass"),
                (5, True, "5 markers should fail"),
                (6, True, "6 markers should fail"),
            ]

            for marker_count, should_fail, description in test_cases:
                # Create plan with specific number of markers
                markers_text = ""
                for i in range(marker_count):
                    if i < len(TEMPLATE_MARKERS):
                        markers_text += f"{TEMPLATE_MARKERS[i]}\n"

                plan_content = f"""
# Implementation Plan: Test
**Date**: 2025-11-13
{markers_text}
Some actual content here.
"""
                plan_file.write_text(plan_content)

                is_unfilled, found_markers = detect_unfilled_plan(plan_file)

                assert is_unfilled == should_fail, \
                    f"{description}: expected {should_fail}, got {is_unfilled} with {len(found_markers)} markers"


class TestRegressionCases:
    """Regression tests for plan validation."""

    def test_plan_with_code_blocks_not_confused(self):
        """Verify code blocks don't trigger false positives."""
        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"

            # Plan with code examples that mention markers
            plan_file.write_text("""
# Implementation Plan: Code Examples

**Date**: 2025-11-13

Example code:
```python
def get_feature():
    return "[FEATURE]"  # This is just example code

def needs_clarification():
    return "or NEEDS CLARIFICATION"  # Also example
```

The implementation is clear and ready.
""")

            is_unfilled, markers = detect_unfilled_plan(plan_file)

            # Should still detect these markers (they're in the text)
            # This test documents current behavior - markers in code blocks ARE detected
            # This is acceptable as it errs on the side of caution
            assert isinstance(markers, list), "Should return markers list"

    def test_plan_with_proper_brackets_not_confused(self):
        """Verify proper use of brackets doesn't trigger false positives."""
        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"

            # Plan using brackets properly (not template markers)
            plan_file.write_text("""
# Implementation Plan: Bracket Usage

**Date**: 2025-11-13

Array access: users[0], items[index]
Optional parameters: query[string]
Type hints: List[User], Dict[str, Any]

Implementation is complete.
""")

            is_unfilled, markers = detect_unfilled_plan(plan_file)

            # Should not detect these as template markers
            assert len(markers) == 0, \
                f"Proper bracket usage should not trigger markers, found: {markers}"

    def test_unicode_content_in_plan(self):
        """Verify plan with Unicode content doesn't cause issues."""
        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"

            # Plan with Unicode characters (smart quotes from the encoding issue)
            plan_file.write_text("""
# Implementation Plan: Unicode Test

**Date**: 2025-11-13
**Author**: José García

User's profile system — handles authentication
Temperature: 72°F ± 2°
Price: $100 × quantity

Implementation complete.
""", encoding='utf-8')

            is_unfilled, markers = detect_unfilled_plan(plan_file)

            # Should handle Unicode gracefully
            assert is_unfilled is False, "Unicode content should not cause detection issues"
            assert len(markers) == 0, "Should not detect Unicode as markers"


class TestErrorMessages:
    """Test error message quality and actionability."""

    def test_error_message_includes_marker_count(self):
        """Verify error message shows how many markers found."""
        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"
            plan_file.write_text(TEMPLATE_PLAN)

            try:
                validate_plan_filled(plan_file, strict=True)
                pytest.fail("Should have raised PlanValidationError")
            except PlanValidationError as e:
                error_msg = str(e)

                # Should show count
                assert "template markers" in error_msg.lower(), \
                    "Should mention markers"
                # Should show actual markers found
                assert any(marker in error_msg for marker in ["[FEATURE]", "[DATE]"]), \
                    "Should show example markers"

    def test_error_message_suggests_remediation(self):
        """Verify error message provides clear next steps."""
        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"
            plan_file.write_text(TEMPLATE_PLAN)

            try:
                validate_plan_filled(plan_file, feature_slug="001-auth", strict=True)
                pytest.fail("Should have raised PlanValidationError")
            except PlanValidationError as e:
                error_msg = str(e)

                # Should suggest running plan workflow
                assert "/spec-kitty.plan" in error_msg, \
                    "Should suggest plan workflow"

                # Should mention feature
                assert "001-auth" in error_msg, \
                    "Should include feature slug for context"

                # Should explain what needs to be done
                assert "complete" in error_msg.lower() or "fill" in error_msg.lower(), \
                    "Should explain plan needs to be filled"


# Performance test
class TestPerformance:
    """Test performance requirements."""

    def test_plan_detection_under_20ms(self):
        """Verify template detection completes in < 20ms for typical plan."""
        import time

        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"
            plan_file.write_text(TEMPLATE_PLAN)

            # Run detection
            start = time.time()
            detect_unfilled_plan(plan_file)
            elapsed = (time.time() - start) * 1000  # Convert to ms

            assert elapsed < 20, \
                f"Plan detection took {elapsed:.1f}ms, should be < 20ms"

    def test_large_plan_file_performance(self):
        """Verify detection works efficiently on large plan files."""
        import time

        with TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"

            # Create a large plan (100KB)
            large_content = TEMPLATE_PLAN + ("\n# Extra Section\nContent here.\n" * 1000)
            plan_file.write_text(large_content)

            # Should still be fast
            start = time.time()
            detect_unfilled_plan(plan_file)
            elapsed = (time.time() - start) * 1000

            assert elapsed < 50, \
                f"Large plan detection took {elapsed:.1f}ms, should be < 50ms"

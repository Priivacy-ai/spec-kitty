"""Behavioral tests for execute_with_glossary hook.

Following ATDD principles: focus on integration behavior, not mocks.
These tests verify:
- Hook respects metadata-driven enablement
- Primitive execution with/without glossary pipeline
- Pipeline integration contract

The execute_with_glossary hook is the integration point between mission
executors and the glossary validation pipeline. When glossary_check is
enabled (default), it runs the full middleware stack before executing
the primitive. See:
- src/doctrine/missions/glossary_hook.py for hook implementation
- src/specify_cli/glossary/attachment.py for pipeline runner
"""

from pathlib import Path
from unittest.mock import Mock


from doctrine.missions.glossary_hook import execute_with_glossary
from doctrine.missions.primitives import PrimitiveExecutionContext


class TestGlossaryHookEnablement:
    """Verify hook respects glossary_check metadata."""

    def test_skips_pipeline_when_disabled(self):
        """Given: context with glossary_check=disabled
        When: execute_with_glossary called
        Then: primitive runs without glossary pipeline
        """
        primitive_fn = Mock(return_value="result")
        ctx = PrimitiveExecutionContext(
            step_id="step-001",
            mission_id="mission-001",
            run_id="run-001",
            inputs={},
            metadata={"glossary_check": "disabled"},
            config={},
        )

        result = execute_with_glossary(
            primitive_fn=primitive_fn,
            context=ctx,
            repo_root=Path("/tmp"),
        )

        assert result == "result"
        primitive_fn.assert_called_once_with(ctx)

    def test_skips_pipeline_when_bool_false(self):
        """Given: context with glossary_check=False (YAML boolean)
        When: execute_with_glossary called
        Then: primitive runs without glossary pipeline
        """
        primitive_fn = Mock(return_value="result")
        ctx = PrimitiveExecutionContext(
            step_id="step-001",
            mission_id="mission-001",
            run_id="run-001",
            inputs={},
            metadata={"glossary_check": False},
            config={},
        )

        result = execute_with_glossary(
            primitive_fn=primitive_fn,
            context=ctx,
            repo_root=Path("/tmp"),
        )

        assert result == "result"
        primitive_fn.assert_called_once_with(ctx)


class TestPrimitiveForwarding:
    """Verify primitive execution returns correct results."""

    def test_returns_primitive_result(self):
        """Given: primitive returns complex object
        When: execute_with_glossary called
        Then: returns exact primitive result (no wrapping)
        """
        primitive_fn = Mock(return_value={"status": "done", "output": [1, 2, 3]})
        ctx = PrimitiveExecutionContext(
            step_id="step-001",
            mission_id="mission-001",
            run_id="run-001",
            inputs={},
            metadata={"glossary_check": False},
            config={},
        )

        result = execute_with_glossary(
            primitive_fn=primitive_fn,
            context=ctx,
            repo_root=Path("/tmp"),
        )

        assert result == {"status": "done", "output": [1, 2, 3]}

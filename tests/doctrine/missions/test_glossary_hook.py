"""Behavioral tests for execute_with_glossary hook and _read_glossary_check_metadata.

Targets mutation-prone areas:
- _read_glossary_check_metadata: key name, None guard, disabled/enabled string
  comparisons, bool handling, unknown-value default
- execute_with_glossary: metadata extraction, no-runner fallback, result forwarding

Patterns: Boundary Pair (disabled/enabled strings, bool False vs None),
Non-Identity Inputs (distinct metadata keys), Bi-Directional Logic
(True vs. False return from enablement check).
"""

from pathlib import Path
from unittest.mock import Mock, patch

from doctrine.missions.glossary_hook import _read_glossary_check_metadata, execute_with_glossary
from doctrine.missions.primitives import PrimitiveExecutionContext
import pytest

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


# ── _read_glossary_check_metadata ──────────────────────────────────────────────


class TestReadGlossaryCheckMetadata:
    """Boundary pairs on key name, None guard, and string comparison."""

    def test_absent_key_returns_true(self):
        assert _read_glossary_check_metadata({}) is True

    def test_absent_key_non_empty_dict_returns_true(self):
        assert _read_glossary_check_metadata({"other_key": "value"}) is True

    def test_glossary_check_key_is_read(self):
        # Value must come from "glossary_check", not some other key
        result = _read_glossary_check_metadata({"glossary_check": "disabled"})
        assert result is False

    def test_wrong_key_falls_through_to_default(self):
        result = _read_glossary_check_metadata({"glossary_check_flag": "disabled"})
        assert result is True

    def test_none_value_returns_true(self):
        assert _read_glossary_check_metadata({"glossary_check": None}) is True

    def test_bool_false_returns_false(self):
        assert _read_glossary_check_metadata({"glossary_check": False}) is False

    def test_bool_true_returns_true(self):
        assert _read_glossary_check_metadata({"glossary_check": True}) is True

    def test_string_disabled_returns_false(self):
        assert _read_glossary_check_metadata({"glossary_check": "disabled"}) is False

    def test_string_enabled_returns_true(self):
        assert _read_glossary_check_metadata({"glossary_check": "enabled"}) is True

    def test_string_disabled_case_insensitive(self):
        assert _read_glossary_check_metadata({"glossary_check": "DISABLED"}) is False

    def test_string_enabled_case_insensitive(self):
        assert _read_glossary_check_metadata({"glossary_check": "ENABLED"}) is True

    def test_unknown_string_returns_true(self):
        assert _read_glossary_check_metadata({"glossary_check": "maybe"}) is True

    def test_disabled_returns_false_not_true(self):
        result = _read_glossary_check_metadata({"glossary_check": "disabled"})
        assert result is not True

    def test_enabled_returns_true_not_false(self):
        result = _read_glossary_check_metadata({"glossary_check": "enabled"})
        assert result is not False


# ── execute_with_glossary ──────────────────────────────────────────────────────


def _make_ctx(metadata: dict | None = None) -> PrimitiveExecutionContext:
    return PrimitiveExecutionContext(
        step_id="step-001",
        mission_id="mission-001",
        run_id="run-001",
        inputs={},
        metadata=metadata or {},
        config={},
    )


class TestGlossaryHookEnablement:
    """Verify hook respects glossary_check metadata."""

    def test_skips_pipeline_when_disabled(self):
        primitive_fn = Mock(return_value="result")
        ctx = _make_ctx({"glossary_check": "disabled"})
        result = execute_with_glossary(primitive_fn=primitive_fn, context=ctx, repo_root=Path("/tmp"))
        assert result == "result"
        primitive_fn.assert_called_once_with(ctx)

    def test_skips_pipeline_when_bool_false(self):
        primitive_fn = Mock(return_value="result")
        ctx = _make_ctx({"glossary_check": False})
        result = execute_with_glossary(primitive_fn=primitive_fn, context=ctx, repo_root=Path("/tmp"))
        assert result == "result"
        primitive_fn.assert_called_once_with(ctx)

    def test_reads_metadata_from_context(self):
        primitive_fn = Mock(return_value="ok")
        ctx = _make_ctx({"glossary_check": "disabled"})
        result = execute_with_glossary(primitive_fn=primitive_fn, context=ctx, repo_root=Path("/tmp"))
        assert result == "ok"

    def test_no_runner_registered_falls_through_to_primitive(self):
        primitive_fn = Mock(return_value="fallback-result")
        ctx = _make_ctx({})
        # Patch get_runner to return None — simulates no runner registered
        with (
            patch("doctrine.missions.glossary_hook.get_runner", return_value=None),
            patch("doctrine.missions.glossary_hook.import_module", side_effect=ImportError),
        ):
            result = execute_with_glossary(
                primitive_fn=primitive_fn, context=ctx, repo_root=Path("/tmp")
            )
        assert result == "fallback-result"
        primitive_fn.assert_called_once_with(ctx)

    def test_context_with_empty_metadata_still_runs(self):
        primitive_fn = Mock(return_value="ran")
        ctx = _make_ctx({})
        with (
            patch("doctrine.missions.glossary_hook.get_runner", return_value=None),
            patch("doctrine.missions.glossary_hook.import_module", side_effect=ImportError),
        ):
            result = execute_with_glossary(
                primitive_fn=primitive_fn, context=ctx, repo_root=Path("/tmp")
            )
        assert result == "ran"


class TestPrimitiveForwarding:
    """Verify primitive execution returns correct results."""

    def test_returns_primitive_result(self):
        primitive_fn = Mock(return_value={"status": "done", "output": [1, 2, 3]})
        ctx = _make_ctx({"glossary_check": False})
        result = execute_with_glossary(
            primitive_fn=primitive_fn, context=ctx, repo_root=Path("/tmp")
        )
        assert result == {"status": "done", "output": [1, 2, 3]}

    def test_disabled_path_returns_primitive_result_directly(self):
        expected = object()
        primitive_fn = Mock(return_value=expected)
        ctx = _make_ctx({"glossary_check": "disabled"})
        result = execute_with_glossary(
            primitive_fn=primitive_fn, context=ctx, repo_root=Path("/tmp")
        )
        assert result is expected

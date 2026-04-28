"""Unit tests for WPMetadata.resolved_agent() — total 4-tuple parser (#833).

Locks in the contract for WP03's agent-identity 4-tuple parser. The parser
must accept every supported colon arity (1/2/3/4) on the ``agent`` field
without silently discarding any non-empty positional segment, must fall back
to documented defaults for empty positional segments and trailing missing
segments, and must raise ``ValueError`` when ``tool`` is empty.

References:
- GitHub issue #833
- kitty-specs/release-3-2-0a6-tranche-2-01KQ9MKP/data-model.md §2
"""

from __future__ import annotations

import pytest

from specify_cli.status.models import AgentAssignment
from specify_cli.status.wp_metadata import WPMetadata

pytestmark = pytest.mark.fast


def _make_wp(agent: str | None) -> WPMetadata:
    """Construct a minimal WPMetadata with the supplied ``agent`` field."""
    return WPMetadata(work_package_id="WP01", title="Test", agent=agent)


# ── Arity coverage ─────────────────────────────────────────────────────────


def test_one_segment_uses_all_defaults() -> None:
    """A bare (non-colon) tool token preserves the legacy fallback semantics.

    For ``agent="claude"`` we keep the historical AgentAssignment shape
    (``model="unknown-model"``, ``profile_id=None``, ``role=None``) so
    pre-#833 callers do not see a regression in resolved values.
    """
    result = _make_wp("claude").resolved_agent()
    assert isinstance(result, AgentAssignment)
    assert result.tool == "claude"
    # When no registry entry exists the documented default for ``model`` is
    # ``unknown-model`` (preserving prior behavior).
    assert result.model == "unknown-model"
    # ``profile_id`` and ``role`` defaults remain ``None`` for a bare token
    # so existing AgentAssignment passthrough callers keep working.
    assert result.profile_id is None
    assert result.role is None


def test_two_segments_preserves_model() -> None:
    """``tool:model`` preserves *model* and fills the trailing slots from defaults."""
    result = _make_wp("claude:opus-4-7").resolved_agent()
    assert result.tool == "claude"
    assert result.model == "opus-4-7"
    # Per data-model.md §2, role default is the documented constant
    # "implementer" once the user opts into the colon format.
    assert result.role == "implementer"


def test_three_segments_preserves_profile() -> None:
    """``tool:model:profile_id`` preserves model + profile_id and defaults role."""
    result = _make_wp("claude:opus-4-7:reviewer-default").resolved_agent()
    assert result.tool == "claude"
    assert result.model == "opus-4-7"
    assert result.profile_id == "reviewer-default"
    assert result.role == "implementer"


def test_four_segments_preserves_role() -> None:
    """``tool:model:profile_id:role`` preserves every supplied non-empty segment.

    This is the regression the WP fixes: prior to #833 the ``model``,
    ``profile_id`` and ``role`` slots were silently discarded — only ``tool``
    survived.
    """
    result = _make_wp(
        "claude:opus-4-7:reviewer-default:reviewer"
    ).resolved_agent()
    assert result.tool == "claude"
    assert result.model == "opus-4-7"
    assert result.profile_id == "reviewer-default"
    assert result.role == "reviewer"


# ── Empty-segment handling ─────────────────────────────────────────────────


def test_empty_positional_segment_falls_back() -> None:
    """An empty positional segment falls back to the documented default.

    For ``claude::reviewer-default:reviewer`` the empty model slot must
    resolve to the registry default (``unknown-model`` here) while the
    explicitly supplied profile_id and role survive verbatim.
    """
    result = _make_wp("claude::reviewer-default:reviewer").resolved_agent()
    assert result.tool == "claude"
    assert result.model == "unknown-model"
    assert result.profile_id == "reviewer-default"
    assert result.role == "reviewer"


def test_trailing_empty_segments_fall_back() -> None:
    """Trailing missing/empty segments fall back to defaults.

    ``claude:opus-4-7:::`` is equivalent to supplying ``tool`` and ``model``
    with empty trailing positions for ``profile_id`` and ``role``.
    """
    result = _make_wp("claude:opus-4-7:::").resolved_agent()
    assert result.tool == "claude"
    assert result.model == "opus-4-7"
    # No registry default → profile_id stays None.
    assert result.profile_id is None
    # role default per the documented table.
    assert result.role == "implementer"


def test_two_empty_middle_segments_use_defaults() -> None:
    """Multiple empty positional segments each fall back independently."""
    result = _make_wp("claude:::reviewer").resolved_agent()
    assert result.tool == "claude"
    assert result.model == "unknown-model"
    assert result.profile_id is None
    assert result.role == "reviewer"


# ── Error path ─────────────────────────────────────────────────────────────


def test_empty_tool_raises() -> None:
    """An empty ``tool`` slot raises ``ValueError`` — parsing is total but tool is required."""
    with pytest.raises(ValueError) as excinfo:
        _make_wp(":opus-4-7").resolved_agent()
    # Error message names the WP id so operators can locate the offending file.
    assert "WP01" in str(excinfo.value)


def test_empty_tool_with_full_arity_raises() -> None:
    """Empty tool slot raises even when every other segment is supplied."""
    with pytest.raises(ValueError):
        _make_wp(":opus-4-7:reviewer-default:reviewer").resolved_agent()


# ── Additional regression coverage ─────────────────────────────────────────


def test_wp_field_model_used_when_colon_segment_empty() -> None:
    """When the colon ``model`` slot is empty, fall back to ``WPMetadata.model``."""
    wp = WPMetadata(
        work_package_id="WP01",
        title="Test",
        agent="claude::reviewer-default:reviewer",
        model="frontmatter-model",
    )
    result = wp.resolved_agent()
    # Because no agent registry entry exists for "claude", the
    # WP-level ``model`` field becomes the ``default_model`` source.
    assert result.model == "frontmatter-model"
    assert result.profile_id == "reviewer-default"
    assert result.role == "reviewer"


def test_wp_field_role_used_when_colon_segment_empty() -> None:
    """An empty trailing ``role`` segment falls back to ``WPMetadata.role`` before "implementer"."""
    wp = WPMetadata(
        work_package_id="WP01",
        title="Test",
        agent="claude:opus-4-7:reviewer-default:",
        role="frontmatter-role",
    )
    result = wp.resolved_agent()
    assert result.role == "frontmatter-role"


def test_resolved_agent_returns_agent_assignment_for_colon_format() -> None:
    """Colon-formatted strings still produce an AgentAssignment instance."""
    result = _make_wp("claude:opus-4-7:reviewer-default:reviewer").resolved_agent()
    assert isinstance(result, AgentAssignment)


def test_four_arity_assignment_is_immutable() -> None:
    """The 4-tuple AgentAssignment must remain frozen (no mutation post-resolve)."""
    result = _make_wp("claude:opus-4-7:reviewer-default:reviewer").resolved_agent()
    with pytest.raises((AttributeError, TypeError)):
        result.tool = "other"  # type: ignore[misc]

"""Regression tests for acceptance clarification marker detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.acceptance import _check_needs_clarification

pytestmark = pytest.mark.fast


def test_needs_clarification_ignores_descriptive_prose(tmp_path: Path) -> None:
    """Mentioning the marker syntax in prose is not an unresolved marker."""
    artifact = tmp_path / "research.md"
    artifact.write_text(
        "| Spec marker | Resolution |\n"
        "|-------------|------------|\n"
        "| (no `[NEEDS CLARIFICATION]` markers in spec) | n/a |\n",
        encoding="utf-8",
    )

    assert _check_needs_clarification([artifact]) == []


def test_needs_clarification_flags_canonical_marker(tmp_path: Path) -> None:
    """The acceptance gate still flags real deferred-decision markers."""
    artifact = tmp_path / "spec.md"
    artifact.write_text(
        "The system must choose a queue backend. "
        "[NEEDS CLARIFICATION: choose durable queue] <!-- decision_id: 01KS0ABCDEF0123456789ABCDE -->\n",
        encoding="utf-8",
    )

    assert _check_needs_clarification([artifact]) == [str(artifact)]

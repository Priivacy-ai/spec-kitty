"""Pinning tests for the substantive-plan gate's tolerance of source formats.

WP01 / FR-013 (#1896): ``_has_substantive_technical_context`` must accept a
Technical Context section whose fields are rendered as Markdown bullets
(``- **Language/Version**: ...``) — the exact shape the canonical plan
template emits — not only the un-bulleted ``**Field**: value`` form. A real,
populated bulleted section was previously rejected as non-substantive,
falsely blocking ``setup-plan``.

These tests pin the FIXED behaviour: mutate the peer-field regex back to the
bullet-intolerant form and ``test_bulleted_technical_context_is_substantive``
fails — proving the pin genuinely reproduces #1896.
"""

from __future__ import annotations

import pytest

from specify_cli.missions._substantive import (
    _has_substantive_technical_context,
    describe_technical_context_gap,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# Canonical bulleted Technical Context (real values) — the plan-template shape.
_BULLETED_REAL = """# Implementation Plan

## Technical Context
- **Language/Version**: Python 3.12
- **Primary Dependencies**: typer, rich, ruamel.yaml
- **Testing**: pytest

## Constitution Check
"""

# Bulleted form but every value is still a placeholder → NOT substantive.
_BULLETED_PLACEHOLDERS = """# Implementation Plan

## Technical Context
- **Language/Version**: [e.g., Python 3.12]
- **Primary Dependencies**: [e.g., typer]
- **Testing**: [NEEDS CLARIFICATION]

## Constitution Check
"""

# Real Language/Version but every PEER field is a placeholder → not substantive,
# and the gap reason should name the peer-field shape.
_BULLETED_PEERS_PLACEHOLDER = """# Implementation Plan

## Technical Context
- **Language/Version**: Python 3.12
- **Primary Dependencies**: [e.g., typer]
- **Testing**: [NEEDS CLARIFICATION]

## Constitution Check
"""

# Un-bulleted form (already worked before #1896) — guard against regressing it.
_PLAIN_REAL = """# Implementation Plan

## Technical Context
**Language/Version**: Python 3.12
**Primary Dependencies**: typer, rich

## Constitution Check
"""

# Asterisk-bullet variant (``* **Field**: value``).
_STAR_BULLETED_REAL = """# Implementation Plan

## Technical Context
* **Language/Version**: Python 3.12
* **Primary Dependencies**: typer, rich

## Constitution Check
"""


def test_bulleted_technical_context_is_substantive() -> None:
    """#1896 pin: a real, dash-bulleted Technical Context is substantive."""
    assert _has_substantive_technical_context(_BULLETED_REAL) is True


def test_star_bulleted_technical_context_is_substantive() -> None:
    """The asterisk-bullet rendering is equally tolerated."""
    assert _has_substantive_technical_context(_STAR_BULLETED_REAL) is True


def test_bulleted_placeholders_remain_non_substantive() -> None:
    """Bulleting MUST NOT relax the placeholder filter (no false positives)."""
    assert _has_substantive_technical_context(_BULLETED_PLACEHOLDERS) is False


def test_plain_technical_context_still_substantive() -> None:
    """The pre-#1896 un-bulleted shape keeps passing (no regression)."""
    assert _has_substantive_technical_context(_PLAIN_REAL) is True


def test_describe_gap_none_when_substantive() -> None:
    """No gap is reported for a real bulleted section."""
    assert describe_technical_context_gap(_BULLETED_REAL) is None


def test_describe_gap_names_peer_field_format() -> None:
    """FR-013: real Language/Version but placeholder peers → name the format."""
    reason = describe_technical_context_gap(_BULLETED_PEERS_PLACEHOLDER)
    assert reason is not None
    # The diagnostic must mention the offending peer-field shape.
    assert "peer field" in reason
    assert "bulleted" in reason


def test_describe_gap_names_language_version_when_missing() -> None:
    """A placeholder Language/Version is reported with field-level precision."""
    reason = describe_technical_context_gap(_BULLETED_PLACEHOLDERS)
    assert reason is not None
    assert "Language/Version" in reason


def test_describe_gap_missing_section() -> None:
    """An absent Technical Context section is named explicitly."""
    reason = describe_technical_context_gap("# Plan\n\n## Other\n")
    assert reason is not None
    assert "missing" in reason

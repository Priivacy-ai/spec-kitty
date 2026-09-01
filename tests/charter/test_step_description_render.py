"""WP01 (deliver-loaded-doctrine) — step ``description`` reaches the agent (FR-004).

A procedure/tactic step carries a required ``title`` and an optional
``description``. Before this WP only the ``title`` rendered, so the authored
``description`` — the concrete "how" — never reached the agent through either
the action-doctrine bundle body or the profile-channel inline body. These tests
pin the description onto all three render functions and assert the output is
byte-identical when the description is absent.
"""

from __future__ import annotations

import pytest

from charter.context_renderers.artifact_bodies import (
    _format_inline_procedure_body,
    _format_inline_tactic_body,
)
from charter.context_renderers.profile_sections import format_inline_named_body
from charter.offering.procedures.models import ProcedureStep
from charter.offering.tactics.models import TacticStep

pytestmark = [pytest.mark.fast]

_TITLE = "run the migration"
_DESCRIPTION = "invoke the backfill CLI and confirm every mission gains an id"


class _Procedure:
    """Minimal procedure shape the inline-body formatter reads via ``getattr``."""

    def __init__(self, steps: list[ProcedureStep]) -> None:
        self.name = "backfill"
        self.purpose = "mint ids for legacy missions"
        self.entry_condition = None
        self.exit_condition = None
        self.steps = steps


class _Tactic:
    def __init__(self, steps: list[TacticStep]) -> None:
        self.name = "extract-method"
        self.purpose = "shrink a long function"
        self.steps = steps


def test_procedure_step_description_renders_under_title() -> None:
    body = _format_inline_procedure_body(
        _Procedure([ProcedureStep(title=_TITLE, description=_DESCRIPTION)])
    )

    # FR-004: the description is not a loose substring — it is an 8-space
    # indented sub-line BENEATH the title line, not spliced into it.
    assert f"      - {_TITLE}" in body
    assert f"        {_DESCRIPTION}" in body


def test_tactic_step_description_renders_under_title() -> None:
    body = _format_inline_tactic_body(
        _Tactic([TacticStep(title=_TITLE, description=_DESCRIPTION)])
    )

    assert f"      - {_TITLE}" in body
    assert f"        {_DESCRIPTION}" in body


def test_profile_inline_named_body_renders_description() -> None:
    body = format_inline_named_body(
        _Procedure([ProcedureStep(title=_TITLE, description=_DESCRIPTION)])
    )

    assert f"      - {_TITLE}" in body
    assert f"        {_DESCRIPTION}" in body


def test_procedure_body_byte_identical_when_description_absent() -> None:
    with_none = _format_inline_procedure_body(
        _Procedure([ProcedureStep(title=_TITLE)])
    )
    with_empty = _format_inline_procedure_body(
        _Procedure([ProcedureStep(title=_TITLE, description="   ")])
    )

    assert with_none == with_empty
    # The title line is present; no extra description sub-line was emitted.
    assert f"      - {_TITLE}" in with_none
    assert with_none == with_empty
    step_region = [line for line in with_none if line.startswith("        ")]
    assert step_region == [], "no description sub-line when the description is absent"


def test_tactic_body_byte_identical_when_description_absent() -> None:
    with_none = _format_inline_tactic_body(_Tactic([TacticStep(title=_TITLE)]))
    with_empty = _format_inline_tactic_body(
        _Tactic([TacticStep(title=_TITLE, description="  ")])
    )

    assert with_none == with_empty
    assert [line for line in with_none if line.startswith("        ")] == []


def test_profile_named_body_byte_identical_when_description_absent() -> None:
    with_none = format_inline_named_body(_Procedure([ProcedureStep(title=_TITLE)]))

    assert f"      - {_TITLE}" in with_none
    assert [line for line in with_none if line.startswith("        ")] == []


def test_profile_named_body_titleless_step_uses_description_as_header_once() -> None:
    """A step with a ``description`` but no ``title`` (FR-004 fall-through).

    ``format_inline_named_body`` uses the description AS the ``- <desc>`` header
    line and emits NO 8-space sub-line — the description must appear EXACTLY
    once, never duplicated as both header and indented sub-line.
    """
    body = format_inline_named_body(
        _Procedure([ProcedureStep(title="", description=_DESCRIPTION)])
    )

    # The description stands in as the header line ...
    assert f"      - {_DESCRIPTION}" in body
    # ... exactly once across the whole body ...
    assert body.count(f"      - {_DESCRIPTION}") == 1
    # ... and never also as an 8-space sub-line duplicate.
    assert f"        {_DESCRIPTION}" not in body
    assert [line for line in body if line.startswith("        ")] == []

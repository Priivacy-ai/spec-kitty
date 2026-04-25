"""Retrospective-marker check (R-001).

A custom mission template MUST declare its final :class:`PromptStep` with
``id == "retrospective"`` so future tranches (#506-#511) can attach
execution semantics by step id without breaking v1 mission YAML.
"""

from __future__ import annotations

from specify_cli.next._internal_runtime.schema import MissionTemplate

#: Stable step id that marks a custom mission's retrospective step.
RETROSPECTIVE_MARKER_ID: str = "retrospective"


def has_retrospective_marker(template: MissionTemplate) -> bool:
    """Return ``True`` iff the template's last step has the retrospective id.

    Exactly one rule: ``template.steps[-1].id == "retrospective"``. Templates
    with no steps at all return ``False``. The marker MUST be the last step;
    earlier occurrences of an id == "retrospective" do not satisfy the rule.
    """
    if not template.steps:
        return False
    last_id: str = template.steps[-1].id
    return last_id == RETROSPECTIVE_MARKER_ID


__all__ = [
    "RETROSPECTIVE_MARKER_ID",
    "has_retrospective_marker",
]

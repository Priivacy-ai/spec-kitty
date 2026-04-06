"""Review subsystem for spec-kitty.

Provides arbiter checklist and rationale model for false-positive review
rejections.  See :mod:`specify_cli.review.arbiter` for the full API.
"""

from .arbiter import (
    ArbiterCategory,
    ArbiterChecklist,
    ArbiterDecision,
    _derive_category,
    _is_arbiter_override,
    create_arbiter_decision,
    get_arbiter_overrides_for_wp,
    parse_category_from_note,
    persist_arbiter_decision,
    prompt_arbiter_checklist,
)

__all__ = [
    "ArbiterCategory",
    "ArbiterChecklist",
    "ArbiterDecision",
    "create_arbiter_decision",
    "get_arbiter_overrides_for_wp",
    "parse_category_from_note",
    "persist_arbiter_decision",
    "prompt_arbiter_checklist",
    # private but useful for testing
    "_derive_category",
    "_is_arbiter_override",
]

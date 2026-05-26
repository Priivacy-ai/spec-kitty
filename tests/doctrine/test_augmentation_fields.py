"""Cross-field validator for ``overrides``/``enhances`` on doctrine artifact kinds.

Consolidates the per-kind augmentation-field test files (LD-2 in the
2026-05-25 architectural review). The parametrisation matrix encodes one row
per artifact kind; each row supplies:

* the model class under test,
* a minimal valid sample-YAML dict (the same shape used by the per-kind tests
  this file replaces),
* the artifact ``id`` (or ``profile_id``) used by the validator's error
  message, and
* the kind label embedded in that same error message.

All five kinds share the identical four-case matrix:

* neither field set         → backward compatibility, model loads cleanly.
* ``enhances`` only         → pack author declares augmentation intent.
* ``overrides`` only        → pack author declares replacement intent.
* both fields set together  → cross-field validator raises ``ValidationError``.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from doctrine.agent_profiles.profile import AgentProfile, Specialization
from doctrine.paradigms.models import Paradigm
from doctrine.procedures.models import Procedure, ProcedureStep
from doctrine.styleguides.models import Styleguide
from doctrine.tactics.models import Tactic, TacticStep

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


# Each row: (model_class, minimal-valid sample dict, artifact id, kind label in error message).
# The kind label matches the literal wording produced by each model's
# ``_augmentation_intent_is_exclusive`` validator -- in particular note that
# ``AgentProfile`` uses ``"agent profile"`` (with a space) and ``profile_id``
# rather than ``id`` for the artifact identifier substitution.
AUGMENTATION_MATRIX: list[Any] = [
    pytest.param(
        Tactic,
        {
            "schema_version": "1.0",
            "id": "test-tactic",
            "name": "Test Tactic",
            "steps": [TacticStep(title="Step One")],
        },
        "test-tactic",
        "tactic",
        id="tactic",
    ),
    pytest.param(
        Styleguide,
        {
            "schema_version": "1.0",
            "id": "test-style",
            "title": "Test Styleguide",
            "scope": "code",
            "principles": ["Write clear code"],
        },
        "test-style",
        "styleguide",
        id="styleguide",
    ),
    pytest.param(
        Paradigm,
        {
            "schema_version": "1.0",
            "id": "test-paradigm",
            "name": "Test Paradigm",
            "summary": "A test paradigm.",
        },
        "test-paradigm",
        "paradigm",
        id="paradigm",
    ),
    pytest.param(
        Procedure,
        {
            "schema_version": "1.0",
            "id": "test-procedure",
            "name": "Test Procedure",
            "purpose": "Test mutually-exclusive augmentation fields.",
            "entry_condition": "Test entry.",
            "exit_condition": "Test exit.",
            "steps": [ProcedureStep(title="Step One")],
        },
        "test-procedure",
        "procedure",
        id="procedure",
    ),
    pytest.param(
        AgentProfile,
        {
            "profile_id": "test-profile",
            "name": "Test Profile",
            "purpose": "Validate augmentation field semantics.",
            "specialization": Specialization(primary_focus="Testing"),
            "roles": ["implementer"],
        },
        "test-profile",
        "agent profile",
        id="agent_profile",
    ),
]


@pytest.mark.parametrize("model_cls, sample, artifact_id, kind", AUGMENTATION_MATRIX)
def test_neither_field_set_loads(
    model_cls: type, sample: dict[str, Any], artifact_id: str, kind: str
) -> None:
    """Backward compatibility (NFR-004): existing fixtures keep loading."""
    instance = model_cls(**sample)
    assert instance.overrides is None
    assert instance.enhances is None


@pytest.mark.parametrize("model_cls, sample, artifact_id, kind", AUGMENTATION_MATRIX)
def test_enhances_only_loads(
    model_cls: type, sample: dict[str, Any], artifact_id: str, kind: str
) -> None:
    """Pack author declares augmentation intent."""
    instance = model_cls(**{**sample, "enhances": f"builtin-{kind}-id"})
    assert instance.enhances == f"builtin-{kind}-id"
    assert instance.overrides is None


@pytest.mark.parametrize("model_cls, sample, artifact_id, kind", AUGMENTATION_MATRIX)
def test_overrides_only_loads(
    model_cls: type, sample: dict[str, Any], artifact_id: str, kind: str
) -> None:
    """Pack author declares replacement intent."""
    instance = model_cls(**{**sample, "overrides": f"builtin-{kind}-id"})
    assert instance.overrides == f"builtin-{kind}-id"
    assert instance.enhances is None


@pytest.mark.parametrize("model_cls, sample, artifact_id, kind", AUGMENTATION_MATRIX)
def test_both_set_raises_mutually_exclusive(
    model_cls: type, sample: dict[str, Any], artifact_id: str, kind: str
) -> None:
    """Mutual exclusion -- the validator must reject both fields set together.

    The error message must include the canonical wording (``mutually exclusive``)
    so operators can grep their logs, the artifact identifier so they know which
    YAML to edit, and the kind label so the surface is unambiguous when multiple
    artifact kinds appear in the same validation batch.
    """
    with pytest.raises(ValidationError) as exc_info:
        model_cls(**{**sample, "overrides": "foo", "enhances": "bar"})
    message = str(exc_info.value)
    assert "mutually exclusive" in message
    assert artifact_id in message
    assert kind in message

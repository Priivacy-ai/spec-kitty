"""Architectural guard — activation registry schema (context-scoped mode).

Mission B WP05 introduces the charter-level *activation registry*:

    activations:
      - activation_context:
          mission_type: software-dev
          action: implement
        doctrine_pack_id: very-serious-developers
        artifact_id: caveman-comments
        artifact_kind: styleguide

This file pins the tuple shape and the closed vocabularies for
``mission_type`` and ``action``. Without these vocabularies fixed in
one place, the activation registry would drift (artifact-author A uses
``mission_type: dev``, artifact-author B uses ``mission_type: software``,
prompt builder matches nothing).

See ``docs/development/doctrine-artifact-selection-preflight.md`` →
"Two activation modes — global vs context-scoped", and
``docs/development/mission-b-proposed-scope.md`` → WP05.

Expected status TODAY: every test FAILS on ``ImportError`` (the
``charter.activations`` module does not exist) or on the missing
schema. Mission B WP05 must create the module and the schema.

Expected status AFTER Mission B WP05: PASS.
"""

from __future__ import annotations

import pytest


pytestmark = [pytest.mark.architectural]


# Canonical vocabulary the registry must enforce. Mirrors the proposed-scope
# document's Pre-conditions §2 ("Decide on the activation_context vocabulary").
_EXPECTED_MISSION_TYPES: frozenset[str] = frozenset(
    {"software-dev", "documentation", "research", "plan", "any", "generic"}
)
_EXPECTED_ACTIONS: frozenset[str] = frozenset(
    {
        # Mission-type verbs (the prompt builder emits these as action labels).
        "specify",
        "plan",
        "tasks",
        "implement",
        "review",
        "merge",
        "accept",
        # Charter-loop verbs (charter context resolution itself is an action).
        "charter.interview",
        "charter.generate",
        "charter.context",
    }
)


def test_activation_entry_schema_exists_and_carries_required_fields() -> None:
    """``charter.activations.ActivationEntry`` MUST exist with the four
    canonical fields: ``activation_context`` (dict[str, str]),
    ``doctrine_pack_id`` (str), ``artifact_id`` (str), and an optional
    ``artifact_kind`` (str).

    Fails today with ``ImportError`` because Mission B WP05 has not
    landed. The import location is assumed to be ``charter.activations`` —
    if Mission B chooses a different module location, update this test
    to match (and document the change in the WP05 spec).
    """
    try:
        from charter.activations import ActivationEntry  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            "Could not import `charter.activations.ActivationEntry`. "
            "Mission B WP05 must introduce the activation registry surface "
            "at this canonical import path so artifacts authors / pack "
            "authors have one place to look. See "
            "docs/development/mission-b-proposed-scope.md → WP05.\n"
            f"Underlying ImportError: {exc!r}"
        )

    model_fields = getattr(ActivationEntry, "model_fields", None)
    assert model_fields is not None, (
        "ActivationEntry should be a Pydantic model so the schema is "
        "introspectable (and the YAML loader can validate). "
        f"Observed type without `model_fields`: {type(ActivationEntry).__name__}"
    )
    required_field_names = {"activation_context", "doctrine_pack_id", "artifact_id"}
    missing = required_field_names - set(model_fields)
    assert not missing, (
        f"ActivationEntry is missing required fields: {sorted(missing)}. "
        "Canonical shape (per the pre-flight 'Two activation modes' table):\n"
        "  - activation_context: dict[str, str]   # {mission_type?, action?}\n"
        "  - doctrine_pack_id:   str              # which pack to fetch from\n"
        "  - artifact_id:        str              # id of the artifact to fetch\n"
        "  - artifact_kind:      str | None       # optional disambiguator\n"
    )
    assert "artifact_kind" in model_fields, (
        "ActivationEntry MUST expose an optional `artifact_kind` field so "
        "two artifacts that share an id across kinds (rare but legal) can "
        "be disambiguated by the resolver. See pre-flight Case 1 step 5."
    )


def test_activation_context_mission_type_vocabulary_is_closed() -> None:
    """``activation_context.mission_type`` MUST be one of the canonical mission
    types or the wildcard ``any`` / ``generic`` token. The vocabulary lives
    in one place so artifact authors / pack authors / prompt builder agree.

    Fails today on ImportError. Mission B WP05 ships the vocabulary as
    an enum / Literal that pytest can compare against
    ``_EXPECTED_MISSION_TYPES``.
    """
    try:
        from charter.activations import ALLOWED_MISSION_TYPES  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            "`charter.activations.ALLOWED_MISSION_TYPES` is not defined. "
            "Mission B WP05 must expose the canonical mission-type vocabulary "
            "for the activation registry — either as a frozenset constant "
            "or as the membership set of a Literal type — so this test can "
            "compare it against the expected vocabulary.\n"
            f"Expected vocabulary: {sorted(_EXPECTED_MISSION_TYPES)}\n"
            f"Underlying ImportError: {exc!r}"
        )

    observed = frozenset(ALLOWED_MISSION_TYPES)
    missing = _EXPECTED_MISSION_TYPES - observed
    extra = observed - _EXPECTED_MISSION_TYPES
    assert not missing and not extra, (
        "ALLOWED_MISSION_TYPES drifted from the canonical vocabulary.\n"
        f"  missing (expected but not declared): {sorted(missing)}\n"
        f"  extra   (declared but not expected): {sorted(extra)}\n"
        f"  expected: {sorted(_EXPECTED_MISSION_TYPES)}\n"
        f"  observed: {sorted(observed)}\n"
        "If Mission B intentionally widens / narrows the vocabulary, update "
        "this test in lockstep AND amend mission-b-proposed-scope.md."
    )


def test_activation_context_action_vocabulary_is_closed() -> None:
    """``activation_context.action`` MUST be one of the canonical mission-type
    verbs (specify / plan / tasks / implement / review / merge / accept) or
    one of the charter-loop verbs (charter.interview / .generate / .context).

    Fails today on ImportError. Mission B WP05 ships the vocabulary in the
    same surface as the mission-type vocabulary so the registry is fully
    closed.
    """
    try:
        from charter.activations import ALLOWED_ACTIONS  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            "`charter.activations.ALLOWED_ACTIONS` is not defined. "
            "Mission B WP05 must expose the canonical action vocabulary "
            "alongside ALLOWED_MISSION_TYPES.\n"
            f"Expected vocabulary: {sorted(_EXPECTED_ACTIONS)}\n"
            f"Underlying ImportError: {exc!r}"
        )

    observed = frozenset(ALLOWED_ACTIONS)
    missing = _EXPECTED_ACTIONS - observed
    extra = observed - _EXPECTED_ACTIONS
    assert not missing and not extra, (
        "ALLOWED_ACTIONS drifted from the canonical vocabulary.\n"
        f"  missing (expected but not declared): {sorted(missing)}\n"
        f"  extra   (declared but not expected): {sorted(extra)}\n"
        f"  expected: {sorted(_EXPECTED_ACTIONS)}\n"
        f"  observed: {sorted(observed)}\n"
    )


def test_activation_entry_validates_membership_of_vocabulary() -> None:
    """Constructing an ``ActivationEntry`` with a non-vocabulary ``mission_type``
    or ``action`` MUST raise a validation error — not silently store the
    typo. Pydantic's Literal validation is the simplest implementation.

    Fails today on ImportError; after Mission B WP05, ensures the
    vocabulary closure is *enforced*, not just *declared*.
    """
    try:
        from charter.activations import ActivationEntry  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            "Cannot test ActivationEntry validation: import failed. "
            "Land the schema first (see prior tests).\n"
            f"Underlying ImportError: {exc!r}"
        )

    # A clearly-invalid mission_type should be rejected.
    from pydantic import ValidationError

    with pytest.raises((ValidationError, ValueError)):
        ActivationEntry(
            activation_context={"mission_type": "not-a-real-mission-type", "action": "implement"},
            doctrine_pack_id="project",
            artifact_id="caveman-comments",
        )

    # An invalid action should also be rejected.
    with pytest.raises((ValidationError, ValueError)):
        ActivationEntry(
            activation_context={"mission_type": "software-dev", "action": "not-a-real-action"},
            doctrine_pack_id="project",
            artifact_id="caveman-comments",
        )

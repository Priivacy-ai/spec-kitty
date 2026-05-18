"""Architectural guard — trigger registry coverage.

Every ``triggers:`` value declared in a shipped doctrine artifact MUST
appear in the canonical agent-action registry (``_REGISTERED_TRIGGERS``
below). The registry is the runtime's known vocabulary of agent
actions that the prompt builder can emit conditional fetch stanzas
for; a dangling trigger declared in an artifact but unknown to the
prompt builder is a *dead trigger* — the conditional rule would never
appear in any prompt, no matter what mission ran.

Today there are **no** ``triggers:`` declarations in shipped artifacts
(``src/doctrine/**/*.yaml``), so this test passes trivially. The
registry is intentionally an empty ``frozenset()`` placeholder; Mission
B WP05 must:

1. Define the canonical trigger vocabulary (e.g. ``write_comment``,
   ``write_docstring``, ``rename_identifier``, ``add_dependency``,
   ``review_diff``, ...). The list lives in this file's
   ``_REGISTERED_TRIGGERS`` constant so the registry has exactly one
   home that's gate-protected.
2. Wire the prompt builder to emit per-trigger fetch stanzas when an
   artifact's trigger matches an action the agent is about to take.
3. Author the first artifacts that actually declare ``triggers:``.

The moment step 3 lands without step 1, this test fails — preventing
silent dead-trigger drift.

See ``docs/development/doctrine-artifact-selection-preflight.md`` →
"Edge case 6: Trigger registry mismatch", and
``docs/development/mission-b-proposed-scope.md`` → WP05.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML


pytestmark = [pytest.mark.architectural]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCTRINE_ROOT = _REPO_ROOT / "src" / "doctrine"


# ---------------------------------------------------------------------------
# Canonical trigger registry  (data-model.md §7 — SINGLE SOURCE OF TRUTH)
# ---------------------------------------------------------------------------
#
# Per data-model.md §7 ("Trigger Registry (FR-009) — CANONICAL DEFINITION"),
# this file is the canonical home for both vocabularies.  The runtime
# re-exports under ``charter.activations`` (``ALLOWED_ACTIONS`` and
# ``REGISTERED_TRIGGERS``) MUST be byte-identical to the constants below
# — pinned by ``test_trigger_registry_runtime_export_in_sync``.
#
# 10-token operator-side action vocabulary for ``activation_context.action``
# in operator-authored ``activations:`` blocks (charter, org-pack,
# mission-type profile).  Mission-type verbs + charter-loop verbs.
_ALLOWED_ACTIONS: frozenset[str] = frozenset(
    {
        # Mission-type verbs
        "specify",
        "plan",
        "tasks",
        "implement",
        "review",
        "merge",
        "accept",
        # Charter-loop verbs
        "charter.interview",
        "charter.generate",
        "charter.context",
    }
)

# Union formula (the ONLY place this formula appears in code):
#   _REGISTERED_TRIGGERS = _ALLOWED_ACTIONS ∪ {fine-grained tokens}
#
# Fine-grained tokens describe agent sub-actions that may occur during
# ANY mission verb (e.g. ``write_comment`` happens during implement,
# review, and the charter loop).  They are NOT in ``_ALLOWED_ACTIONS``
# because they cannot stand alone as a mission verb, but they ARE valid
# operator-authored tokens for ``activation_context.action`` per the
# wider validator in ``charter.activations`` (see data-model.md §7's
# mutation rule).
_REGISTERED_TRIGGERS: frozenset[str] = _ALLOWED_ACTIONS | frozenset(
    {
        "write_comment",
        "write_docstring",
        "rename_identifier",
        "add_dependency",
    }
)


def _iter_doctrine_yaml_files() -> list[Path]:
    """Yield every ``*.yaml`` under ``src/doctrine/``."""
    return sorted(_DOCTRINE_ROOT.rglob("*.yaml"))


def _extract_trigger_values(data: object) -> set[str]:
    """Recursively collect every value from any ``triggers:`` list in ``data``."""
    found: set[str] = set()
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "triggers" and isinstance(value, list):
                for entry in value:
                    if isinstance(entry, str) and entry.strip():
                        found.add(entry.strip())
                    elif isinstance(entry, dict):
                        # Allow {name: write_comment, scope: ...} shapes.
                        name = entry.get("name") or entry.get("action")
                        if isinstance(name, str) and name.strip():
                            found.add(name.strip())
            else:
                found |= _extract_trigger_values(value)
    elif isinstance(data, list):
        for item in data:
            found |= _extract_trigger_values(item)
    return found


def _safe_load_yaml(path: Path) -> object | None:
    yaml = YAML(typ="safe")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.strip():
        return None
    try:
        return yaml.load(text)
    except Exception:  # noqa: BLE001 — parse errors don't speak to this rule
        return None


def test_every_declared_trigger_is_in_the_registered_set() -> None:
    """A shipped artifact MAY declare ``triggers:`` only with values in
    ``_REGISTERED_TRIGGERS``. Any other value is a dead trigger.

    Today this test passes vacuously (no triggers declared). It is the
    architectural barrier that prevents Mission B WP05 from shipping
    artifacts that declare triggers the prompt builder cannot emit.
    """
    offenders: dict[str, set[str]] = {}
    for yaml_path in _iter_doctrine_yaml_files():
        data = _safe_load_yaml(yaml_path)
        if data is None:
            continue
        declared = _extract_trigger_values(data)
        if not declared:
            continue
        unknown = declared - _REGISTERED_TRIGGERS
        if unknown:
            offenders[str(yaml_path.relative_to(_REPO_ROOT))] = unknown

    if offenders:
        details = "\n".join(
            f"  - {path}: unknown triggers {sorted(values)}"
            for path, values in sorted(offenders.items())
        )
        pytest.fail(
            "Dead-trigger declarations detected. The following shipped "
            "artifacts declare `triggers:` values that are NOT in the "
            "canonical agent-action registry (`_REGISTERED_TRIGGERS` in "
            "this test file). Each unknown trigger means the conditional "
            "fetch stanza would never appear in any prompt:\n"
            f"{details}\n\n"
            f"Currently registered triggers: {sorted(_REGISTERED_TRIGGERS)}\n\n"
            "Fix: either (a) add the trigger value to `_REGISTERED_TRIGGERS` "
            "in tests/architectural/test_trigger_registry_coverage.py AND "
            "teach the prompt builder to emit fetch stanzas for that "
            "action (Mission B WP05), or (b) correct the artifact to use "
            "an already-registered trigger value. See "
            "docs/development/mission-b-proposed-scope.md → WP05."
        )


def test_registered_triggers_constant_is_a_frozenset_for_immutability() -> None:
    """``_REGISTERED_TRIGGERS`` MUST be a frozenset.

    This is a defence-in-depth check: a mutable set would let a test or
    a helper accidentally extend the registry at runtime, defeating the
    architectural rule. The test is cheap and obvious, so we keep it.
    """
    assert isinstance(_REGISTERED_TRIGGERS, frozenset), (
        "_REGISTERED_TRIGGERS must be a frozenset to prevent runtime mutation. "
        f"Observed type: {type(_REGISTERED_TRIGGERS).__name__}"
    )


def test_allowed_actions_constant_is_a_frozenset_for_immutability() -> None:
    """``_ALLOWED_ACTIONS`` MUST be a frozenset (same rationale as the
    sibling check for ``_REGISTERED_TRIGGERS``)."""
    assert isinstance(_ALLOWED_ACTIONS, frozenset), (
        "_ALLOWED_ACTIONS must be a frozenset to prevent runtime mutation. "
        f"Observed type: {type(_ALLOWED_ACTIONS).__name__}"
    )


def test_registered_triggers_is_strict_superset_of_allowed_actions() -> None:
    """Per the union formula in data-model.md §7,
    ``_REGISTERED_TRIGGERS = _ALLOWED_ACTIONS ∪ {fine-grained tokens}`` —
    so every action MUST be a registered trigger, and the trigger set
    MUST contain at least one fine-grained token not in the action set.

    Pinning this here keeps the two vocabularies from accidentally
    diverging in a future refactor (e.g. someone moving ``implement``
    out of ``_ALLOWED_ACTIONS`` without also removing it from
    ``_REGISTERED_TRIGGERS``).
    """
    assert _ALLOWED_ACTIONS <= _REGISTERED_TRIGGERS, (
        "_REGISTERED_TRIGGERS must be a superset of _ALLOWED_ACTIONS per "
        "the union formula in data-model.md §7. Missing from triggers: "
        f"{sorted(_ALLOWED_ACTIONS - _REGISTERED_TRIGGERS)}"
    )
    fine_grained = _REGISTERED_TRIGGERS - _ALLOWED_ACTIONS
    assert fine_grained, (
        "_REGISTERED_TRIGGERS must contain at least one fine-grained "
        "token beyond _ALLOWED_ACTIONS. Today the canonical set is "
        "{write_comment, write_docstring, rename_identifier, "
        "add_dependency} — see data-model.md §7."
    )


def test_trigger_registry_runtime_export_in_sync() -> None:
    """Cross-check: the runtime re-export in :mod:`charter.activations`
    MUST be byte-identical to the canonical frozensets in this file.

    Pinning this eliminates the copy/paste-drift risk identified in
    ``analysis-report.md`` finding A1 (Trigger Registry vs Activation
    Vocabulary drift).  Per data-model.md §7 "MANDATORY runtime
    re-export", the runtime contract is that the two pairs are
    byte-identical ``frozenset[str]`` instances at import time — this
    test is the architectural gate that enforces that contract.

    If this test fails, do NOT edit the runtime constants directly.
    The canonical home is THIS file (per data-model.md §7).  Either:

    1. Update ``_ALLOWED_ACTIONS`` / ``_REGISTERED_TRIGGERS`` here AND
       teach ``charter.activations`` to import / re-export the new
       values (typical case — adding a new trigger token).
    2. Investigate why the runtime is diverging from the canonical
       vocabulary (regression case — fix the import path / re-export).
    """
    from charter.activations import ALLOWED_ACTIONS, REGISTERED_TRIGGERS

    assert isinstance(ALLOWED_ACTIONS, frozenset), (
        "charter.activations.ALLOWED_ACTIONS must be a frozenset "
        f"(observed type: {type(ALLOWED_ACTIONS).__name__})."
    )
    assert isinstance(REGISTERED_TRIGGERS, frozenset), (
        "charter.activations.REGISTERED_TRIGGERS must be a frozenset "
        f"(observed type: {type(REGISTERED_TRIGGERS).__name__})."
    )
    assert ALLOWED_ACTIONS == _ALLOWED_ACTIONS, (
        "charter.activations.ALLOWED_ACTIONS drifted from the canonical "
        "_ALLOWED_ACTIONS in test_trigger_registry_coverage.py. "
        "See data-model.md §7 for the SSOT contract.\n"
        f"  missing from runtime: {sorted(_ALLOWED_ACTIONS - ALLOWED_ACTIONS)}\n"
        f"  extra in runtime:     {sorted(ALLOWED_ACTIONS - _ALLOWED_ACTIONS)}"
    )
    assert REGISTERED_TRIGGERS == _REGISTERED_TRIGGERS, (
        "charter.activations.REGISTERED_TRIGGERS drifted from the canonical "
        "_REGISTERED_TRIGGERS in test_trigger_registry_coverage.py. "
        "See data-model.md §7 for the SSOT contract.\n"
        f"  missing from runtime: {sorted(_REGISTERED_TRIGGERS - REGISTERED_TRIGGERS)}\n"
        f"  extra in runtime:     {sorted(REGISTERED_TRIGGERS - _REGISTERED_TRIGGERS)}"
    )

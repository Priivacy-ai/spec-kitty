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


# Canonical agent-action registry. Populated by Mission B WP05 with the
# trigger vocabulary the prompt builder understands. Today the registry
# is empty — and so are the artifacts. WP05 must extend BOTH together.
_REGISTERED_TRIGGERS: frozenset[str] = frozenset()


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

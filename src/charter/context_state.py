"""First-load context-state bookkeeping (WP04 T021, #2532).

Relocated verbatim from ``charter.context`` (single-owner, no-net-growth for
that file). Local ``.kittify/charter/context-state.json`` read/write plus the
depth-reconciliation logic that decides whether a render is a first load.

``KITTIFY_DIRNAME`` and ``_MIN_EFFECTIVE_DEPTH`` moved along with
``_prepare_context_state`` (their only two call sites besides
``charter.context`` itself, which re-imports both — a declared, coupled
out-of-map edit: the alternative was a reverse import from this leaf back
into ``context.py``, which would re-form an import cycle).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from kernel.atomic import atomic_write
from kernel.clock import now_utc_stamp

# ``_load_state`` / ``_write_state`` / ``_ContextStateBundle`` are intentionally
# *not* exported: after the context.py re-export shim retirement
# (doctrine-built-in-seam-consolidation WP06) their only importer (the shim) was
# removed, so they have no external ``src/`` importer and would trip the
# symbol-level dead-code gate. They remain live module-internal helpers (used by
# the state-load/save functions below); re-export them here once a real external
# consumer imports them.
__all__ = [
    "KITTIFY_DIRNAME",
    "_MIN_EFFECTIVE_DEPTH",
    "_mark_action_loaded",
    "_prepare_context_state",
]


KITTIFY_DIRNAME = ".kittify"

_MIN_EFFECTIVE_DEPTH = 2  # minimum depth for bootstrap context (full summary + references)
# WP11 (T059) retired ``_EXTENDED_CONTEXT_DEPTH``: ``depth`` is now purely the
# DRG suggests-hop cap, not also a render-verbosity tier (which gated
# styleguides/toolguides out at every delivered depth).


@dataclass(frozen=True)
class _ContextStateBundle:
    """First-load state bundle used while rendering charter context."""

    state_path: Path
    state: dict[str, object]
    first_load: bool
    effective_depth: int


def _load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"schema_version": "1.0.0", "actions": {}}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {"schema_version": "1.0.0", "actions": {}}

    if not isinstance(data, dict):
        return {"schema_version": "1.0.0", "actions": {}}

    actions = data.get("actions")
    if not isinstance(actions, dict):
        data["actions"] = {}

    return data


def _write_state(path: Path, state: dict[str, object]) -> None:
    atomic_write(path, json.dumps(state, indent=2, sort_keys=True), mkdir=True)


def _mark_action_loaded(state: dict[str, object], state_path: Path, action: str) -> None:
    """Persist first-load timestamp for *action* into context-state.json."""
    actions_obj = state.setdefault("actions", {})
    if not isinstance(actions_obj, dict):
        actions_obj = {}
        state["actions"] = actions_obj
    actions_obj[action] = now_utc_stamp()
    _write_state(state_path, state)


def _prepare_context_state(
    repo_root: Path,
    action: str,
    depth: int | None,
) -> _ContextStateBundle:
    """Resolve first-load state and effective context depth."""
    state_path = repo_root / KITTIFY_DIRNAME / "charter" / "context-state.json"
    state = _load_state(state_path)
    actions_val = state.get("actions", {})
    first_load = action not in actions_val if isinstance(actions_val, dict) else True
    if depth is not None:
        effective_depth = depth
    elif first_load:
        effective_depth = _MIN_EFFECTIVE_DEPTH
    else:
        effective_depth = 1
    return _ContextStateBundle(
        state_path=state_path,
        state=state,
        first_load=first_load,
        effective_depth=effective_depth,
    )

"""SPDD/REASONS pack activation detection.

Single source of truth for "is the SPDD/REASONS doctrine pack active for this
project?". The helper inspects the project's resolved charter selection
(IC-04 / WP04: ``.kittify/charter/charter.yaml``'s ``governance:`` and
``directives:`` sections -- the retired ``governance.yaml`` /
``directives.yaml`` triad files) and returns ``True`` iff at least one of the
four selectors is present:

- paradigm ``structured-prompt-driven-development``
- tactic ``reasons-canvas-fill``
- tactic ``reasons-canvas-review``
- directive ``DIRECTIVE_038``

Failure modes (per ``contracts/activation.md``):

- Missing ``.kittify/charter/`` → returns ``False`` (not an error).
- Malformed YAML → propagates the loader exception (``YAMLError``).
- No paradigms section → returns ``False``.

A small per-process cache keyed on the resolved charter.yaml path is used to
amortise the cost of repeated calls within a single CLI invocation. The cache
is invalidated whenever the file's mtime changes, and is never persisted to
disk. ``clear_activation_cache()`` is exposed for tests.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

PARADIGM_ID = "structured-prompt-driven-development"
TACTIC_FILL_ID = "reasons-canvas-fill"
TACTIC_REVIEW_ID = "reasons-canvas-review"
DIRECTIVE_ID = "DIRECTIVE_038"
DIRECTIVE_NUMERIC_HINT = "038"

_KITTIFY = ".kittify"
_CHARTER = "charter"
# IC-04 (WP04): the retired ``governance.yaml`` / ``directives.yaml`` triad
# files are replaced by the single git-tracked ``charter.yaml``'s
# ``governance:`` / ``directives:`` sections. This module MUST NOT import
# ``charter`` (layer rule: ``kernel <- doctrine <- charter <- specify_cli``),
# so the filename is a local literal rather than
# ``charter.bundle.CHARTER_YAML``.
_CHARTER_YAML = "charter.yaml"

# Per-process cache. Keyed by ``str(charter_yaml_path)`` -> ``(mtime_ns, result)``.
# Never persisted; cleared on test boundary via ``clear_activation_cache``.
_cache: dict[str, tuple[int, bool]] = {}


def clear_activation_cache() -> None:
    """Clear the in-process activation cache. Test-only helper."""
    _cache.clear()


def is_spdd_reasons_active(repo_root: Path) -> bool:
    """Return True iff the SPDD/REASONS pack is active for the given project.

    Activation is a disjunction of four selectors (paradigm, two tactics,
    directive). Charter selection lives in ``.kittify/charter/``; if that
    directory is absent, returns ``False`` without raising.

    Loader exceptions (e.g. malformed YAML) propagate unchanged so callers see
    the same error surface as existing charter loaders.

    The helper reads the charter bundle directly from disk under
    ``<repo_root>/.kittify/charter/``. Bundle freshness is the responsibility
    of upstream charter-context callers (which have their own freshness
    machinery via ``_load_action_doctrine_bundle``); this helper does not
    import the ``charter`` layer (architectural rule:
    ``kernel <- doctrine <- charter <- specify_cli``).
    """
    charter_dir = repo_root / _KITTIFY / _CHARTER
    if not charter_dir.exists():
        return False

    charter_yaml_path = charter_dir / _CHARTER_YAML

    cache_key = str(charter_yaml_path.resolve()) if charter_yaml_path.exists() else str(charter_yaml_path)
    mtime = charter_yaml_path.stat().st_mtime_ns if charter_yaml_path.exists() else 0

    cached = _cache.get(cache_key)
    if cached is not None and cached[0] == mtime:
        return cached[1]

    result = _compute_active(charter_yaml_path)
    _cache[cache_key] = (mtime, result)
    return result


def _compute_active(charter_yaml_path: Path) -> bool:
    """Compute activation by inspecting charter.yaml's governance/directives."""
    if not charter_yaml_path.exists():
        return False

    data = _load_yaml(charter_yaml_path)
    if not isinstance(data, dict):
        return False

    if _governance_selects_pack(data.get("governance")):
        return True
    if _directives_select_pack(data.get("directives")):
        return True
    return False


def _governance_selects_pack(governance: Any) -> bool:
    """Inspect charter.yaml's ``governance:`` section for any SPDD/REASONS selector."""
    if not isinstance(governance, dict):
        return False

    doctrine = governance.get("doctrine")
    if not isinstance(doctrine, dict):
        return False

    paradigms = _coerce_str_list(doctrine.get("selected_paradigms"))
    if PARADIGM_ID in paradigms:
        return True

    # ``selected_tactics`` is not part of the formal Pydantic schema today, but
    # we read it as a raw key so projects (or future schema additions) that
    # carry tactic selections are detected without a schema change.
    tactics = _coerce_str_list(doctrine.get("selected_tactics"))
    if TACTIC_FILL_ID in tactics or TACTIC_REVIEW_ID in tactics:
        return True

    directives = _coerce_str_list(doctrine.get("selected_directives"))
    if _directive_id_matches(directives):
        return True

    return False


def _directives_select_pack(directives: Any) -> bool:
    """Inspect charter.yaml's ``directives:`` section for ``DIRECTIVE_038`` (or ``038-`` slug)."""
    if not isinstance(directives, dict):
        return False

    raw = directives.get("directives")
    if not isinstance(raw, list):
        return False

    for entry in raw:
        if isinstance(entry, dict):
            entry_id = entry.get("id")
            if isinstance(entry_id, str) and _is_directive_038(entry_id):
                return True
        elif isinstance(entry, str) and _is_directive_038(entry):
            return True

    return False


def _directive_id_matches(directives: list[str]) -> bool:
    """Return True if any directive id in *directives* maps to DIRECTIVE_038."""
    return any(_is_directive_038(d) for d in directives)


def _is_directive_038(raw: str) -> bool:
    """Match ``DIRECTIVE_038`` or any slug carrying the ``038`` numeric hint."""
    if raw == DIRECTIVE_ID:
        return True
    # Accept short forms like '038' or '038-structured-prompt-boundary'.
    match = re.match(r"^(\d+)", raw)
    if match and match.group(1).zfill(3) == DIRECTIVE_NUMERIC_HINT:
        return True
    if raw.upper() == DIRECTIVE_ID.upper():
        return True
    return False


def _coerce_str_list(raw: Any) -> list[str]:
    """Coerce *raw* to ``list[str]`` while ignoring non-string entries."""
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if isinstance(item, (str, int))]


def _load_yaml(path: Path) -> Any:
    """Load YAML from *path*. Loader exceptions propagate (FR-007)."""
    yaml = YAML(typ="safe")
    return yaml.load(path.read_text(encoding="utf-8"))

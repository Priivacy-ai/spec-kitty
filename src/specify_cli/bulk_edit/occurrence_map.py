"""Occurrence map schema, loading, validation, and admissibility checking.

An occurrence map is a YAML file that describes how a bulk rename/remove/deprecate
operation should be classified across different occurrence categories. Each category
carries an ``action`` that tells the executor how to handle occurrences of that kind.

The canonical schema lives in ``src/doctrine/schemas/occurrence-map.schema.yaml``
and the user-facing starter template lives in
``src/doctrine/templates/occurrence-map-template.yaml``. Both are loaded at import
time via :mod:`doctrine.shared.schema_utils` so the constants below stay in lock
step with the published schema — there is no second source of truth to drift.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Any

import jsonschema
from ruamel.yaml import YAML

from kernel.schema_utils import SchemaUtilities

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema + template accessors
# ---------------------------------------------------------------------------

SCHEMA_NAME: str = "occurrence-map"
TEMPLATE_FILENAME: str = "occurrence-map-template.yaml"


def load_schema() -> dict[str, Any]:
    """Return the JSON Schema dict for ``occurrence_map.yaml``.

    The schema lives in ``src/doctrine/schemas/occurrence-map.schema.yaml`` and is
    loaded (and cached) by :class:`doctrine.shared.schema_utils.SchemaUtilities`.
    """
    return SchemaUtilities.load_schema(SCHEMA_NAME)


def template_path() -> Path:
    """Return the filesystem path to the starter template YAML."""
    try:
        resource = files("doctrine") / "templates" / TEMPLATE_FILENAME
        return Path(str(resource))
    except (ModuleNotFoundError, TypeError):
        # Development fallback for non-resource contexts.
        return (
            Path(__file__).resolve().parents[2]
            / "doctrine"
            / "templates"
            / TEMPLATE_FILENAME
        )


def load_template_text() -> str:
    """Return the starter template YAML as a string."""
    return template_path().read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Schema-derived constants
# ---------------------------------------------------------------------------


@cache
def _schema_definitions() -> dict[str, Any]:
    defs: dict[str, Any] = load_schema().get("definitions", {})
    return defs


@cache
def _valid_actions() -> frozenset[str]:
    return frozenset(_schema_definitions().get("action", {}).get("enum", []))


@cache
def _valid_operations() -> frozenset[str]:
    return frozenset(_schema_definitions().get("operation", {}).get("enum", []))


@cache
def _standard_categories() -> frozenset[str]:
    return frozenset(
        _schema_definitions().get("standard_category", {}).get("enum", [])
    )


# The 8 standard occurrence categories required by FR-004 — sourced from the
# schema so adding/removing a category in one place is a single edit. An
# admissible occurrence map must classify every one of these, even when the
# action is ``do_not_change`` (omitting a category silently whitelists it).
VALID_ACTIONS: frozenset[str] = _valid_actions()
VALID_OPERATIONS: frozenset[str] = _valid_operations()
STANDARD_CATEGORIES: frozenset[str] = _standard_categories()

PLACEHOLDER_TERMS: frozenset[str] = frozenset(
    {"TODO", "TBD", "FIXME", "XXX", "PLACEHOLDER", ""}
)

MIN_ADMISSIBLE_CATEGORIES: int = 3

_KNOWN_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {"target", "categories", "exceptions", "moves", "status"}
)

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of a validation or admissibility check."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MoveEntry:
    """A single multi-path structural move (IC-10, #1815).

    Maps one or more ``from`` source paths to a single ``to`` destination
    path. Expresses a structural relocation that the eight single-term-rename
    categories cannot capture.
    """

    sources: list[str]
    destination: str
    reason: str | None = None


@dataclass(frozen=True)
class OccurrenceMap:
    """Parsed representation of an ``occurrence_map.yaml`` file."""

    target_term: str
    target_replacement: str | None
    target_operation: str
    categories: dict[str, dict[str, str]]
    exceptions: list[dict[str, str]]
    status: dict[str, Any] | None
    raw: dict[str, Any]
    moves: list[MoveEntry] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_occurrence_map(feature_dir: Path) -> OccurrenceMap | None:
    """Read and parse ``occurrence_map.yaml`` from *feature_dir*.

    Returns ``None`` when the file does not exist.
    """
    yaml_path = feature_dir / "occurrence_map.yaml"
    if not yaml_path.exists():
        return None

    yaml = YAML(typ="safe")
    with open(yaml_path) as fh:
        data: dict[str, Any] = yaml.load(fh)

    if data is None:
        return None

    target = data.get("target", {})
    categories = data.get("categories", {})
    exceptions = data.get("exceptions", [])
    status = data.get("status")
    moves = _parse_moves(data.get("moves"))

    return OccurrenceMap(
        target_term=target.get("term", ""),
        target_replacement=target.get("replacement"),
        target_operation=target.get("operation", ""),
        categories=categories,
        exceptions=exceptions if exceptions is not None else [],
        status=status,
        raw=data,
        moves=moves,
    )


def _parse_moves(raw_moves: Any) -> list[MoveEntry]:
    """Parse the optional ``moves:`` block into :class:`MoveEntry` objects.

    Tolerant by design: malformed entries are skipped here and surfaced by
    :func:`validate_occurrence_map`, which reports human-readable errors. A
    missing or null block yields an empty list so legacy single-term maps are
    unaffected (C-OMAP-1).
    """
    if not isinstance(raw_moves, list):
        return []

    parsed: list[MoveEntry] = []
    for entry in raw_moves:
        if not isinstance(entry, dict):
            continue
        sources_raw = entry.get("from")
        sources = (
            [str(s) for s in sources_raw] if isinstance(sources_raw, list) else []
        )
        destination_raw = entry.get("to")
        destination = destination_raw if isinstance(destination_raw, str) else ""
        reason_raw = entry.get("reason")
        reason = reason_raw if isinstance(reason_raw, str) else None
        parsed.append(
            MoveEntry(sources=sources, destination=destination, reason=reason)
        )
    return parsed


# ---------------------------------------------------------------------------
# Structural validation
# ---------------------------------------------------------------------------


def validate_occurrence_map(omap: OccurrenceMap) -> ValidationResult:
    """Validate an :class:`OccurrenceMap` for structural correctness.

    Checks:
    * ``target`` section exists with a non-empty ``term``
    * ``target.operation`` is one of :data:`VALID_OPERATIONS`
    * ``categories`` section exists with at least one entry
    * Every category has an ``action`` key whose value is in :data:`VALID_ACTIONS`

    Warns on unknown top-level keys.
    """
    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(_validate_target(omap.raw.get("target", _MISSING)))
    errors.extend(_validate_categories(omap.raw.get("categories", _MISSING)))
    errors.extend(_validate_moves(omap.raw.get("moves")))

    for key in omap.raw:
        if key not in _KNOWN_TOP_LEVEL_KEYS:
            warnings.append(f"Unknown top-level key '{key}'")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


# Sentinel distinguishing an absent section from an explicit ``None`` value.
_MISSING: Any = object()


def _validate_target(target: Any) -> list[str]:
    """Validate the required ``target`` section."""
    if target is _MISSING:
        return ["Missing required 'target' section"]
    if not isinstance(target, dict):
        return ["'target' must be a mapping"]

    errors: list[str] = []
    term = target.get("term")
    if term is None:
        errors.append("Missing required 'target.term'")
    elif not isinstance(term, str) or term.strip() == "":
        errors.append("'target.term' must be a non-empty string")

    operation = target.get("operation")
    if operation is not None and operation not in VALID_OPERATIONS:
        errors.append(
            f"Invalid target.operation '{operation}'; "
            f"must be one of {sorted(VALID_OPERATIONS)}"
        )
    return errors


def _validate_categories(cats: Any) -> list[str]:
    """Validate the required ``categories`` section."""
    if cats is _MISSING:
        return ["Missing required 'categories' section"]
    if not isinstance(cats, dict) or len(cats) == 0:
        return ["'categories' must be a non-empty mapping"]

    errors: list[str] = []
    for cat_name, cat_value in cats.items():
        if not isinstance(cat_value, dict):
            errors.append(f"Category '{cat_name}' must be a mapping")
            continue
        action = cat_value.get("action")
        if action is None:
            errors.append(f"Category '{cat_name}' missing required 'action' key")
        elif action not in VALID_ACTIONS:
            errors.append(
                f"Category '{cat_name}' has invalid action '{action}'; "
                f"must be one of {sorted(VALID_ACTIONS)}"
            )
    return errors


def _validate_moves(moves_raw: Any) -> list[str]:
    """Validate the optional ``moves`` section (IC-10 / C-OMAP-1).

    A missing or ``None`` block produces no errors so legacy single-term maps
    are unaffected.
    """
    if moves_raw is None:
        return []
    if not isinstance(moves_raw, list):
        return ["'moves' must be a list when present"]

    errors: list[str] = []
    for index, entry in enumerate(moves_raw):
        errors.extend(_validate_move_entry(index, entry))
    return errors


def _validate_move_entry(index: int, entry: Any) -> list[str]:
    """Validate a single ``moves[]`` entry; return human-readable errors."""
    errors: list[str] = []
    label = f"moves[{index}]"
    if not isinstance(entry, dict):
        return [f"{label} must be a mapping with 'from' and 'to'"]

    sources = entry.get("from")
    if sources is None:
        errors.append(f"{label} missing required 'from' key")
    elif not isinstance(sources, list) or len(sources) == 0:
        errors.append(f"{label}.from must be a non-empty list of paths")
    else:
        for src in sources:
            if not isinstance(src, str) or src.strip() == "":
                errors.append(f"{label}.from entries must be non-empty strings")
                break

    destination = entry.get("to")
    if destination is None:
        errors.append(f"{label} missing required 'to' key")
    elif not isinstance(destination, str) or destination.strip() == "":
        errors.append(f"{label}.to must be a non-empty string")

    return errors


# ---------------------------------------------------------------------------
# JSON Schema validation
# ---------------------------------------------------------------------------


def validate_against_schema(raw: dict[str, Any]) -> ValidationResult:
    """Validate the raw map dict against the JSON Schema.

    This is a machine-enforced contract check — if the schema file changes, the
    bounds of what this function accepts change with it. Use this alongside
    :func:`validate_occurrence_map` (which produces human-readable errors tuned
    for the runtime gate's output panels).
    """
    errors: list[str] = []
    validator = jsonschema.Draft202012Validator(load_schema())
    for err in sorted(validator.iter_errors(raw), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"{path}: {err.message}")
    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=[])


# ---------------------------------------------------------------------------
# Admissibility checking
# ---------------------------------------------------------------------------


def check_admissibility(omap: OccurrenceMap) -> ValidationResult:
    """Check whether the occurrence map is *admissible* for execution.

    An admissible map:
    * Has a ``target.term`` that is not a well-known placeholder
    * Has at least :data:`MIN_ADMISSIBLE_CATEGORIES` categories
    * Classifies every :data:`STANDARD_CATEGORIES` entry (FR-004 —
      omitting a standard category silently whitelists that risk surface)
    """
    errors: list[str] = []
    warnings: list[str] = []

    term = omap.target_term.strip()
    if term.upper() in {p.upper() for p in PLACEHOLDER_TERMS}:
        errors.append(
            f"target.term '{omap.target_term}' is a placeholder; "
            "provide a real term before execution"
        )

    num_categories = len(omap.categories)
    if num_categories < MIN_ADMISSIBLE_CATEGORIES:
        errors.append(
            f"Need at least {MIN_ADMISSIBLE_CATEGORIES} categories, "
            f"got {num_categories}"
        )

    # FR-004: every standard category must be explicitly classified.
    missing = sorted(STANDARD_CATEGORIES - set(omap.categories.keys()))
    if missing:
        errors.append(
            "Occurrence map is missing required standard categories: "
            f"{missing}. Every category must be present — use action "
            "'do_not_change' for risk surfaces that must not be modified."
        )

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )

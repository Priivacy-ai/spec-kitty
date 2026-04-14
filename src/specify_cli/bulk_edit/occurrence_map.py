"""Occurrence map schema, loading, validation, and admissibility checking.

An occurrence map is a YAML file that describes how a bulk rename/remove/deprecate
operation should be classified across different occurrence categories. Each category
carries an ``action`` that tells the executor how to handle occurrences of that kind.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_ACTIONS: frozenset[str] = frozenset(
    {"rename", "manual_review", "do_not_change", "rename_if_user_visible"}
)

VALID_OPERATIONS: frozenset[str] = frozenset({"rename", "remove", "deprecate"})

PLACEHOLDER_TERMS: frozenset[str] = frozenset(
    {"TODO", "TBD", "FIXME", "XXX", "PLACEHOLDER", ""}
)

MIN_ADMISSIBLE_CATEGORIES: int = 3

# The 8 standard occurrence categories required by FR-004.
# An admissible occurrence map must classify every one of these, even when
# the action is ``do_not_change`` — omitting a category from the map
# silently whitelists it, which defeats the guardrail's purpose.
STANDARD_CATEGORIES: frozenset[str] = frozenset(
    {
        "code_symbols",
        "import_paths",
        "filesystem_paths",
        "serialized_keys",
        "cli_commands",
        "user_facing_strings",
        "tests_fixtures",
        "logs_telemetry",
    }
)

_KNOWN_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {"target", "categories", "exceptions", "status"}
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
class OccurrenceMap:
    """Parsed representation of an ``occurrence_map.yaml`` file."""

    target_term: str
    target_replacement: str | None
    target_operation: str
    categories: dict[str, dict[str, str]]
    exceptions: list[dict[str, str]]
    status: dict[str, Any] | None
    raw: dict[str, Any]


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

    return OccurrenceMap(
        target_term=target.get("term", ""),
        target_replacement=target.get("replacement"),
        target_operation=target.get("operation", ""),
        categories=categories,
        exceptions=exceptions if exceptions is not None else [],
        status=status,
        raw=data,
    )


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

    # --- target section ---
    if "target" not in omap.raw:
        errors.append("Missing required 'target' section")
    else:
        target = omap.raw["target"]
        if not isinstance(target, dict):
            errors.append("'target' must be a mapping")
        else:
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

    # --- categories section ---
    if "categories" not in omap.raw:
        errors.append("Missing required 'categories' section")
    else:
        cats = omap.raw["categories"]
        if not isinstance(cats, dict) or len(cats) == 0:
            errors.append("'categories' must be a non-empty mapping")
        else:
            for cat_name, cat_value in cats.items():
                if not isinstance(cat_value, dict):
                    errors.append(
                        f"Category '{cat_name}' must be a mapping"
                    )
                    continue
                action = cat_value.get("action")
                if action is None:
                    errors.append(
                        f"Category '{cat_name}' missing required 'action' key"
                    )
                elif action not in VALID_ACTIONS:
                    errors.append(
                        f"Category '{cat_name}' has invalid action '{action}'; "
                        f"must be one of {sorted(VALID_ACTIONS)}"
                    )

    # --- unknown top-level keys ---
    for key in omap.raw:
        if key not in _KNOWN_TOP_LEVEL_KEYS:
            warnings.append(f"Unknown top-level key '{key}'")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


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

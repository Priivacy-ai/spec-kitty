"""Guard expression compiler for v1 mission state machines.

Provides:
- parse_guard_expression(expr): Parse "func_name(args)" into (name, args_list)
- GUARD_REGISTRY: Maps guard names to factory callables
- compile_guards(config, feature_dir): Replace expression strings with bound callables
- 6 guard primitives: artifact_exists, gate_passed, all_wp_status,
  any_wp_status, input_provided, event_count

Each guard factory returns a callable that receives a transitions EventData
object and returns bool. Guards never raise exceptions for missing context;
they return False instead.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from .schema import MissionValidationError


# ---------------------------------------------------------------------------
# Expression parser
# ---------------------------------------------------------------------------

_EXPR_RE = re.compile(r"^(\w+)\((.*)\)$", re.DOTALL)


def parse_guard_expression(expr: str) -> tuple[str, list[Any]]:
    """Parse a guard expression string into (function_name, args_list).

    Examples::

        >>> parse_guard_expression('artifact_exists("spec.md")')
        ("artifact_exists", ["spec.md"])
        >>> parse_guard_expression('event_count("source_documented", 3)')
        ("event_count", ["source_documented", 3])

    Args:
        expr: A string like ``func_name(arg1, arg2, ...)``.

    Returns:
        Tuple of (function_name, list_of_parsed_args).

    Raises:
        ValueError: If *expr* does not match the ``name(args)`` pattern.
    """
    match = _EXPR_RE.match(expr.strip())
    if not match:
        raise ValueError(f"Invalid guard expression syntax: '{expr}'. Expected format: function_name(arg1, arg2, ...)")

    func_name = match.group(1)
    raw_args = match.group(2).strip()

    if not raw_args:
        return func_name, []

    args: list[Any] = []
    for token in _split_args(raw_args):
        token = token.strip()
        # Try integer
        try:
            args.append(int(token))
            continue
        except ValueError:
            pass
        # Try unquoting string
        if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
            args.append(token[1:-1])
        else:
            # Bare identifier — keep as string
            args.append(token)

    return func_name, args


def _split_args(raw: str) -> list[str]:
    """Split comma-separated args, respecting quoted strings."""
    parts: list[str] = []
    current: list[str] = []
    in_quote: str | None = None

    for ch in raw:
        if in_quote:
            current.append(ch)
            if ch == in_quote:
                in_quote = None
        elif ch in ('"', "'"):
            in_quote = ch
            current.append(ch)
        elif ch == ",":
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)

    if current:
        parts.append("".join(current))

    return parts


# ---------------------------------------------------------------------------
# Guard primitive factories
# ---------------------------------------------------------------------------


def _make_artifact_exists_guard(args: list[Any]) -> Callable[..., bool]:
    """Guard: True when a file at *path* exists relative to feature_dir."""
    path = str(args[0])

    def guard(event_data: Any) -> bool:
        model = event_data.model
        feature_dir = getattr(model, "feature_dir", None)
        if feature_dir is None:
            return False
        return (Path(feature_dir) / path).exists()

    return guard


def _make_gate_passed_guard(args: list[Any]) -> Callable[..., bool]:
    """Guard: True when a ``gate_passed`` event with *gate_name* exists in the mission event log."""
    gate_name = str(args[0])

    def guard(event_data: Any) -> bool:
        model = event_data.model
        feature_dir = getattr(model, "feature_dir", None)
        if feature_dir is None:
            return False
        log_path = Path(feature_dir) / "mission-events.jsonl"
        if not log_path.exists():
            return False
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("type") == "gate_passed" and entry.get("name") == gate_name:
                    return True
        except (json.JSONDecodeError, OSError):
            return False
        return False

    return guard


def _make_all_wp_status_guard(args: list[Any]) -> Callable[..., bool]:
    """Guard: True when ALL WP task files have ``lane`` equal to *status*."""
    status = str(args[0])

    def guard(event_data: Any) -> bool:
        model = event_data.model
        feature_dir = getattr(model, "feature_dir", None)
        if feature_dir is None:
            return False
        tasks_dir = Path(feature_dir) / "tasks"
        if not tasks_dir.is_dir():
            return False
        wp_files = sorted(tasks_dir.glob("WP*.md"))
        if not wp_files:
            return False
        for wp_file in wp_files:
            lane = _read_lane_from_frontmatter(wp_file)
            if lane != status:
                return False
        return True

    return guard


def _make_any_wp_status_guard(args: list[Any]) -> Callable[..., bool]:
    """Guard: True when ANY WP task file has ``lane`` equal to *status*."""
    status = str(args[0])

    def guard(event_data: Any) -> bool:
        model = event_data.model
        feature_dir = getattr(model, "feature_dir", None)
        if feature_dir is None:
            return False
        tasks_dir = Path(feature_dir) / "tasks"
        if not tasks_dir.is_dir():
            return False
        wp_files = sorted(tasks_dir.glob("WP*.md"))
        if not wp_files:
            return False
        for wp_file in wp_files:
            lane = _read_lane_from_frontmatter(wp_file)
            if lane == status:
                return True
        return False

    return guard


def _make_input_provided_guard(args: list[Any]) -> Callable[..., bool]:
    """Guard: True when *name* exists in ``model.inputs`` and is not None."""
    name = str(args[0])

    def guard(event_data: Any) -> bool:
        model = event_data.model
        inputs = getattr(model, "inputs", None)
        if inputs is None:
            return False
        return inputs.get(name) is not None

    return guard


def _make_event_count_guard(args: list[Any]) -> Callable[..., bool]:
    """Guard: True when count of events with matching *type* >= *min_count*."""
    event_type = str(args[0])
    min_count = int(args[1])

    def guard(event_data: Any) -> bool:
        model = event_data.model
        feature_dir = getattr(model, "feature_dir", None)
        if feature_dir is None:
            return False
        log_path = Path(feature_dir) / "mission-events.jsonl"
        if not log_path.exists():
            return False
        count = 0
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("type") == event_type:
                    count += 1
        except (json.JSONDecodeError, OSError):
            return False
        return count >= min_count

    return guard


# ---------------------------------------------------------------------------
# Guard registry
# ---------------------------------------------------------------------------

GUARD_REGISTRY: dict[str, Callable[..., Callable[..., bool]]] = {
    "artifact_exists": _make_artifact_exists_guard,
    "gate_passed": _make_gate_passed_guard,
    "all_wp_status": _make_all_wp_status_guard,
    "any_wp_status": _make_any_wp_status_guard,
    "input_provided": _make_input_provided_guard,
    "event_count": _make_event_count_guard,
}


# ---------------------------------------------------------------------------
# Frontmatter helper (minimal, avoids coupling to specify_cli.frontmatter)
# ---------------------------------------------------------------------------


def _read_lane_from_frontmatter(file_path: Path) -> str | None:
    """Read the ``lane`` field from a YAML frontmatter block.

    Returns None if the file cannot be read or has no lane field.
    This is a minimal parser that avoids importing the full frontmatter module
    to keep the guard system self-contained.
    """
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        return None

    if not text.startswith("---"):
        return None

    end = text.find("---", 3)
    if end == -1:
        return None

    frontmatter_text = text[3:end]
    for line in frontmatter_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("lane:"):
            value = stripped[5:].strip().strip('"').strip("'")
            return value

    return None


# ---------------------------------------------------------------------------
# Guard compilation: string expressions -> bound callables
# ---------------------------------------------------------------------------


def _is_guard_expression(s: str) -> bool:
    """Return True if *s* looks like a guard expression (contains parens)."""
    return "(" in s and s.rstrip().endswith(")")


def compile_guards(config: dict[str, Any], feature_dir: Path | None = None) -> dict[str, Any]:
    """Process a v1 config dict, compiling guard expression strings into callables.

    For each transition in ``config["transitions"]``, this function inspects
    the ``conditions`` and ``unless`` arrays.  Any entry that looks like a
    guard expression (e.g. ``artifact_exists("spec.md")``) is:

    1. Parsed into (function_name, args).
    2. Looked up in :data:`GUARD_REGISTRY`.
    3. Replaced in-place with the callable returned by the factory.

    Unknown guard expressions raise :class:`MissionValidationError` at
    load time so typos are caught early.

    Args:
        config: A v1 mission config dict (must have ``"transitions"`` key).
        feature_dir: Optional feature directory for guards that need filesystem
            access.  Passed through to guard callables at evaluation time via
            the model, not captured at compile time.

    Returns:
        The *same* config dict, mutated in place with expression strings
        replaced by compiled callables.

    Raises:
        MissionValidationError: If an expression references an unknown guard
            function name.
    """
    transitions = config.get("transitions", [])

    for idx, transition in enumerate(transitions):
        transition.get("trigger", f"t{idx}")

        for key in ("conditions", "unless"):
            entries = transition.get(key)
            if not entries:
                continue

            for i, entry in enumerate(entries):
                if not isinstance(entry, str):
                    continue
                if not _is_guard_expression(entry):
                    continue

                func_name, args = parse_guard_expression(entry)

                if func_name not in GUARD_REGISTRY:
                    raise MissionValidationError(
                        f"Unknown guard expression: '{func_name}' in '{entry}'. "
                        f"Supported guards: {', '.join(sorted(GUARD_REGISTRY.keys()))}"
                    )

                factory = GUARD_REGISTRY[func_name]
                guard_callable = factory(args)
                entries[i] = guard_callable

    return config

from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


_BANNED_CALLS = {
    ("datetime", "now"): "datetime.now()",
    ("datetime", "utcnow"): "datetime.utcnow()",
    ("datetime", "datetime", "now"): "datetime.datetime.now()",
    ("datetime", "datetime", "utcnow"): "datetime.datetime.utcnow()",
    ("date", "today"): "date.today()",
    ("datetime", "date", "today"): "datetime.date.today()",
    ("time", "time"): "time.time()",
}

_ALIASABLE_CLOCK_PATHS = set(_BANNED_CALLS) | {
    ("datetime",),
    ("datetime", "datetime"),
    ("date",),
    ("datetime", "date"),
    ("time",),
}


@dataclass(frozen=True, order=True)
class WallClockAssertionViolation:
    path: Path
    line: int
    call: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.call}"


def find_wall_clock_assertion_violations(paths: Iterable[Path]) -> list[WallClockAssertionViolation]:
    """Find direct wall-clock reads inside pytest assert expressions."""
    violations: list[WallClockAssertionViolation] = []
    for path in sorted({Path(p) for p in paths}):
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        aliases = _import_aliases(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                for call, call_name in _wall_clock_calls(node, aliases):
                    violations.append(
                        WallClockAssertionViolation(
                            path=path,
                            line=getattr(call, "lineno", node.lineno),
                            call=call_name,
                        )
                    )
    return sorted(violations)


def format_wall_clock_assertion_violations(
    violations: Iterable[WallClockAssertionViolation],
) -> str:
    rendered = "\n".join(f"  - {violation.render()}" for violation in violations)
    return (
        "Wall-clock reads are not allowed inside test assertions.\n"
        "Inject a stable `now=`/clock into production code and assert against that fixed value.\n"
        "For genuine freshness-window checks, capture bounds before/after the action and keep the wall-clock calls out of the assert expression.\n"
        f"{rendered}"
    )


def _wall_clock_calls(
    assert_node: ast.Assert,
    aliases: dict[str, tuple[str, ...]],
) -> list[tuple[ast.Call, str]]:
    calls: list[tuple[ast.Call, str]] = []
    for node in ast.walk(assert_node):
        if not isinstance(node, ast.Call):
            continue
        raw_path = _attribute_path(node.func)
        if not raw_path:
            continue
        normalized_path = _normalize_alias(raw_path, aliases)
        if normalized_path in _BANNED_CALLS:
            calls.append((node, f"{'.'.join(raw_path)}()"))
    return calls


def _import_aliases(tree: ast.AST) -> dict[str, tuple[str, ...]]:
    aliases: dict[str, tuple[str, ...]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = tuple(alias.name.split("."))
                if parts and parts[0] in {"datetime", "time"}:
                    aliases[alias.asname or parts[0]] = parts
        elif isinstance(node, ast.ImportFrom) and node.module in {"datetime", "time"}:
            for alias in node.names:
                if alias.name == "*":
                    _add_star_import_aliases(aliases, node.module)
                    continue
                aliases[alias.asname or alias.name] = (node.module, alias.name)
        elif isinstance(node, ast.Assign):
            _add_assignment_aliases(aliases, node.targets, node.value)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            _add_assignment_aliases(aliases, [node.target], node.value)
    return aliases


def _add_star_import_aliases(
    aliases: dict[str, tuple[str, ...]],
    module: str | None,
) -> None:
    if module == "time":
        aliases["time"] = ("time", "time")
    elif module == "datetime":
        aliases["datetime"] = ("datetime", "datetime")
        aliases["date"] = ("datetime", "date")


def _add_assignment_aliases(
    aliases: dict[str, tuple[str, ...]],
    targets: list[ast.expr],
    value: ast.expr,
) -> None:
    source = _normalize_alias(_attribute_path(value), aliases)
    if source not in _ALIASABLE_CLOCK_PATHS:
        return
    for target in targets:
        if isinstance(target, ast.Name):
            aliases[target.id] = source


def _normalize_alias(
    path: tuple[str, ...],
    aliases: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    if not path:
        return path
    replacement = aliases.get(path[0])
    if replacement is None:
        return path
    return replacement + path[1:]


def _attribute_path(node: ast.AST) -> tuple[str, ...]:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return tuple(reversed(parts))

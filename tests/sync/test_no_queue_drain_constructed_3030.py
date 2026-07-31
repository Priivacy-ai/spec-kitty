"""SC-005 anchor: no code path constructs the queue-backed drain (#3030 WP02).

SC-005 accepts WP02 when "the queue-backed drain is gone **and a test asserts no
code path constructs it**". The daemon call sites were deleted in T008, but a
deletion alone is not a guarantee — the functions still exist in ``sync/batch.py``
and a future edit could re-wire them in a single line. That drain has no
per-project consent anywhere on it, so re-wiring it silently reinstates the
cross-project leak this mission exists to close.

This test is the standing guard. It reads the source tree rather than mocking
anything, so it cannot be satisfied by a stub: any production module that
imports or calls ``batch_sync``/``sync_all_queued_events`` fails it, as does
re-adding either name to the ``specify_cli.sync`` public API.

Deliberately *not* asserted: references inside ``sync/batch.py`` itself, where
the two functions are defined and one calls the other. Both are unreachable from
production, so those are dead-to-dead references. Retiring the implementations
outright belongs to the work package that already opens ``batch.py`` for FR-014.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fast]

RETIRED_DRAIN_NAMES = frozenset({"batch_sync", "sync_all_queued_events"})

# The module that defines them; its internal references are dead-to-dead.
_DEFINING_MODULE = Path("specify_cli/sync/batch.py")


def _src_root() -> Path:
    root = Path(__file__).resolve().parents[2] / "src"
    assert root.is_dir(), f"source root not found at {root}"
    return root


def _production_modules() -> list[Path]:
    root = _src_root()
    return [
        path
        for path in sorted(root.rglob("*.py"))
        if path.relative_to(root) != _DEFINING_MODULE
    ]


def _offending_references(tree: ast.AST) -> list[str]:
    """Return references that would re-construct the retired drain."""
    found: list[str] = []

    for node in ast.walk(tree):
        # `from .batch import batch_sync`
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in RETIRED_DRAIN_NAMES:
                    found.append(f"line {node.lineno}: imports {alias.name}")
        # `batch_sync(...)` / `something.batch_sync(...)`
        elif isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in RETIRED_DRAIN_NAMES:
                found.append(f"line {node.lineno}: calls {name}")

    return found


def test_no_production_module_constructs_the_queue_backed_drain() -> None:
    """FR-012/SC-005: the retired drain has no caller anywhere in ``src/``."""
    offenders: dict[str, list[str]] = {}

    for path in _production_modules():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - defensive
            continue
        refs = _offending_references(tree)
        if refs:
            offenders[str(path.relative_to(_src_root()))] = refs

    assert not offenders, (
        "The queue-backed event drain was retired in #3030 WP02 (FR-012) because "
        "it carries no per-project consent. Re-wiring it reinstates the "
        "cross-project leak. Deliver events through the journal dispatcher "
        f"(delivery/dispatcher.py) instead.\nOffending references: {offenders}"
    )


def test_retired_drain_is_not_in_the_sync_public_api() -> None:
    """Neither name may be re-exported from ``specify_cli.sync``."""
    import specify_cli.sync as sync_pkg

    exported = set(sync_pkg.__all__)
    leaked = exported & RETIRED_DRAIN_NAMES
    assert not leaked, (
        f"{sorted(leaked)} must not be part of the specify_cli.sync public API — "
        "exporting the retired drain invites exactly the re-wiring FR-012 removed."
    )


def test_retired_drain_is_not_lazily_resolvable() -> None:
    """The lazy ``__getattr__`` map must not resolve them either.

    ``__all__`` alone is advisory; the module's lazy attribute map is what
    actually hands a caller a working function object.
    """
    import specify_cli.sync as sync_pkg

    for name in sorted(RETIRED_DRAIN_NAMES):
        with pytest.raises(AttributeError):
            getattr(sync_pkg, name)

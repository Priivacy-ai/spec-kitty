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

Strengthened for #3167, because the deletion made the green vacuous
--------------------------------------------------------------------
``#3167`` deleted the two functions themselves. **Nothing can import a name that
does not exist**, so from that commit on this file passed for a reason that no
longer discriminates: a scanner that returned ``[]`` unconditionally, or one
pointed at an empty directory, would look exactly as green. ``NFR-004`` promises
this guarantee never *decreases*, and a vacuous green is a decrease — so two
things changed here rather than nothing:

* ``test_scanner_flags_a_synthetic_reintroduction`` is the positive control the
  sibling permanence guard (``tests/architectural/test_batch_drain_retired_3167.py``)
  already carries. It feeds ``_offending_references`` a **synthetic source string**
  holding ``from .batch import batch_sync`` plus a call, and requires both to be
  flagged — and a near-identical clean source to be flagged not at all. The
  string is parsed in memory and never written to ``src/``.
* The ``sync/batch.py`` self-exclusion is **gone**. It existed because the two
  functions were *defined* there and one called the other, making those
  references dead-to-dead. With the definitions deleted the carve-out no longer
  excuses anything — it just leaves ``batch.py`` as the single file in the tree
  where re-adding a sender *together with* a caller would be invisible to this
  gate, which is the exact shape of the bypass ``#3167`` removed.

``test_the_scan_is_non_vacuous`` prints the scanned-module input count, so an
"all checks passed" here can never be confused with a gate that ran on nothing.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

RETIRED_DRAIN_NAMES = frozenset({"batch_sync", "sync_all_queued_events"})

#: The module the two senders used to live in. It is scanned like every other
#: module: #3167 deleted the definitions, so there is no longer any dead-to-dead
#: reference here to excuse, and excluding it would leave exactly one file where a
#: reintroduced sender *plus* its caller passes this gate unseen.
_FORMER_DEFINING_MODULE = "specify_cli/sync/batch.py"

#: POSITIVE CONTROL subject. Parsed in memory, never written to ``src/``: source
#: reproducing the reintroduction this file exists to catch — the import form and
#: the call form, which are the two node kinds ``_offending_references`` matches.
_SYNTHETIC_REINTRODUCTION = """\
from .batch import batch_sync


def _drain_the_queue(queue) -> None:
    batch_sync(queue)
"""

#: The same shape routed through the journal dispatcher instead. Structurally
#: identical (one relative import, one call) so a scanner that flagged *everything*
#: — the other way to fake a green here — reds on this half of the control.
_SYNTHETIC_CLEAN = """\
from .delivery.dispatcher import dispatch_pending


def _drain_the_queue(queue) -> None:
    dispatch_pending(queue)
"""


def _src_root() -> Path:
    root = Path(__file__).resolve().parents[2] / "src"
    assert root.is_dir(), f"source root not found at {root}"
    return root


def _production_modules() -> list[Path]:
    return sorted(_src_root().rglob("*.py"))


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


def test_scanner_flags_a_synthetic_reintroduction() -> None:
    """POSITIVE CONTROL (#3167, NFR-004): the scanner still bites.

    ``#3167`` deleted ``batch_sync`` and ``sync_all_queued_events``, so
    ``test_no_production_module_constructs_the_queue_backed_drain`` below can no
    longer fail for the reason it was written to catch — nothing can import a name
    that is gone. Its green therefore proves the tree is clean **only if** the
    matcher would still have spoken. That is what this test establishes, on a
    synthetic source string rather than by mutating ``src/``.

    Both directions are asserted, because either one alone is fakeable: a matcher
    that returns everything passes the first half, and a matcher that returns
    nothing passes the second.
    """
    flagged = _offending_references(ast.parse(_SYNTHETIC_REINTRODUCTION))
    assert flagged == ["line 1: imports batch_sync", "line 5: calls batch_sync"], (
        "the reintroduction matcher no longer flags a source that both imports and "
        f"calls a retired sender — it returned {flagged!r}. Until this is fixed, the "
        "clean result from the src/ scan in this file is silence, not evidence."
    )

    quiet = _offending_references(ast.parse(_SYNTHETIC_CLEAN))
    assert quiet == [], (
        "the matcher flagged a structurally identical source that routes through the "
        f"journal dispatcher instead: {quiet!r}. A matcher that fires on everything "
        "cannot distinguish a reintroduction from correct code."
    )


def test_the_scan_is_non_vacuous() -> None:
    """The ``src/`` scan runs on real files, and ``batch.py`` is one of them.

    Two failure modes, both of which would leave the assertion below green:

    * an empty or unreachable input set (a moved package, a renamed ``src/``), and
    * the ``sync/batch.py`` self-exclusion this WP removed, which — once the
      definitions were deleted — no longer excused a dead-to-dead reference and
      instead made ``batch.py`` the one file where re-adding a sender together with
      its caller was invisible to this gate.

    The input count is printed (visible under ``-s``) so "all checks passed" here is
    never mistaken for a gate that ran on nothing.
    """
    modules = _production_modules()
    root = _src_root()
    print(f"[#3167 drain scan] input: {len(modules)} production module(s) scanned under {root}")

    assert len(modules) > 900, f"only {len(modules)} module(s) found under {root} — this scan has lost its input"

    relative = {str(path.relative_to(root)) for path in modules}
    assert _FORMER_DEFINING_MODULE in relative, (
        f"{_FORMER_DEFINING_MODULE} is not in the scanned set. #3167 removed its "
        "self-exclusion on purpose: with the senders deleted there is no dead-to-dead "
        "reference left to excuse, and skipping it would leave exactly one file where "
        "a reintroduced sender plus a caller passes this gate unseen."
    )


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

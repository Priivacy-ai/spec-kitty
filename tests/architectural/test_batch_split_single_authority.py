"""Single-authority guard for the ordered-batch midpoint split (#2755).

Mission ``sync-batch-400-poison-isolation`` folded the batch-splitting arithmetic
onto ONE canonical leaf, ``specify_cli.core.batch_partition.split_in_half`` (the
plain keep-left ``//2`` cut). #2755 retrofitted every consumer onto that shared
authority so none re-derives the cut on its own.

**T017 retired by #3167 — read this before assuming coverage was lost.** The
behavioral-delegation guard patched ``core.batch_partition.split_in_half`` with a
counting spy and asserted ``specify_cli.sync.batch._shrink_events_for_retry``
invoked it. That shrink was part of the queue-backed drain #3167 deleted, so the
guard's subject no longer exists and the test could only have been kept alive by
inventing a caller. Its requirement — "no consumer re-derives the midpoint" — did
not die with it; it is carried, over ALL of ``src/``, by T018 below.

**T018 — AST single-authority guard (still live, and the reason this file stays).**
Walk ``src/specify_cli`` for any ``len(...) // 2`` floor-division and assert none
survive outside the two legitimate, allowlisted sites: the SSOT itself
(``core/batch_partition.py``) and the unrelated ``doc_analysis/gap_analysis.py``
core-area heuristic (``len(project_areas) // 2``). ``cli/commands/sync.py``'s
``limit // 2`` is not ``len()``-based and is naturally out of scope. Non-vacuity
is proven by a runnable self-test that the matcher fires on a synthetic violating
snippet (DIRECTIVE_041: a rotting proof is not a gate).

T018 pins #2755 across the whole source tree **independently of** ``sync/batch.py``,
so its scope is unchanged by the retirement. ``core/batch_partition.py::split_in_half``
is deliberately kept as a zero-consumer canonical leaf (operator decision, #3167).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src" / "specify_cli"

# Sites where a ``len(...) // 2`` floor-division is legitimate and must NOT be
# rewired onto ``split_in_half``:
#   * batch_partition.py — the single authority itself (it *is* the ``//2``).
#   * gap_analysis.py    — an unrelated core-area heuristic on ``project_areas``.
_LEN_HALF_ALLOWLIST = frozenset(
    {
        _SRC / "core" / "batch_partition.py",
        _SRC / "doc_analysis" / "gap_analysis.py",
    }
)


# ---------------------------------------------------------------------------
# T018 — AST single-authority guard (belt-and-suspenders, allowlisted)
# ---------------------------------------------------------------------------


def _is_len_floordiv_by_two(node: ast.AST) -> bool:
    """True for a ``len(...) // 2`` floor-division ``BinOp``."""
    if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.FloorDiv):
        return False
    right = node.right
    if not (isinstance(right, ast.Constant) and right.value == 2):
        return False
    left = node.left
    return (
        isinstance(left, ast.Call)
        and isinstance(left.func, ast.Name)
        and left.func.id == "len"
    )


def _find_len_floordiv_sites(tree: ast.AST) -> list[int]:
    """Return the line numbers of every ``len(...) // 2`` in ``tree``."""
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.BinOp) and _is_len_floordiv_by_two(node)
    ]


def test_ast_matcher_is_non_vacuous() -> None:
    """The matcher fires on a synthetic ``len(x) // 2`` (proof it is not dead)."""
    snippet = "mid = max(1, len(events) // 2)\n"
    assert _find_len_floordiv_sites(ast.parse(snippet)) == [1]

    clean = "mid = max(1, len(events) // 3)\n"
    assert _find_len_floordiv_sites(ast.parse(clean)) == []


def test_no_reimplemented_len_half_split_outside_authority() -> None:
    """No ``len(...) // 2`` survives outside the two allowlisted sites.

    RED before the #2755 rewire (``sync/batch.py`` still re-derived the midpoint
    inline); GREEN once the shrink delegates to ``split_in_half``.
    """
    offenders: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        if "__pycache__" in path.parts or path in _LEN_HALF_ALLOWLIST:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for lineno in _find_len_floordiv_sites(tree):
            offenders.append(f"{path.relative_to(_REPO_ROOT)}:{lineno}")

    assert not offenders, (
        "re-derived `len(...) // 2` batch midpoint(s) outside the single authority "
        "(specify_cli.core.batch_partition) — delegate to split_in_half instead: "
        + ", ".join(offenders)
    )

"""Single-authority guard for the ordered-batch midpoint split (#2755).

Mission ``sync-batch-400-poison-isolation`` folded the batch-splitting arithmetic
onto ONE canonical leaf, ``specify_cli.core.batch_partition.split_in_half`` (the
plain keep-left ``//2`` cut). The legacy 413 byte-shrink,
``specify_cli.sync.batch._shrink_events_for_retry``, historically re-derived that
midpoint inline (``events[: max(1, len(events) // 2)]``). #2755 retrofits the
shrink onto the shared authority so no consumer re-derives the cut on its own.

This file makes that consolidation permanent with TWO guards:

* **T017 — behavioral delegation (LOAD-BEARING).** Patch the REAL
  ``core.batch_partition.split_in_half`` with a counting spy and assert
  ``_shrink_events_for_retry`` actually *invokes* it for a ``len > 1`` batch.
  This is behavioral — it survives any source respelling and cannot be faked by
  a comment or an equivalent inline expression. It is RED until the shrink
  delegates.

* **T018 — AST single-authority (belt-and-suspenders).** Walk ``src/specify_cli``
  for any ``len(...) // 2`` floor-division and assert none survive outside the
  two legitimate, allowlisted sites: the SSOT itself
  (``core/batch_partition.py``) and the unrelated ``doc_analysis/gap_analysis.py``
  core-area heuristic (``len(project_areas) // 2``). ``cli/commands/sync.py``'s
  ``limit // 2`` is not ``len()``-based and is naturally out of scope. Non-vacuity
  is proven by a runnable self-test that the matcher fires on a synthetic
  violating snippet (DIRECTIVE_041: a rotting proof is not a gate).
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from specify_cli.core import batch_partition
from specify_cli.sync import batch as batch_mod

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
# T017 — behavioral delegation (LOAD-BEARING, non-fakeable)
# ---------------------------------------------------------------------------


def test_shrink_delegates_to_shared_split_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_shrink_events_for_retry`` must invoke the shared ``split_in_half``.

    Patches the REAL ``core.batch_partition.split_in_half`` with a spy that
    delegates to the original and counts calls, then drives the shrink over a
    ``len > 1`` batch. An inline re-derivation of ``//2`` would leave the spy
    at zero calls — this proves delegation, not merely an equal result.
    """
    original: Callable[
        [Sequence[dict[str, object]]],
        tuple[list[dict[str, object]], list[dict[str, object]]],
    ] = batch_partition.split_in_half
    calls: list[int] = []

    def spy(
        events: list[dict[str, object]],
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        calls.append(len(events))
        return original(events)

    monkeypatch.setattr(batch_partition, "split_in_half", spy)

    events = [{"event_id": f"e{i}"} for i in range(4)]
    result = batch_mod._shrink_events_for_retry(events)

    assert calls, "shrink did not delegate to core.batch_partition.split_in_half"
    # keep-left-drop-rest: the shrink keeps the left half only.
    assert result == events[: max(1, len(events) // 2)]


def test_shrink_uses_plain_split_not_create_aware(monkeypatch: pytest.MonkeyPatch) -> None:
    """The 413 shrink uses PLAIN ``split_in_half`` — never ``create_aware_midpoint``.

    Byte-sizing must not inherit create-aware key snapping. If the shrink ever
    reached for the create-aware primitive, this spy would trip.
    """

    def forbidden(*_args: object, **_kwargs: object) -> int:
        raise AssertionError(
            "413 shrink must not call create_aware_midpoint — use plain split_in_half"
        )

    monkeypatch.setattr(batch_partition, "create_aware_midpoint", forbidden)

    events = [{"event_id": f"e{i}"} for i in range(4)]
    assert batch_mod._shrink_events_for_retry(events) == events[:2]


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

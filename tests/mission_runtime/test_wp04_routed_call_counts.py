"""WP04 commit 1 — per-site structural call-count assertions for the 4 routed sites.

Mission ``meta-fail-closed-3162-01KZ7FSQ``, census rows 1, 2, 3 and 13.

Why a structural assertion and not a printed pre/post count
-----------------------------------------------------------
This work package is **0-net** on the routed census: WP05 is the mission's
single allocator. A printed pre/post pair is only a check a human has to compare;
it does not *close* the budget, because a **fold** -- collapsing two routed calls
into one -- survives both clauses of the live gate. Concretely, with
``ROUTED_LOAD_META_FLOOR = 127`` and ``ROUTED_LOAD_META_FLOOR_MARGIN = 4``
(``tests/architectural/test_inline_meta_read_gate.py``), a folded tree reading
129 satisfies ``>= 127``, ``> 127`` and ``129 - 127 <= 4`` -- all three clauses
green. Lanes B and C are concurrent and file-disjoint, so no file-overlap check
can see the coupling either.

These four assertions close it per site: each routed function's **own body** must
hold **exactly one** ``load_meta_fail_closed(`` call and **zero** ``load_meta(``
calls.

Matching is on the **exact callee name**, never a substring: ``load_meta_fail_closed``
*contains* ``load_meta``, so a substring test would report zero ``load_meta(``
calls while the routed call itself supplied the match.

Each message names the **module**, because ``_resolve_mission_id`` is defined in
four modules on this tree -- and two of them are this mission's own sites with
**opposite arms**: row 3 here (``src/mission_runtime/resolution.py``, degrade)
and row 9 in ``src/specify_cli/decisions/service.py`` (refuse-typed, WP03).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

#: Repo root derived from THIS FILE's location, so the assertion reads the same
#: tree the test file lives in. A worktree run without ``PYTHONPATH`` otherwise
#: AST-scans the edited tree while importing the unedited one.
_REPO_ROOT = Path(__file__).resolve().parents[2]

_FAIL_CLOSED_CALLEE = "load_meta_fail_closed"
_RAW_CALLEE = "load_meta"

#: (module path relative to repo root, routed function symbol) -- census rows
#: 1, 2, 3, 13.
_ROUTED_SITES = [
    ("src/mission_runtime/resolution.py", "_mid8_from_primary_meta"),
    ("src/mission_runtime/resolution.py", "_resolve_coordination_branch"),
    ("src/mission_runtime/resolution.py", "_resolve_mission_id"),
    ("src/specify_cli/upgrade/feature_meta.py", "load_feature_meta"),
]


def _callee_name(node: ast.Call) -> str | None:
    """The bare callee name for ``f(...)`` and ``a.b.f(...)``, else ``None``."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _function_body_call_names(module_rel: str, symbol: str) -> list[str]:
    """Every callee name invoked inside *symbol*'s own body in *module_rel*.

    Nested function definitions are excluded, so "own body" means what it says.
    """
    path = _REPO_ROOT / module_rel
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    targets = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol
    ]
    # golden-count: cardinality-is-contract
    # `targets` holds ast.FunctionDef nodes all named `symbol` by construction of the
    # filter above — indistinguishable elements, so a member-set equality is strictly
    # weaker than the count. The contract is uniqueness of the definition. Escape
    # hatch per test_golden_count_ban's documented policy; folded by WP08.
    assert len(targets) == 1, (  # golden-count: cardinality-is-contract
        f"expected exactly one definition of {symbol!r} in {module_rel}, found "
        f"{len(targets)} -- the module or the symbol name moved"
    )
    target = targets[0]

    nested_ids = {
        id(inner)
        for node in ast.walk(target)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node is not target
        for inner in ast.walk(node)
    }

    names: list[str] = []
    for node in ast.walk(target):
        if isinstance(node, ast.Call) and id(node) not in nested_ids:
            name = _callee_name(node)
            if name is not None:
                names.append(name)
    return names


@pytest.mark.parametrize(("module_rel", "symbol"), _ROUTED_SITES)
def test_routed_site_holds_exactly_one_fail_closed_call_and_no_raw_call(
    module_rel: str, symbol: str
) -> None:
    """Each routed site: exactly 1 ``load_meta_fail_closed(``, 0 ``load_meta(``.

    Exact callee name, module named in every message.
    """
    names = _function_body_call_names(module_rel, symbol)

    fail_closed = [n for n in names if n == _FAIL_CLOSED_CALLEE]
    raw = [n for n in names if n == _RAW_CALLEE]

    # golden-count: cardinality-is-contract
    # `fail_closed` is a list of IDENTICAL strings (filtered `n == _FAIL_CLOSED_CALLEE`),
    # so `set(fail_closed) == {_FAIL_CLOSED_CALLEE}` is true for one call and for five —
    # strictly weaker than the count. The count IS the contract: this is the mission's
    # routed-budget assertion, and both directions matter (two calls is an overspend,
    # zero means the routing never reached the site; a fold that collapses two routed
    # calls into one also reds the ROUTED_LOAD_META_FLOOR gate downward). Escape hatch
    # per test_golden_count_ban's documented policy; folded by WP08.
    assert len(fail_closed) == 1, (  # golden-count: cardinality-is-contract
        f"{module_rel}::{symbol} must hold EXACTLY ONE {_FAIL_CLOSED_CALLEE}() call "
        f"in its own body, found {len(fail_closed)}. More than one is a routed-census "
        f"overspend (this work package is 0-net; WP05 is the sole allocator); zero "
        f"means the routing did not reach this site."
    )
    assert len(raw) == 0, (
        f"{module_rel}::{symbol} must hold ZERO bare {_RAW_CALLEE}() calls in its own "
        f"body, found {len(raw)}. Matched on the EXACT callee name -- note "
        f"{_FAIL_CLOSED_CALLEE!r} contains {_RAW_CALLEE!r}, so a substring check would "
        f"have silently passed here."
    )


def test_exact_name_matching_is_what_the_assertion_actually_does() -> None:
    """Control: prove the matcher is exact-name, not substring.

    Without this, the four assertions above could be vacuously green: a
    substring implementation would count the routed ``load_meta_fail_closed(``
    call as a bare ``load_meta(`` hit and red every site, or -- with the
    comparison inverted -- never fire at all. This pins the discriminator
    itself on a synthetic module, so the guard cannot rot silently.
    """
    synthetic = ast.parse(
        "def probe():\n"
        "    load_meta_fail_closed(x)\n"
        "    other.load_meta_fail_closed(y)\n"
    )
    target = synthetic.body[0]
    assert isinstance(target, ast.FunctionDef)
    names = [
        _callee_name(node) for node in ast.walk(target) if isinstance(node, ast.Call)
    ]

    assert names.count(_FAIL_CLOSED_CALLEE) == 2
    assert names.count(_RAW_CALLEE) == 0, (
        "exact-name matching is broken: load_meta_fail_closed was counted as a bare "
        "load_meta call, which would make the four site assertions meaningless"
    )

"""Sole-live-caller characterization audit (WP01 T005, mission
``scopesource-gate-followup-01KY6S9P``) — RETIRED-CENSUS-CALLER pin.

**Re-adjudicated by WP04 (as this file's own original docstring anticipated).**
The original characterization pinned two facts about the base commit:
(a) ``evaluate_pre_review_gate`` had exactly TWO production call sites — the
named-handler registry (``gate_registry.py``, always passing ``scope_source``
explicitly) and a dead composition helper, ``_mt_pre_review_gate_verdict``
(``tasks_move_task.py``), which was the ONLY call site omitting
``scope_source`` — the exact shape that fell through
``evaluate_pre_review_gate``'s now-retired ``scope_source is None`` census
branch; and (b) that dead helper had no production call site of its own — it
was reachable ONLY via a ``tasks.py`` compat re-export and a compat-surface
name-listing test.

WP04 (FR-001/FR-002, data-model.md sec. 6) deleted BOTH the census branch
(``scope_source`` is now a REQUIRED parameter) and the dead composition
helper (+ its compat re-export) — precisely the precondition this file
existed to gate. What survives now is a permanent regression pin of the
POST-deletion shape: exactly ONE production call site (the registry handler,
always passing ``scope_source`` explicitly), and the retired symbol name
gone from BOTH modules — never resurrected as a shim.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from specify_cli.cli.commands.agent import tasks as tasks_compat
from specify_cli.cli.commands.agent import tasks_move_task as tmt
from specify_cli.review import gate_registry
from specify_cli.review.scope_source import GateCoverageScopeSource
from specify_cli.status.models import Lane

pytestmark = [pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"

_EVALUATE_SYMBOL = "evaluate_pre_review_gate"
_RETIRED_CENSUS_CALLER_SYMBOL = "_mt_pre_review_gate_verdict"

_REGISTRY_HANDLER_FILE = Path("src/specify_cli/review/gate_registry.py")


def _callee_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _call_sites(symbol: str) -> list[tuple[Path, ast.Call]]:
    """Every ``ast.Call`` node under ``src/`` whose callee is named ``symbol``.

    Matches both a bare name (``evaluate_pre_review_gate(...)``) and a dotted
    attribute access (``pre_review_gate.evaluate_pre_review_gate(...)``) --
    the two calling conventions actually used in this codebase -- so a call
    site is never missed just because of how a module imported the symbol.
    A ``def``/``import ... as`` reference is never an ``ast.Call`` node, so
    this walk naturally excludes definitions and compat re-exports.
    """
    sites: list[tuple[Path, ast.Call]] = []
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _callee_name(node) == symbol:
                sites.append((path.relative_to(_REPO_ROOT), node))
    return sites


def _call_kwargs(call: ast.Call) -> set[str]:
    return {kw.arg for kw in call.keywords if kw.arg is not None}


def test_evaluate_pre_review_gate_has_exactly_one_production_call_site() -> None:
    """(FR-002 post-deletion) the retired census branch's ONLY caller is gone
    — the sole surviving production call site is the named-handler registry.

    A second call site reappearing would mean a new caller reaches
    ``evaluate_pre_review_gate`` unaccounted for; a ``scope_source=None`` call
    site reappearing would resurrect the retired census default (now a
    ``TypeError`` — ``scope_source`` is a required, keyword-only parameter)."""
    sites = _call_sites(_EVALUATE_SYMBOL)
    call_files = {path for path, _ in sites}
    assert call_files == {_REGISTRY_HANDLER_FILE}, (
        "evaluate_pre_review_gate call sites drifted from the post-WP04 "
        f"characterized set; found {sorted(str(f) for f in call_files)}"
    )


def test_registry_handler_call_site_names_scope_source_explicitly() -> None:
    """The registry handler's call site names ``scope_source`` explicitly --
    the live ``for_review`` dispatch path never omits it."""
    matches = [call for path, call in _call_sites(_EVALUATE_SYMBOL) if path == _REGISTRY_HANDLER_FILE]
    assert len(matches) == 1
    assert "scope_source" in _call_kwargs(matches[0])


def test_registry_handler_resolves_a_concrete_non_none_scope_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime confirmation: dispatching the registry handler with a real
    ``TransitionGateContext`` reaches ``evaluate_pre_review_gate`` with a
    concrete (non-``None``) ``scope_source`` -- never a default."""
    from specify_cli.review.pre_review_gate import GateOutcome, GateVerdict, ScopeResult

    captured: dict[str, Any] = {}

    def _spy(_changed_files: Any, **kwargs: Any) -> GateVerdict:
        captured.update(kwargs)
        return GateVerdict(
            outcome=GateOutcome.NO_COVERAGE,
            scope=ScopeResult.from_override(()),
            reason="stub verdict -- evaluate_pre_review_gate is monkeypatched for this test",
        )

    monkeypatch.setattr(gate_registry, "evaluate_pre_review_gate", _spy)
    scope_source = GateCoverageScopeSource(repo_root=_REPO_ROOT)
    ctx = gate_registry.TransitionGateContext(
        changed_files=("src/example.py",),
        scope_source=scope_source,
        baseline=None,
        repo_root=_REPO_ROOT,
        force=False,
        from_lane=Lane.IN_PROGRESS,
        to_lane=Lane.FOR_REVIEW,
    )
    gate_registry._spec_kitty_pre_review_handler(ctx)
    assert "scope_source" in captured
    assert captured["scope_source"] is not None
    assert captured["scope_source"] is scope_source


def test_retired_census_caller_has_no_call_site_anywhere() -> None:
    """The dead composition helper this file originally characterized as
    "reachable only via a compat re-export" is now deleted outright (WP04,
    data-model.md sec. 6) -- it must never gain a call site again (that would
    mean a shim or reintroduction slipped back in)."""
    sites = _call_sites(_RETIRED_CENSUS_CALLER_SYMBOL)
    assert sites == [], (
        f"{_RETIRED_CENSUS_CALLER_SYMBOL} gained a call site after its WP04 "
        f"retirement: {[str(path) for path, _ in sites]}"
    )


def test_retired_census_caller_is_gone_from_both_modules_not_re_shimmed() -> None:
    """Sanity companion: the retired symbol is absent from BOTH
    ``tasks_move_task.py`` (its former home) and ``tasks.py`` (its former
    compat re-export) -- never resurrected as a shim on either surface."""
    assert not hasattr(tmt, _RETIRED_CENSUS_CALLER_SYMBOL)
    assert not hasattr(tasks_compat, _RETIRED_CENSUS_CALLER_SYMBOL)

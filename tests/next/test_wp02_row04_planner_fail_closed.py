"""WP02 / census row 4 — ``planner._resolve_workflow_for_mission`` fails closed.

Census row 4 of ``kitty-specs/meta-fail-closed-3162-01KZ7FSQ/contracts/routing-manifest.md``
§1.4: ``runtime.next._internal_runtime.planner._resolve_workflow_for_mission`` reads
``meta.json`` through ``specify_cli.mission_metadata.load_meta`` on the signature
default (``on_malformed="raise"``) with **no** handler, so a corrupt ``meta.json``
throws a bare :class:`ValueError` straight onto the ``spec-kitty next`` path.
This is the REFUSE-raw arm; WP02 routes it onto
``specify_cli.core.paths.load_meta_fail_closed`` so the escape is the typed
:class:`~specify_cli.core.paths.MissionMetaReadError` instead (FR-001).

Two independent proofs, because either one alone is cheatable:

* **behavioural** — the raised error carries a ``load_meta_fail_closed`` frame in
  ``core/paths.py`` and preserves the decode :class:`ValueError` as ``__cause__``.
  Without the frame check, ``except ValueError: raise MissionMetaReadError(...)``
  at the entry point satisfies "a typed error reaches the caller" with **zero**
  routing — the ``SC-001`` cheat.
* **structural** — an AST call-count assertion over the routed function's **own
  body**: exactly one ``load_meta_fail_closed(`` call and zero ``load_meta(``
  calls, matched on the **exact callee name**. A substring check is green under a
  fold; the routed-count floor is green under a fold too (128 satisfies all three
  clauses of ``test_routed_load_meta_floor`` at floor 126 / margin 4). The count
  assertion is what closes the budget for this row.

``C-001``: no arm changes — the ``if meta is None:`` default-workflow arm and the
``workflow_id is None`` arm keep their current behaviour, pinned by the negative
controls below (including ``NFR-001``'s absent-file arm).
"""

from __future__ import annotations

import ast
import json
import traceback
from collections import Counter
from pathlib import Path

import pytest

from runtime.next._internal_runtime import planner as planner_mod
from runtime.next.runtime_bridge_engine import resolve_workflow_for_mission
from specify_cli.core.paths import MissionMetaReadError

# ``unit`` is the category (the tests inspect a return value / a raise against a
# ``tmp_path`` meta.json, nothing more); ``fast`` is the orthogonal performance
# characterisation the taxonomy defines separately
# (``docs/context/testing-taxonomy.md`` §Fast) — measured 0.06 s for the slowest
# item, no subprocess, no git, no network.
#
# ``fast`` is load-bearing for CI selection, not decoration (mission
# meta-fail-closed-3162-01KZ7FSQ, WP08 / ledger F10). This file sits under a
# ``next`` shard-group root, so GC-1 requires it to carry a ``next_shard_N``
# marker (``tests/_next_shard_map.py``) — and ``unit-contract-residual``, the only
# job that selected it while it was ``unit``-only, excludes every ``next_shard_*``
# test by construction (``ci-quality.yml``:
# ``-m "(unit or contract) and not (... or next_shard_1 or next_shard_2 or next_shard_3)"``).
# Sharding it without this marker would therefore have moved it from one gate to
# zero. ``fast`` puts it in ``fast-tests-next`` (``tests/next/ tests/specify_cli/next/
# tests/runtime/ -m "fast and not windows_ci"``), which is shard-agnostic.
pytestmark = [pytest.mark.unit, pytest.mark.fast]

#: Truncated, syntactically invalid JSON — genuinely unparseable, a REAL corrupt
#: file (FR-001 forbids patching the reader to simulate corruption).
_CORRUPT_META = '{"workflow_id":'

#: The permanent default both no-meta arms resolve to (NEW-2 resolution).
_DEFAULT_WORKFLOW = "software-dev-default"

#: The module under census, taken from the **imported** module's own ``__file__``
#: rather than from this test file's location. That makes the AST census and the
#: behavioural drive read the SAME tree by construction, closing the split-tree
#: hazard (an editable ``.pth`` can pin imports to a different ``src/`` than a
#: test-file-relative ``SRC_ROOT`` derives).
_PLANNER_SRC = Path(planner_mod.__file__)


def direct_call_names(module_path: Path, func_name: str) -> Counter[str]:
    """Count calls by EXACT callee name inside *func_name*'s own body.

    Nested ``def`` / ``async def`` / ``lambda`` bodies are excluded, so "own
    body" means exactly that and a helper defined inside the function cannot
    launder a call out of the count.

    Callee names are exact, never substrings: ``load_meta_fail_closed`` counts
    under its own key and never increments ``load_meta``. A substring test
    ("is ``load_meta_fail_closed(`` in the source") passes when two reads have
    been folded into one, which is precisely the failure this assertion exists
    to catch.
    """
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    target: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == func_name:
            target = node
            break
    assert target is not None, f"{func_name} is not defined in {module_path}"

    counts: Counter[str] = Counter()
    stack: list[ast.AST] = list(ast.iter_child_nodes(target))
    while stack:
        node = stack.pop()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            continue  # a nested definition is not this function's own body
        if isinstance(node, ast.Call):
            callee = node.func
            if isinstance(callee, ast.Name):
                counts[callee.id] += 1
            elif isinstance(callee, ast.Attribute):
                counts[callee.attr] += 1
        stack.extend(ast.iter_child_nodes(node))
    return counts


def assert_raised_from_the_routed_seam(exc: MissionMetaReadError) -> None:
    """Assert *exc* was raised BY ``load_meta_fail_closed``, not re-wrapped locally.

    This is the anti-``SC-001`` assertion: it distinguishes a genuinely routed
    call site from a public entry point that wraps a still-unrouted ``load_meta``
    in ``except ValueError: raise MissionMetaReadError(...)``.
    """
    frames = traceback.extract_tb(exc.__traceback__)
    seam = [f for f in frames if f.name == "load_meta_fail_closed"]
    assert seam, (
        "no 'load_meta_fail_closed' frame in the traceback — the typed error did "
        "not come from the routed seam (SC-001 cheat shape). frames="
        f"{[f.name for f in frames]}"
    )
    assert seam[0].filename.replace("\\", "/").endswith("core/paths.py"), (
        f"the load_meta_fail_closed frame is not core/paths.py: {seam[0].filename}"
    )
    assert isinstance(exc.__cause__, ValueError), (
        "the underlying decode ValueError was not preserved as __cause__; got "
        f"{exc.__cause__!r}"
    )
    assert not isinstance(exc, ValueError), (
        "MissionMetaReadError must NOT be a ValueError (MRO RuntimeError -> "
        "Exception) or callers' existing 'except ValueError' arms would still "
        "absorb the fail-closed refusal"
    )


def test_census_row04_corrupt_meta_raises_typed_error_from_the_routed_seam(
    tmp_path: Path,
) -> None:
    """Census row 4: a corrupt ``meta.json`` raises the typed error, not ``ValueError``."""
    (tmp_path / "meta.json").write_text(_CORRUPT_META, encoding="utf-8")

    with pytest.raises(MissionMetaReadError) as excinfo:
        resolve_workflow_for_mission(tmp_path)

    assert_raised_from_the_routed_seam(excinfo.value)


def test_census_row04_is_routed_exactly_once_and_is_not_folded() -> None:
    """Census row 4's structural proof — the per-site call-count assertion.

    One routed call in, one routed call out: WP02 is 0-net on the routed census
    (``contracts/headroom-allocation.md`` §2), so a helper wrapping (which adds a
    call) or a fold (which removes one) both fail here rather than surfacing only
    at integration.
    """
    counts = direct_call_names(_PLANNER_SRC, "_resolve_workflow_for_mission")
    assert counts["load_meta_fail_closed"] == 1, (
        "_resolve_workflow_for_mission must hold EXACTLY ONE load_meta_fail_closed("
        f") call in its own body; found {counts['load_meta_fail_closed']}"
    )
    assert counts["load_meta"] == 0, (
        "_resolve_workflow_for_mission still calls load_meta( directly; census "
        f"row 4 is not routed. count={counts['load_meta']}"
    )


def test_census_row04_module_carries_no_local_typed_raise() -> None:
    """The module must not manufacture the typed error itself (anti-``SC-001``)."""
    source = _PLANNER_SRC.read_text(encoding="utf-8")
    assert "raise MissionMetaReadError" not in source, (
        "planner.py raises MissionMetaReadError locally — that is the SC-001 "
        "cheat, not routing through the seam"
    )
    assert "except ValueError" not in source, (
        "planner.py grew an 'except ValueError' arm; census row 4 is REFUSE-raw "
        "and must keep propagating (C-001 — no arm changes)"
    )


def test_census_row04_negative_control_absent_meta_still_resolves_default(
    tmp_path: Path,
) -> None:
    """``NFR-001`` absent-file arm: a missing ``meta.json`` is NOT a read failure."""
    assert not (tmp_path / "meta.json").exists()
    assert resolve_workflow_for_mission(tmp_path).workflow_id == _DEFAULT_WORKFLOW


def test_census_row04_negative_control_valid_meta_still_resolves_default(
    tmp_path: Path,
) -> None:
    """``C-001``: a valid ``meta.json`` without ``workflow_id`` keeps its arm."""
    (tmp_path / "meta.json").write_text(
        json.dumps({"mission_id": "01KVN754TY9CVJ8G10ERTMPVRH"}), encoding="utf-8"
    )
    assert resolve_workflow_for_mission(tmp_path).workflow_id == _DEFAULT_WORKFLOW

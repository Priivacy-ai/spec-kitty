"""WP02 / census row 7 — ``gate.ensure_occurrence_classification_ready`` fails closed.

Census row 7 of ``kitty-specs/meta-fail-closed-3162-01KZ7FSQ/contracts/routing-manifest.md``
§1.4: ``specify_cli.bulk_edit.gate.ensure_occurrence_classification_ready`` performs
its **own** ``meta.json`` read (``gate.py:80``), separate from
``_is_bulk_edit_mission``'s (census row 6, ``gate.py:57``). It reads through
``specify_cli.mission_metadata.load_meta`` on the signature default
(``on_malformed="raise"``) with no handler — the REFUSE-raw arm. WP02 routes it
onto ``specify_cli.core.paths.load_meta_fail_closed`` (FR-001).

``ensure_occurrence_classification_ready`` is public and is the entry
``spec-kitty implement`` uses, so it is driven directly — no wrapper needed.

This file carries the **module-wide** anti-fold pair that row 6's test could not:
once census rows 6 and 7 are both routed, ``gate.py`` must hold **zero**
``load_meta(`` calls and **exactly two** ``load_meta_fail_closed(`` calls. That
pair is what catches a collapse of the two ``gate.py`` reads into one shared
helper — a fold the routed-count floor cannot see (128 satisfies all three clauses
of ``test_routed_load_meta_floor`` at floor 126 / margin 4).

``C-001``: the ``if meta is None: return GateResult(passed=True, change_mode=None)``
arm is unchanged, pinned by the negative controls below.
"""

from __future__ import annotations

import ast
import json
import traceback
from collections import Counter
from pathlib import Path

import pytest

from specify_cli.bulk_edit import gate as gate_mod
from specify_cli.bulk_edit.gate import GateResult, ensure_occurrence_classification_ready
from specify_cli.core.paths import MissionMetaReadError

pytestmark = pytest.mark.unit

#: Truncated, syntactically invalid JSON — a REAL corrupt file.
_CORRUPT_META = '{"change_mode":'

_MISSION_ID = "01KVN754TY9CVJ8G10ERTMPVRH"

#: An occurrence map that validates AND is admissible (all 8 standard categories).
#: Same shape as ``tests/specify_cli/bulk_edit/test_gate.py``'s
#: ``VALID_OCCURRENCE_MAP`` — reused rather than reinvented.
_VALID_OCCURRENCE_MAP = """\
target:
  term: oldName
  replacement: newName
  operation: rename
categories:
  code_symbols:
    action: rename
  import_paths:
    action: rename
  filesystem_paths:
    action: manual_review
  serialized_keys:
    action: do_not_change
  cli_commands:
    action: do_not_change
  user_facing_strings:
    action: rename_if_user_visible
  tests_fixtures:
    action: rename
  logs_telemetry:
    action: do_not_change
"""

#: Census target, taken from the **imported** module's own ``__file__`` so the AST
#: census and the behavioural drive read the same tree by construction.
_GATE_SRC = Path(gate_mod.__file__)


def direct_call_names(module_path: Path, func_name: str | None = None) -> Counter[str]:
    """Count calls by EXACT callee name.

    With *func_name*, the scope is that function's **own body** (nested ``def`` /
    ``async def`` / ``lambda`` bodies excluded). With ``None``, the scope is the
    whole module — which is how the two-``gate.py``-reads anti-fold pair is
    asserted.

    Callee names are exact, never substrings: ``load_meta_fail_closed`` counts
    under its own key and never increments ``load_meta``.
    """
    tree = ast.parse(module_path.read_text(encoding="utf-8"))

    root: ast.AST = tree
    if func_name is not None:
        found: ast.FunctionDef | ast.AsyncFunctionDef | None = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == func_name:
                found = node
                break
        assert found is not None, f"{func_name} is not defined in {module_path}"
        root = found

    counts: Counter[str] = Counter()
    stack: list[ast.AST] = list(ast.iter_child_nodes(root))
    while stack:
        node = stack.pop()
        if func_name is not None and isinstance(
            node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda
        ):
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
    """Assert *exc* was raised BY ``load_meta_fail_closed`` (anti-``SC-001``)."""
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
        f"the decode ValueError was not preserved as __cause__; got {exc.__cause__!r}"
    )
    assert not isinstance(exc, ValueError), (
        "MissionMetaReadError must NOT be a ValueError, or existing 'except "
        "ValueError' arms would absorb the fail-closed refusal"
    )


def test_census_row07_corrupt_meta_raises_typed_error_from_the_gate_entry(
    tmp_path: Path,
) -> None:
    """Census row 7 via the public entry ``ensure_occurrence_classification_ready``."""
    (tmp_path / "meta.json").write_text(_CORRUPT_META, encoding="utf-8")

    with pytest.raises(MissionMetaReadError) as excinfo:
        ensure_occurrence_classification_ready(tmp_path)

    assert_raised_from_the_routed_seam(excinfo.value)
    names = [f.name for f in traceback.extract_tb(excinfo.value.__traceback__)]
    assert "ensure_occurrence_classification_ready" in names, (
        f"the refusal did not come from census row 7's entry. frames={names}"
    )
    assert "_is_bulk_edit_mission" not in names, (
        "the refusal came from census row 6's read, not row 7's own read at "
        f"gate.py:80 — row 7's read must fire first. frames={names}"
    )


def test_census_row07_is_routed_exactly_once_and_is_not_folded() -> None:
    """Census row 7's structural proof — the per-site call-count assertion."""
    counts = direct_call_names(_GATE_SRC, "ensure_occurrence_classification_ready")
    assert counts["load_meta_fail_closed"] == 1, (
        "ensure_occurrence_classification_ready must hold EXACTLY ONE "
        "load_meta_fail_closed() call in its own body; found "
        f"{counts['load_meta_fail_closed']}"
    )
    assert counts["load_meta"] == 0, (
        "ensure_occurrence_classification_ready still calls load_meta( directly; "
        f"census row 7 is not routed. count={counts['load_meta']}"
    )


def test_gate_module_holds_exactly_two_routed_reads_and_no_unrouted_read() -> None:
    """Module-wide anti-fold pair for ``gate.py``'s TWO reads (census rows 6 + 7).

    A shared ``_read_meta(dir)`` helper collapsing both reads into one takes the
    lane's routed census to 128 — inside the ``[127, 130]`` band and green against
    all three clauses of ``test_routed_load_meta_floor``, so the floor cannot
    catch it. This assertion can.
    """
    counts = direct_call_names(_GATE_SRC)
    assert counts["load_meta"] == 0, (
        f"gate.py still calls load_meta( somewhere; count={counts['load_meta']}"
    )
    assert counts["load_meta_fail_closed"] == 2, (
        "gate.py must hold EXACTLY TWO load_meta_fail_closed() calls — census row "
        "6 (_is_bulk_edit_mission) and census row 7 "
        "(ensure_occurrence_classification_ready), NOT folded into one shared "
        f"helper; found {counts['load_meta_fail_closed']}"
    )


def test_gate_module_no_longer_imports_the_unrouted_reader() -> None:
    """``gate.py``'s ``load_meta`` import is gone once both rows are routed (F401)."""
    source = _GATE_SRC.read_text(encoding="utf-8")
    assert "from specify_cli.mission_metadata import load_meta" not in source, (
        "gate.py still imports load_meta; with both census rows 6 and 7 routed the "
        "import is unused and ruff F401 flags it"
    )
    assert "raise MissionMetaReadError" not in source, (
        "gate.py raises MissionMetaReadError locally — that is the SC-001 cheat"
    )


def test_census_row07_negative_control_absent_meta_passes_with_no_change_mode(
    tmp_path: Path,
) -> None:
    """``NFR-001`` absent-file arm: a missing ``meta.json`` still passes the gate."""
    assert not (tmp_path / "meta.json").exists()
    assert ensure_occurrence_classification_ready(tmp_path) == GateResult(
        passed=True, change_mode=None
    )


def test_census_row07_negative_control_valid_non_bulk_edit_passes(
    tmp_path: Path,
) -> None:
    """``C-001``: a valid non-bulk-edit mission still passes at zero cost."""
    (tmp_path / "meta.json").write_text(
        json.dumps({"mission_id": _MISSION_ID}), encoding="utf-8"
    )
    result = ensure_occurrence_classification_ready(tmp_path)
    assert result.passed is True
    assert result.errors == []


def test_census_row07_negative_control_valid_bulk_edit_with_good_map_passes(
    tmp_path: Path,
) -> None:
    """``C-001``: a valid bulk-edit mission with a good occurrence map still passes."""
    (tmp_path / "meta.json").write_text(
        json.dumps({"mission_id": _MISSION_ID, "change_mode": "bulk_edit"}),
        encoding="utf-8",
    )
    (tmp_path / "occurrence_map.yaml").write_text(
        _VALID_OCCURRENCE_MAP, encoding="utf-8"
    )
    result = ensure_occurrence_classification_ready(tmp_path)
    assert result.change_mode == "bulk_edit"
    assert result.passed is True, result.errors

"""WP02 / census row 6 — ``gate._is_bulk_edit_mission`` fails closed.

Census row 6 of ``kitty-specs/meta-fail-closed-3162-01KZ7FSQ/contracts/routing-manifest.md``
§1.4: ``specify_cli.bulk_edit.gate._is_bulk_edit_mission`` reads ``meta.json``
through ``specify_cli.mission_metadata.load_meta`` on the signature default
(``on_malformed="raise"``) with **no** handler — the REFUSE-raw arm, so a corrupt
``meta.json`` throws a bare :class:`ValueError` out of the bulk-edit gate. WP02
routes it onto ``specify_cli.core.paths.load_meta_fail_closed`` (FR-001).

Entry point matters here. The corrupt file is driven through
``specify_cli.bulk_edit.gate.check_review_diff_compliance``, whose first statement
is ``if not _is_bulk_edit_mission(feature_dir)`` — so the read that fires is row
6's. ``ensure_occurrence_classification_ready`` is **not** used: it performs its
OWN ``meta.json`` read first (census row 7, ``gate.py:80``), so driving it would
silently test the other row.

Scope note on the structural assertion. It is scoped to
``_is_bulk_edit_mission``'s **own body**, not to the module: at this commit
``ensure_occurrence_classification_ready`` still holds a live ``load_meta(`` call
(census row 7 is routed in T010), so a module-wide zero-``load_meta`` assertion
would be red here for the wrong reason. The module-wide pair is asserted in
``test_wp02_row07_gate_entry_fail_closed.py`` once both rows are routed.

``C-001``: the ``meta is not None and meta.get("change_mode") == "bulk_edit"``
guard is unchanged, pinned by the negative controls below.
"""

from __future__ import annotations

import ast
import json
import traceback
from collections import Counter
from pathlib import Path

import pytest

from specify_cli.bulk_edit import gate as gate_mod
from specify_cli.bulk_edit.gate import _is_bulk_edit_mission, check_review_diff_compliance
from specify_cli.core.paths import MissionMetaReadError

pytestmark = pytest.mark.unit

#: Truncated, syntactically invalid JSON — a REAL corrupt file.
_CORRUPT_META = '{"change_mode":'

_MISSION_ID = "01KVN754TY9CVJ8G10ERTMPVRH"

#: Census target, taken from the **imported** module's own ``__file__`` so the AST
#: census and the behavioural drive read the same tree by construction.
_GATE_SRC = Path(gate_mod.__file__)


def direct_call_names(module_path: Path, func_name: str) -> Counter[str]:
    """Count calls by EXACT callee name inside *func_name*'s own body.

    Nested ``def`` / ``async def`` / ``lambda`` bodies are excluded. Callee names
    are exact, never substrings: ``load_meta_fail_closed`` counts under its own
    key and never increments ``load_meta``.
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
            continue
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


def test_census_row06_corrupt_meta_raises_typed_error_via_review_diff_entry(
    tmp_path: Path,
) -> None:
    """Census row 6 via the public entry ``gate.check_review_diff_compliance``."""
    (tmp_path / "meta.json").write_text(_CORRUPT_META, encoding="utf-8")

    with pytest.raises(MissionMetaReadError) as excinfo:
        check_review_diff_compliance(tmp_path, tmp_path, "HEAD~1", "HEAD")

    assert_raised_from_the_routed_seam(excinfo.value)
    names = [f.name for f in traceback.extract_tb(excinfo.value.__traceback__)]
    assert "_is_bulk_edit_mission" in names, (
        f"the refusal did not come from census row 6's read. frames={names}"
    )


def test_census_row06_is_routed_exactly_once_and_is_not_folded() -> None:
    """Census row 6's structural proof — the per-site call-count assertion.

    Scoped to ``_is_bulk_edit_mission``'s own body: row 7 (``gate.py:80``) is
    still unrouted at this commit, so the module-wide count is asserted by row
    7's test instead.
    """
    counts = direct_call_names(_GATE_SRC, "_is_bulk_edit_mission")
    assert counts["load_meta_fail_closed"] == 1, (
        "_is_bulk_edit_mission must hold EXACTLY ONE load_meta_fail_closed() call "
        f"in its own body; found {counts['load_meta_fail_closed']}"
    )
    assert counts["load_meta"] == 0, (
        "_is_bulk_edit_mission still calls load_meta( directly; census row 6 is "
        f"not routed. count={counts['load_meta']}"
    )


def test_census_row06_module_carries_no_local_typed_raise() -> None:
    """The module must not manufacture the typed error itself (anti-``SC-001``).

    Note this asserts only the absence of a local ``raise MissionMetaReadError``.
    ``gate.py`` legitimately contains an ``except ValueError`` inside
    ``_feature_dir_rel`` catching ``Path.relative_to``'s ``ValueError``
    (``routing-manifest.md`` §2.2 records it as a *spurious* hit of the
    ``except ValueError`` census — it is not a ``meta.json`` read arm), so a
    module-wide ``"except ValueError" not in source`` assertion would be wrong
    here.
    """
    source = _GATE_SRC.read_text(encoding="utf-8")
    assert "raise MissionMetaReadError" not in source, (
        "gate.py raises MissionMetaReadError locally — that is the SC-001 cheat, "
        "not routing through the seam"
    )


def test_census_row06_negative_control_absent_meta_is_not_bulk_edit(
    tmp_path: Path,
) -> None:
    """``NFR-001`` absent-file arm: a missing ``meta.json`` is ``False``, not a raise."""
    assert not (tmp_path / "meta.json").exists()
    assert _is_bulk_edit_mission(tmp_path) is False
    assert check_review_diff_compliance(tmp_path, tmp_path, "HEAD~1", "HEAD") is None


def test_census_row06_negative_control_valid_non_bulk_edit_is_false(
    tmp_path: Path,
) -> None:
    """``C-001``: a valid non-bulk-edit ``meta.json`` still answers ``False``."""
    (tmp_path / "meta.json").write_text(
        json.dumps({"mission_id": _MISSION_ID}), encoding="utf-8"
    )
    assert _is_bulk_edit_mission(tmp_path) is False
    assert check_review_diff_compliance(tmp_path, tmp_path, "HEAD~1", "HEAD") is None


def test_census_row06_negative_control_valid_bulk_edit_is_true(tmp_path: Path) -> None:
    """``C-001``: a valid ``change_mode: bulk_edit`` mission still answers ``True``."""
    (tmp_path / "meta.json").write_text(
        json.dumps({"mission_id": _MISSION_ID, "change_mode": "bulk_edit"}),
        encoding="utf-8",
    )
    assert _is_bulk_edit_mission(tmp_path) is True

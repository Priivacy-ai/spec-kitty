"""WP03 — merge-pipeline ratchets (#1826 / #1736 residuals).

Recurrence guards for mission ``coordination-merge-stabilization-01KTXRVR``:

* **AC-B3** — no raw ``git update-ref`` subprocess invocation exists in
  ``src/specify_cli`` outside ``git/ref_advance.py``. Any new ref-advance
  site re-inherits #1826 (a checked-out worktree left behind its own HEAD)
  unless it goes through :func:`specify_cli.git.ref_advance.advance_branch_ref`.
* **AC-F1** — every subprocess call site in ``lanes/merge.py`` routes its
  environment through ``_make_merge_env()`` (FR-008b): no bare ``os.environ``
  copies outside the helper, and no subprocess call without an ``env=``
  keyword.
* **AC-F3** — the GENESIS fallback in
  ``coordination/status_transition.py`` catches exactly the two documented
  expected failures (``ValueError``, ``FileNotFoundError``); anything else
  propagates (FR-008d).
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest

import specify_cli
from specify_cli.status import Lane

pytestmark = [pytest.mark.architectural]

SRC_ROOT = Path(specify_cli.__file__).resolve().parent
LANES_MERGE = SRC_ROOT / "lanes" / "merge.py"
REF_ADVANCE_RELPATH = Path("git") / "ref_advance.py"


def _python_sources() -> list[Path]:
    return sorted(SRC_ROOT.rglob("*.py"))


# ---------------------------------------------------------------------------
# AC-B3 — no raw update-ref outside git/ref_advance.py
# ---------------------------------------------------------------------------


def _update_ref_string_constants(tree: ast.AST) -> list[int]:
    """Line numbers of ``"update-ref"`` string constants (argv elements)."""
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value == "update-ref"
    ]


def test_no_raw_update_ref_outside_ref_advance_helper() -> None:
    """AC-B3 (#1826): ``advance_branch_ref`` is the only sanctioned way to
    advance a branch ref. A raw ``git update-ref`` bypasses the
    checked-out-worktree resync and re-introduces the defect class."""
    offenders: list[str] = []
    for source in _python_sources():
        relpath = source.relative_to(SRC_ROOT)
        if relpath == REF_ADVANCE_RELPATH:
            continue
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        offenders.extend(
            f"{relpath}:{lineno}" for lineno in _update_ref_string_constants(tree)
        )
    assert not offenders, (
        "Raw `git update-ref` invocation(s) found outside "
        "specify_cli/git/ref_advance.py — route them through "
        f"advance_branch_ref() (#1826 / AC-B3): {offenders}"
    )


# ---------------------------------------------------------------------------
# AC-F1 — single environment authority in the lane-merge pipeline
# ---------------------------------------------------------------------------


def _is_subprocess_run_call(node: ast.Call) -> bool:
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "run"
        and isinstance(func.value, ast.Name)
        and func.value.id == "subprocess"
    )


def test_lanes_merge_subprocess_calls_route_env_through_helper() -> None:
    """AC-F1 (FR-008b): every ``subprocess.run`` in ``lanes/merge.py`` carries
    an explicit ``env=`` keyword (sourced from ``_make_merge_env``), so the
    pipeline has exactly one environment authority."""
    tree = ast.parse(LANES_MERGE.read_text(encoding="utf-8"), filename=str(LANES_MERGE))
    missing_env = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and _is_subprocess_run_call(node)
        and not any(kw.arg == "env" for kw in node.keywords)
    ]
    assert not missing_env, (
        "subprocess.run call(s) in lanes/merge.py without an env= keyword "
        f"(must route through _make_merge_env, AC-F1): lines {missing_env}"
    )


def test_lanes_merge_no_bare_os_environ_outside_helper() -> None:
    """AC-F1 (FR-008b): no ``os.environ`` access in ``lanes/merge.py`` outside
    the ``_make_merge_env`` helper — no ad-hoc PATH/GIT_* mutations."""
    tree = ast.parse(LANES_MERGE.read_text(encoding="utf-8"), filename=str(LANES_MERGE))
    helper_spans: list[tuple[int, int]] = [
        (node.lineno, node.end_lineno or node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "_make_merge_env"
    ]
    assert helper_spans, "_make_merge_env must exist in lanes/merge.py (AC-F1)"

    offenders = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
        and not any(start <= node.lineno <= end for start, end in helper_spans)
    ]
    assert not offenders, (
        "bare os.environ access in lanes/merge.py outside _make_merge_env "
        f"(AC-F1): lines {offenders}"
    )


def test_make_merge_env_matches_historical_inline_construction() -> None:
    """T015 is refactor-only: the helper's env is byte-identical to the inline
    construction it replaced (venv-bin PATH prepend over ``os.environ``)."""
    from specify_cli.lanes.merge import _make_merge_env

    expected = os.environ.copy()
    expected["PATH"] = (
        str(Path(sys.executable).parent) + os.pathsep + expected.get("PATH", "")
    )
    assert _make_merge_env() == expected


# ---------------------------------------------------------------------------
# AC-F3 — narrow GENESIS-fallback exception mask (FR-008d)
# ---------------------------------------------------------------------------


def _read_state(tmp_path: Path) -> tuple[Lane, str | None]:
    from specify_cli.coordination.status_transition import (
        read_current_wp_state_transactional,
    )

    feature_dir = tmp_path / "kitty-specs" / "099-mask-test"
    feature_dir.mkdir(parents=True, exist_ok=True)
    state: tuple[Lane, str | None] = read_current_wp_state_transactional(
        feature_dir=feature_dir,
        mission_slug="099-mask-test",
        wp_id="WP01",
        repo_root=tmp_path,  # not a git repo → transaction topology unavailable
    )
    return state


def _absent_log_error() -> Exception:
    from specify_cli.status.lane_reader import CanonicalStatusNotFoundError

    return CanonicalStatusNotFoundError("expected miss")


@pytest.mark.parametrize(
    "expected_exc",
    [
        ValueError("expected miss"),
        FileNotFoundError("expected miss"),
        # The codebase's concrete "absent log" signal — the failure shape the
        # contract (R7) denotes by FileNotFoundError.
        _absent_log_error(),
    ],
    ids=["pre-schema-value", "absent-file", "absent-canonical-log"],
)
def test_genesis_fallback_catches_documented_expected_types(
    tmp_path: Path, expected_exc: Exception
) -> None:
    """AC-F3: the two documented expected failure shapes (pre-schema lane
    value, absent log/WP file) fall back to GENESIS."""
    from unittest.mock import patch

    with patch(
        "specify_cli.status.lane_reader.get_wp_lane",
        side_effect=expected_exc,
    ):
        lane, actor = _read_state(tmp_path)
    assert lane == Lane.GENESIS
    assert actor is None


def test_genesis_fallback_propagates_unexpected_exceptions(tmp_path: Path) -> None:
    """AC-F3: a non-expected exception (e.g. ``PermissionError``) is a real
    error signal and MUST propagate — the former broad ``except Exception``
    silently converted it into "unseeded WP" (#1736 dormant mask 1)."""
    from unittest.mock import patch

    with patch(
        "specify_cli.status.lane_reader.get_wp_lane",
        side_effect=PermissionError("events log unreadable"),
    ), pytest.raises(PermissionError):
        _read_state(tmp_path)

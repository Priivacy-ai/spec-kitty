"""Guard for planning#88: a parametrized test must never feed a bare ``tmp_path`` to a
path-keyed cache consumer.

See ``tests/architectural/_tmp_path_cache_key_scan.py`` for the full rationale — PR #72 fixed
the one live instance (``_home_pin_scan.py::_corpus``'s caller) and this sweep adds the
mechanised check the squad recommended so a future parametrized caller reds here instead of
silently reading a sibling parametrization's stale parse.

Both halves of the pair (C-003 form (ii)): the real tree must have zero hits, and the SAME
matcher run over a materialised violation must catch it. An empty-set assertion without the
second run proves nothing.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from tests.architectural import _tmp_path_cache_key_scan as guard

pytestmark = pytest.mark.architectural

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = REPO_ROOT / "tests"


def test_no_parametrized_test_feeds_a_bare_tmp_path_to_a_path_keyed_cache_consumer() -> None:
    """(i) of the pair: zero real-tree hits today."""
    hits = guard.scan_tree(TESTS_ROOT)
    assert hits == [], f"parametrized test(s) feeding a bare tmp_path to a path-keyed cache: {hits}"


def test_the_guard_catches_a_planted_violation(tmp_path: Path) -> None:
    """(ii) of the pair: the SAME matcher over a module containing the exact shape."""
    planted = tmp_path / "test_planted_violation.py"
    planted.write_text(
        textwrap.dedent(
            """\
            import pytest

            @pytest.mark.parametrize("limb_id", ["a", "b"])
            def test_something(tmp_path, limb_id):
                scan_graph_monolith_paths(tmp_path)
            """
        ),
        encoding="utf-8",
    )
    hits = guard.scan_tree(tmp_path)
    assert hits == [
        guard.Hit(
            relpath="test_planted_violation.py",
            lineno=5,
            test_name="test_something",
            callee="scan_graph_monolith_paths",
        )
    ], f"control returned {hits!r} — a control returning [] proves nothing"


def test_the_guard_catches_a_planted_keyword_argument_violation(tmp_path: Path) -> None:
    """Positive control: the defect is identical when tmp_path is passed by keyword."""
    planted = tmp_path / "test_planted_keyword_violation.py"
    planted.write_text(
        textwrap.dedent(
            """\
            import pytest

            @pytest.mark.parametrize("limb_id", ["a", "b"])
            def test_something(tmp_path, limb_id):
                scan_graph_monolith_paths(root=tmp_path)
            """
        ),
        encoding="utf-8",
    )
    hits = guard.scan_tree(tmp_path)
    assert hits == [
        guard.Hit(
            relpath="test_planted_keyword_violation.py",
            lineno=5,
            test_name="test_something",
            callee="scan_graph_monolith_paths",
        )
    ], f"keyword-argument control returned {hits!r} — keyword tmp_path must be guarded too"


def test_a_subroot_built_from_tmp_path_is_not_flagged(tmp_path: Path) -> None:
    """Negative control: folding the parametrize key into a subroot (#72's fix) is the escape."""
    planted = tmp_path / "test_correctly_folded.py"
    planted.write_text(
        textwrap.dedent(
            """\
            import pytest

            @pytest.mark.parametrize("limb_id", ["a", "b"])
            def test_something(tmp_path, limb_id):
                scan_graph_monolith_paths(tmp_path / limb_id)
            """
        ),
        encoding="utf-8",
    )
    assert guard.scan_tree(tmp_path) == []


def test_a_non_parametrized_test_is_not_flagged(tmp_path: Path) -> None:
    """Negative control: a bare tmp_path is safe when the test is not parametrized."""
    planted = tmp_path / "test_not_parametrized.py"
    planted.write_text(
        textwrap.dedent(
            """\
            def test_something(tmp_path):
                scan_graph_monolith_paths(tmp_path)
            """
        ),
        encoding="utf-8",
    )
    assert guard.scan_tree(tmp_path) == []

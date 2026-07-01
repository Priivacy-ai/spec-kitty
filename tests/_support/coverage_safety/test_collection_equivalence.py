"""Unit tests for the collection-equivalence helper (T005).

Self-tests scope to a *tiny* fixture test dir written into ``tmp_path`` — never
the real suite — so subprocess collection stays fast (Risks & Mitigations).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._support.coverage_safety.collection_equivalence import (
    CollectionEquivalenceError,
    _looks_like_nodeid,
    assert_equivalent,
    collect_nodeids,
)

pytestmark = [pytest.mark.integration, pytest.mark.fast]

# A minimal, self-contained test module the helper can collect in a subprocess.
_FIXTURE_TESTS = """\
def test_one():
    assert True


def test_two():
    assert True


def test_three():
    assert True
"""


@pytest.fixture()
def fixture_dir(tmp_path: Path) -> Path:
    """A tiny dir holding a single test module with three test functions."""
    target = tmp_path / "shard"
    target.mkdir()
    (target / "test_sample.py").write_text(_FIXTURE_TESTS, encoding="utf-8")
    return target


def test_collect_nodeids_finds_all_tests(fixture_dir: Path) -> None:
    nodeids = collect_nodeids([str(fixture_dir)])
    names = {nid.split("::")[-1] for nid in nodeids}
    assert names == {"test_one", "test_two", "test_three"}
    # Every collected entry is a real nodeid, never a summary line.
    assert all("::" in nid for nid in nodeids)


def test_collect_nodeids_empty_dir_returns_empty_set(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert collect_nodeids([str(empty)]) == set()


def test_assert_equivalent_identical_selectors_passes(fixture_dir: Path) -> None:
    # Same selector both sides — collection is identical, so no raise (the call
    # returns None and must not raise).
    assert_equivalent([str(fixture_dir)], [str(fixture_dir)])


def test_assert_equivalent_parallel_flags_do_not_change_collection(
    fixture_dir: Path,
) -> None:
    # Adding -n auto --dist loadfile must not change the collected nodeid set;
    # this is the real C-EQUIV check shape (serial vs parallel selector).
    assert_equivalent(
        [str(fixture_dir)],
        [str(fixture_dir), "-n", "auto", "--dist", "loadfile"],
    )


def test_assert_equivalent_different_selectors_raises_with_diff(
    fixture_dir: Path,
) -> None:
    # Deselect one test on the "parallel" side via -k so the sets differ; the
    # error must name the missing nodeid (anti-silent-drop).
    with pytest.raises(CollectionEquivalenceError) as exc_info:
        assert_equivalent(
            [str(fixture_dir)],
            [str(fixture_dir), "-k", "not test_three"],
        )
    err = exc_info.value
    assert any("test_three" in nid for nid in err.only_serial)
    assert not err.only_parallel
    assert "test_three" in str(err)


def test_collect_nodeids_raises_on_collection_error(tmp_path: Path) -> None:
    # A module with a syntax error makes pytest exit with a collection error
    # (>=2); the helper must surface that rather than silently returning {}.
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "test_broken.py").write_text("def test_x(:\n    pass\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        collect_nodeids([str(bad)])


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("tests/foo/test_bar.py::test_x", True),
        ("tests/foo/test_bar.py", True),
        ("", False),
        ("3 tests collected in 0.01s", False),
        ("no tests ran in 0.00s", False),
        ("1 warning", False),
    ],
)
def test_looks_like_nodeid_classification(line: str, expected: bool) -> None:
    assert _looks_like_nodeid(line) is expected

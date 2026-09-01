"""Self-test for the shared non-vacuity examined-floor guard (#3273) and the
diff-scope git resolver (#3147, B-WP02).

``related_validator.validate_related`` and
``relative_link_fixer.check_dead_body_links`` both route their "examined
count fell below the floor" ``RuntimeError`` through
``scripts.docs._guards.assert_examined_floor``. These tests exercise the
helper directly so its branches — below-floor raise, at/above-floor no-raise,
and the ``gate``/``noun``/``fr_id``/``extra`` parameterization surfacing in
the message — are covered independently of either caller.

The second half exercises :func:`scripts.docs._guards.resolve_changed_files`,
the shared diff-scope resolver used by all four blocking per-page gates'
``--changed-from`` modes. **B-WP02 is the load-bearing distinction pinned
here:** fail-closed keys on git base RESOLVABILITY (a non-zero ``git`` return
code), never on the resolved changed-set being empty.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.docs._guards import GitDiffError, assert_examined_floor, resolve_changed_files
from tests.docs.conftest import commit_all_changes, init_git_repo_with_base

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_below_floor_raises_with_expected_substrings() -> None:
    """A count under the minimum raises, and the message carries the shape
    both callers' tests assert on: the count, the minimum, the FR id, and the
    "non-vacuity guard" / "expected at least" phrasing."""
    with pytest.raises(RuntimeError) as excinfo:
        assert_examined_floor(0, 1, gate="my_gate", noun="widget(s) examined", fr_id="FR-999")

    message = str(excinfo.value)
    assert "my_gate" in message
    assert "0 widget(s) examined" in message
    assert "expected at least 1" in message
    assert "FR-999 non-vacuity guard" in message


def test_at_floor_does_not_raise() -> None:
    """A count exactly at the minimum clears the floor."""
    assert_examined_floor(1, 1, gate="my_gate", noun="thing(s)", fr_id="FR-999")


def test_above_floor_does_not_raise() -> None:
    """A count above the minimum clears the floor."""
    assert_examined_floor(5, 1, gate="my_gate", noun="thing(s)", fr_id="FR-999")


def test_extra_detail_appears_in_message_when_provided() -> None:
    """The optional ``extra`` caveat is appended inside the parenthetical."""
    with pytest.raises(RuntimeError, match="possible misconfiguration"):
        assert_examined_floor(
            0,
            1,
            gate="my_gate",
            noun="thing(s)",
            fr_id="FR-999",
            extra="possible misconfiguration",
        )


def test_no_extra_detail_omits_trailing_comma() -> None:
    """Without ``extra`` the parenthetical has no dangling ``", "`` suffix."""
    with pytest.raises(RuntimeError) as excinfo:
        assert_examined_floor(0, 1, gate="my_gate", noun="thing(s)", fr_id="FR-999")

    message = str(excinfo.value)
    assert "non-vacuity guard)" in message
    assert "non-vacuity guard," not in message


def test_gate_noun_fr_id_are_parameterized_per_caller() -> None:
    """Different callers get distinct, correctly-substituted messages."""
    with pytest.raises(RuntimeError) as excinfo:
        assert_examined_floor(
            2,
            3,
            gate="check_dead_body_links",
            noun="doc file(s) found under docs/",
            fr_id="FR-004",
        )

    message = str(excinfo.value)
    assert message.startswith("check_dead_body_links:")
    assert "doc file(s) found under docs/" in message
    assert "FR-004 non-vacuity guard" in message


# --------------------------------------------------------------------------- #
# resolve_changed_files (#3147, B-WP02) — diff-scope git resolution.
# --------------------------------------------------------------------------- #


def test_resolved_base_with_no_changes_returns_empty_list_not_error(
    tmp_path: Path,
) -> None:
    """B-WP02: a resolvable base with zero subsequent changes is NOT an error.

    A resolved diff yielding zero changed files is the common shape for a PR
    that doesn't touch docs at all (e.g. ``src/specify_cli/**``-only) — the
    caller must see an empty list, never a raised exception.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# hi\n", encoding="utf-8")
    base_sha = init_git_repo_with_base(repo)

    changed = resolve_changed_files(repo, base_sha)

    assert changed == []


def test_resolved_base_with_changes_returns_changed_paths(tmp_path: Path) -> None:
    """A resolvable base with subsequent changes returns those repo-relative paths."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# hi\n", encoding="utf-8")
    base_sha = init_git_repo_with_base(repo)

    (repo / "docs").mkdir()
    (repo / "docs" / "new.md").write_text("# New\n", encoding="utf-8")
    commit_all_changes(repo, "add a doc")

    changed = resolve_changed_files(repo, base_sha)

    assert changed == ["docs/new.md"]


def test_changed_paths_are_lossless_with_unicode_and_newlines(tmp_path: Path) -> None:
    """NUL framing avoids Git's quotePath encoding and line-delimiter ambiguity."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# hi\n", encoding="utf-8")
    base_sha = init_git_repo_with_base(repo)

    docs = repo / "docs"
    docs.mkdir()
    unicode_path = docs / "café.md"
    newline_path = docs / "line\nbreak.md"
    unicode_path.write_text("# Unicode\n", encoding="utf-8")
    newline_path.write_text("# Newline\n", encoding="utf-8")
    commit_all_changes(repo, "add unusual doc paths")

    changed = resolve_changed_files(repo, base_sha)

    assert changed == ["docs/café.md", "docs/line\nbreak.md"]


def test_unresolvable_base_raises_git_diff_error(tmp_path: Path) -> None:
    """B-WP02: an unresolvable/unfetched base ref is the ONLY fail-closed trigger."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# hi\n", encoding="utf-8")
    init_git_repo_with_base(repo)

    with pytest.raises(GitDiffError):
        resolve_changed_files(repo, "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")


def test_git_diff_error_message_names_the_base_ref(tmp_path: Path) -> None:
    """The raised error is actionable: it names the unresolvable base ref."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# hi\n", encoding="utf-8")
    init_git_repo_with_base(repo)

    with pytest.raises(GitDiffError, match="garbage-ref-does-not-exist"):
        resolve_changed_files(repo, "garbage-ref-does-not-exist")


def test_non_git_directory_raises_git_diff_error(tmp_path: Path) -> None:
    """A repo_root that isn't a git repo at all also fails closed."""
    not_a_repo = tmp_path / "plain"
    not_a_repo.mkdir()

    with pytest.raises(GitDiffError):
        resolve_changed_files(not_a_repo, "HEAD")

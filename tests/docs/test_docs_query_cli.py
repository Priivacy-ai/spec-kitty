"""Tests for `spec-kitty docs query` (WP03, FR-002/FR-003/FR-004/NFR-002).

Each test pins a single, distinct row of ``contracts/cli-contract.md`` --
none share the "return everything" shortcut that a single-anchor fixture
would let pass. The fixture index is built module-locally with
``render_index``/``DocsQueryEntry`` from the packaged
``specify_cli.docs.index_model`` (WP01's home for that schema) -- this file
does NOT share a conftest fixture with WP01/WP02's docs tests.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.docs.index_model import (
    DEFAULT_INDEX_PATH,
    Anchor,
    DocsQueryEntry,
    render_index,
)
from specify_cli.cli.commands import docs as docs_cli

runner = CliRunner()

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

# ``docs_cli.app`` currently registers exactly one command ("query"). Typer's
# own CLI runner collapses a *standalone* single-command Typer app into that
# command directly (so invoking it bare with ["query", "worktree"] would
# treat "query" as the TERM argument, per Typer's documented single-command
# convenience). In production this never bites because `register_commands`
# always mounts the app via `app.add_typer(docs_module.app, name="docs")`,
# which preserves "query" as an explicit subcommand of the "docs" group --
# mirror that exact mounting here so the test surface matches real usage.
_root_app = typer.Typer()
_root_app.add_typer(docs_cli.app, name="docs")


def _invoke(*args: str) -> object:
    return runner.invoke(_root_app, ["docs", *args])

# ---------------------------------------------------------------------------
# Fixture index -- three pages, deliberately path-sorted, that exercise every
# contract row without relying on a single-anchor "return everything" fixture.
# ---------------------------------------------------------------------------

_WORKTREES_ENTRY = DocsQueryEntry(
    path="docs/architecture/worktrees.md",
    title="Execution Worktrees",
    divio_type="explanation",
    anchors=(
        Anchor(slug="overview", text="Overview", level=2),
        Anchor(slug="lane-allocation", text="Lane Allocation", level=2),
    ),
    abstract="How lanes map to git worktrees.",
)

# FR-003 discriminating case (BLOCKING): two anchors, term matches exactly one.
_CHEATSHEET_ENTRY = DocsQueryEntry(
    path="docs/reference/cli-cheatsheet.md",
    title="CLI Cheatsheet Reference",
    divio_type="reference",
    anchors=(
        Anchor(slug="worktree-commands", text="Worktree Commands", level=2),
        Anchor(slug="status-commands", text="Status Commands", level=2),
    ),
    abstract="Quick reference for spec-kitty CLI commands.",
)

_GETTING_STARTED_ENTRY = DocsQueryEntry(
    path="docs/tutorials/getting-started.md",
    title="Getting Started",
    divio_type="tutorial",
    anchors=(
        Anchor(slug="install", text="Install", level=2),
        Anchor(slug="first-mission", text="First Mission", level=2),
    ),
    abstract="Get started with spec-kitty in 10 minutes.",
)

_ALL_ENTRIES = (_WORKTREES_ENTRY, _CHEATSHEET_ENTRY, _GETTING_STARTED_ENTRY)


@pytest.fixture()
def indexed_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Stage a real, on-disk generated index at DEFAULT_INDEX_PATH and chdir."""
    index_path = tmp_path / DEFAULT_INDEX_PATH
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(render_index(_ALL_ENTRIES), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Row 1: match -> correct JSON element shape, exit 0
# ---------------------------------------------------------------------------


def test_match_returns_correct_json_shape(indexed_repo: Path) -> None:
    result = _invoke("query", "worktree", "--json")

    assert result.exit_code == 0
    import json

    payload = json.loads(result.output)
    paths = {item["path"] for item in payload}
    assert paths == {_WORKTREES_ENTRY.path, _CHEATSHEET_ENTRY.path}

    worktrees_item = next(item for item in payload if item["path"] == _WORKTREES_ENTRY.path)
    assert worktrees_item["title"] == "Execution Worktrees"
    assert worktrees_item["divio_type"] == "explanation"
    assert worktrees_item["abstract"] == "How lanes map to git worktrees."
    assert "anchors" in worktrees_item


# ---------------------------------------------------------------------------
# Row FR-003 (BLOCKING): >=2 anchors, term matches exactly one -> anchors
# contains ONLY that one.
# ---------------------------------------------------------------------------


def test_fr003_discriminating_anchor_match_returns_only_matched_anchor(
    indexed_repo: Path,
) -> None:
    result = _invoke("query", "worktree", "--json")
    assert result.exit_code == 0

    import json

    payload = json.loads(result.output)
    cheatsheet_item = next(item for item in payload if item["path"] == _CHEATSHEET_ENTRY.path)

    # The cheatsheet page has TWO anchors; only "worktree-commands" contains
    # the term "worktree". A wrong "return all anchors" implementation would
    # also include "status-commands" here.
    assert [anchor["slug"] for anchor in cheatsheet_item["anchors"]] == ["worktree-commands"]


def test_matched_on_title_only_returns_empty_anchors(indexed_repo: Path) -> None:
    result = _invoke("query", "worktree", "--json")
    assert result.exit_code == 0

    import json

    payload = json.loads(result.output)
    worktrees_item = next(item for item in payload if item["path"] == _WORKTREES_ENTRY.path)

    # "worktree" matched via the title ("Execution Worktrees"); neither
    # anchor's text/slug ("overview", "lane-allocation") contains "worktree".
    assert worktrees_item["anchors"] == []


# ---------------------------------------------------------------------------
# Row 2: no match -> [], exit 0
# ---------------------------------------------------------------------------


def test_no_match_returns_empty_json_array_exit_zero(indexed_repo: Path) -> None:
    result = _invoke("query", "zzzznomatch", "--json")

    assert result.exit_code == 0
    assert result.output.strip() == "[]"


# ---------------------------------------------------------------------------
# Empty/whitespace TERM -> usage error exit 2
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_term", ["", "   "])
def test_empty_or_whitespace_term_is_usage_error(indexed_repo: Path, bad_term: str) -> None:
    result = _invoke("query", bad_term, "--json")

    assert result.exit_code == 2
    assert "Traceback" not in result.output


# ---------------------------------------------------------------------------
# Row 3: --divio-type filter
# ---------------------------------------------------------------------------


def test_divio_type_filter_narrows_to_matching_type(indexed_repo: Path) -> None:
    # "spec-kitty" appears in the cheatsheet (reference) and getting-started
    # (tutorial) abstracts, but NOT in the worktrees abstract/title/anchors.
    result = _invoke("query", "spec-kitty", "--divio-type", "reference", "--json")
    assert result.exit_code == 0

    import json

    payload = json.loads(result.output)
    assert [item["path"] for item in payload] == [_CHEATSHEET_ENTRY.path]


# ---------------------------------------------------------------------------
# Row 4: --section filter
# ---------------------------------------------------------------------------


def test_section_filter_narrows_to_pages_with_that_anchor(indexed_repo: Path) -> None:
    result = _invoke("query", "getting", "--section", "install", "--json")
    assert result.exit_code == 0

    import json

    payload = json.loads(result.output)
    assert [item["path"] for item in payload] == [_GETTING_STARTED_ENTRY.path]
    # The anchor that satisfied --section should be surfaced in the result.
    assert [anchor["slug"] for anchor in payload[0]["anchors"]] == ["install"]


# ---------------------------------------------------------------------------
# Row 5: invalid --divio-type -> exit 2, no traceback
# ---------------------------------------------------------------------------


def test_invalid_divio_type_is_usage_error_no_traceback(indexed_repo: Path) -> None:
    result = _invoke("query", "worktree", "--divio-type", "bogus-type", "--json")

    assert result.exit_code == 2
    assert "Traceback" not in result.output


# ---------------------------------------------------------------------------
# Row 6: missing docs/ tree or index file -> non-zero exit, message, no
# traceback (distinct from the "no match" -> [] exit-0 case above).
# ---------------------------------------------------------------------------


def test_missing_docs_tree_is_actionable_error_no_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)  # empty dir: no docs/, no index

    result = _invoke("query", "worktree", "--json")

    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "docs" in result.output.lower()


def test_missing_index_file_with_docs_tree_present_is_actionable_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "docs").mkdir()  # docs/ exists, but no generated index file
    monkeypatch.chdir(tmp_path)

    result = _invoke("query", "worktree", "--json")

    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "index" in result.output.lower()


# ---------------------------------------------------------------------------
# Row 7 (BLOCKING): default human path (no --json) -> table renders; piped
# output has NO Rich markup/control tokens.
# ---------------------------------------------------------------------------


def test_human_table_renders_with_no_rich_markup_leak(indexed_repo: Path) -> None:
    result = _invoke("query", "worktree")

    assert result.exit_code == 0
    # A table rendered: expect to see the matched paths/titles as plain text.
    assert _WORKTREES_ENTRY.path in result.output
    assert _CHEATSHEET_ENTRY.path in result.output
    # No leaked Rich markup tags and no raw ANSI escape sequences -- CliRunner
    # captures a non-tty stream, so Rich must not emit either.
    assert "[cyan]" not in result.output
    assert "[/cyan]" not in result.output
    assert "[bold]" not in result.output
    assert not _ANSI_ESCAPE.search(result.output)


# ---------------------------------------------------------------------------
# NFR-002 structural guard: no filesystem walk after DocsIndexStore.load().
# ---------------------------------------------------------------------------


def test_query_performs_no_filesystem_access_after_load(
    indexed_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from specify_cli.docs.index_model import DocsIndexStore

    # Load for real (this is the one legitimate filesystem read).
    store = DocsIndexStore.load(Path(DEFAULT_INDEX_PATH))

    rglob_calls: list[Path] = []
    open_calls: list[object] = []

    original_rglob = Path.rglob

    def _spy_rglob(self: Path, *args: object, **kwargs: object) -> object:
        rglob_calls.append(self)
        return original_rglob(self, *args, **kwargs)

    original_open = Path.open

    def _spy_open(self: Path, *args: object, **kwargs: object) -> object:
        open_calls.append(self)
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "rglob", _spy_rglob)
    monkeypatch.setattr(Path, "open", _spy_open)

    results = store.query("worktree")

    assert results  # sanity: the query still found matches
    assert rglob_calls == []
    assert open_calls == []


def test_live_tree_query_is_fast(indexed_repo: Path) -> None:
    """Soft smoke ceiling -- not the primary NFR-002 assertion above."""
    import time

    from specify_cli.docs.index_model import DocsIndexStore

    store = DocsIndexStore.load(Path(DEFAULT_INDEX_PATH))
    started = time.monotonic()
    store.query("worktree")
    assert time.monotonic() - started < 1.0

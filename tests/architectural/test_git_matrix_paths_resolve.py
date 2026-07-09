"""Guard: every ``Source File`` reference in the shipped git-operations
matrix must resolve to a real file on disk (FR-011, issue #2447).

The matrix is shipped doctrine
(``src/doctrine/skills/spec-kitty-git-workflow/references/git-operations-matrix.md``)
that agents read to learn which git commands spec-kitty executes and where.
A phantom row — a ``Source File`` cell naming a file/function that never
existed in git history (``core/mission_detection.py::_detect_from_branch()``,
#2447) — silently misleads every agent that trusts the matrix. This guard
parses the "Python-Executed Git Commands" table and asserts every
path-shaped ``Source File`` cell resolves under ``src/specify_cli/``, so a
future phantom entry fails the build instead of shipping silently.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src" / "specify_cli"
_MATRIX_PATH = (
    _REPO_ROOT
    / "src"
    / "doctrine"
    / "skills"
    / "spec-kitty-git-workflow"
    / "references"
    / "git-operations-matrix.md"
)
_SECTION_HEADING = "## Python-Executed Git Commands"


def _section_lines(markdown_text: str, heading: str) -> list[str]:
    """Return the lines of the table under *heading*, up to the next ``## ``."""
    lines = markdown_text.splitlines()
    start: int | None = None
    end = len(lines)
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start = index + 1
            continue
        if start is not None and line.startswith("## "):
            end = index
            break
    if start is None:
        raise AssertionError(f"Matrix is missing the {heading!r} section")
    return lines[start:end]


def _is_separator_row(cells: list[str]) -> bool:
    return all(set(cell) <= {"-", ":", " "} for cell in cells)


def _table_rows(lines: list[str]) -> list[list[str]]:
    """Parse pipe-delimited markdown table rows, dropping header/separator rows."""
    rows: list[list[str]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if _is_separator_row(cells):
            continue
        if cells and cells[0] == "Command":
            continue
        rows.append(cells)
    return rows


def _source_file_cells(rows: list[list[str]]) -> list[str]:
    """Extract every individual path token from the ``Source File`` column.

    A cell may list several comma-separated files (e.g.
    ``cli/commands/implement.py, git/commit_helpers.py``); each is yielded
    separately.
    """
    cells: list[str] = []
    for row in rows:
        if len(row) < 3:
            continue
        source_cell = row[2]
        for part in source_cell.split(","):
            candidate = part.strip().strip("`").strip()
            if candidate:
                cells.append(candidate)
    return cells


def _is_path_shaped(cell: str) -> bool:
    """Return True for cells that name a concrete source file (not prose)."""
    return cell.endswith(".py")


def _phantom_paths(markdown_text: str) -> list[str]:
    """Return path-shaped ``Source File`` cells that don't resolve on disk."""
    rows = _table_rows(_section_lines(markdown_text, _SECTION_HEADING))
    cells = _source_file_cells(rows)
    path_shaped = [cell for cell in cells if _is_path_shaped(cell)]
    assert path_shaped, "Expected at least one path-shaped Source File cell to check"
    return [cell for cell in path_shaped if not (_SRC_ROOT / cell).exists()]


def test_all_source_file_paths_resolve_on_disk() -> None:
    """Every ``Source File`` cell in the shipped matrix names a real file."""
    text = _MATRIX_PATH.read_text(encoding="utf-8")
    missing = _phantom_paths(text)
    assert not missing, (
        "Phantom Source File reference(s) in git-operations-matrix.md "
        f"(file does not exist under src/specify_cli/): {missing}"
    )


def test_guard_bites_on_planted_phantom_path() -> None:
    """Red-first proof: a planted nonexistent path is caught by the parser."""
    text = _MATRIX_PATH.read_text(encoding="utf-8")
    phantom_name = "core/does_not_exist_phantom_2447.py"
    planted = text.replace(
        "`core/git_ops.py`",
        f"`{phantom_name}`",
        1,
    )
    assert planted != text, "Fixture setup failed: the anchor cell was not found to replace"
    missing = _phantom_paths(planted)
    assert phantom_name in missing

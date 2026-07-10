"""Scope: mock-boundary tests for charter generator — no real git."""

import os
from pathlib import Path

import pytest

from charter.catalog import load_doctrine_catalog
from charter.compiler import CompiledCharter, write_compiled_charter
from charter.generator import build_charter_draft, write_charter

pytestmark = pytest.mark.fast


def test_build_charter_draft_defaults() -> None:
    """WP03 re-pin (T028): draft built with NO project config (no
    ``repo_root``/``pack_context`` passed to ``build_charter_draft``) uses
    the documented absent-config default -- every built-in directive/
    paradigm active, not an empty "neutral" selection.

    Before WP02 (FR-001/FR-002), "no config" meant "no interview
    selections", which defaulted to empty lists, so this test's original
    assertion (``selected_directives == []``) pinned that answers-sourced
    default. Activation is now config-sourced; ``PackContext``'s documented
    three-state absent-key default is "every built-in kind active" (see
    ``charter.pack_context.PackContext`` field docstrings and
    ``tests/charter/test_config_sourced_derivation.py::test_no_pack_context_and_no_repo_root_defaults_to_all_builtins_active``),
    so the "neutral" default flips from empty to all-active. This still
    exercises a genuine, distinct invariant -- that the ``build_charter_draft``
    thin wrapper forwards ``compile_charter``'s selections/markdown
    correctly -- so it is re-pinned, not deleted.
    """
    # Act
    draft = build_charter_draft(mission="software-dev")

    # Assert
    catalog = load_doctrine_catalog()
    assert draft.template_set == "software-dev-default"
    assert sorted(draft.selected_directives) == sorted(catalog.directives)
    assert sorted(draft.selected_paradigms) == sorted(catalog.paradigms)
    assert "selected_directives" in draft.markdown


def test_build_charter_draft_invalid_template_set_raises() -> None:
    """Requesting an unknown template set raises ValueError."""
    # Arrange
    # (no precondition)

    # Assumption check
    # (no precondition)

    # Act / Assert
    with pytest.raises(ValueError):
        build_charter_draft(mission="software-dev", template_set="not-real")


def test_write_charter_respects_force(tmp_path: Path) -> None:
    """write_charter raises FileExistsError when force=False and file exists."""
    # Arrange
    path = tmp_path / "charter.md"
    write_charter(path, "# One", force=False)

    # Assumption check
    assert path.exists(), "first write must have created the file"

    # Act / Assert
    with pytest.raises(FileExistsError):
        write_charter(path, "# Two", force=False)

    write_charter(path, "# Two", force=True)

    # Assert
    assert path.read_text(encoding="utf-8") == "# Two"


@pytest.mark.requires_symlinks
def test_write_charter_rejects_symlink_even_with_force(tmp_path: Path) -> None:
    target = tmp_path / "outside.md"
    target.write_text("# Outside\n", encoding="utf-8")
    path = tmp_path / "charter.md"
    try:
        os.symlink(target, path)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")

    with pytest.raises(FileExistsError, match="is a symlink"):
        write_charter(path, "# Two", force=True)

    assert target.read_text(encoding="utf-8") == "# Outside\n"


@pytest.mark.requires_symlinks
def test_write_compiled_charter_rejects_symlink_even_with_force(tmp_path: Path) -> None:
    target = tmp_path / "outside.md"
    target.write_text("# Outside\n", encoding="utf-8")
    output_dir = tmp_path / ".kittify" / "charter"
    output_dir.mkdir(parents=True)
    try:
        os.symlink(target, output_dir / "charter.md")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")
    compiled = CompiledCharter(
        mission="software-dev",
        template_set="software-dev-default",
        selected_paradigms=[],
        selected_directives=[],
        available_tools=[],
        markdown="# Generated\n",
        references=[],
    )

    with pytest.raises(FileExistsError, match="is a symlink"):
        write_compiled_charter(output_dir, compiled, force=True)

    assert target.read_text(encoding="utf-8") == "# Outside\n"


@pytest.mark.requires_symlinks
def test_write_compiled_charter_rejects_symlinked_output_dir(tmp_path: Path) -> None:
    outside_dir = tmp_path / "outside-charter"
    outside_dir.mkdir()
    output_dir = tmp_path / ".kittify" / "charter"
    output_dir.parent.mkdir()
    try:
        os.symlink(outside_dir, output_dir, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")
    compiled = CompiledCharter(
        mission="software-dev",
        template_set="software-dev-default",
        selected_paradigms=[],
        selected_directives=[],
        available_tools=[],
        markdown="# Generated\n",
        references=[],
    )

    with pytest.raises(FileExistsError, match="Charter output path"):
        write_compiled_charter(output_dir, compiled, force=True, repo_root=tmp_path)

    assert not (outside_dir / "charter.md").exists()
    assert not (outside_dir / "references.yaml").exists()


@pytest.mark.requires_symlinks
def test_write_compiled_charter_rejects_symlinked_output_dir_without_repo_root(tmp_path: Path) -> None:
    outside_dir = tmp_path / "outside-charter"
    outside_dir.mkdir()
    output_dir = tmp_path / ".kittify" / "charter"
    output_dir.parent.mkdir()
    try:
        os.symlink(outside_dir, output_dir, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")
    compiled = CompiledCharter(
        mission="software-dev",
        template_set="software-dev-default",
        selected_paradigms=[],
        selected_directives=[],
        available_tools=[],
        markdown="# Generated\n",
        references=[],
    )

    with pytest.raises(FileExistsError, match="Charter output directory"):
        write_compiled_charter(output_dir, compiled, force=True)

    assert not (outside_dir / "charter.md").exists()


def test_write_compiled_charter_rejects_output_dir_that_resolves_outside_repo(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    compiled = CompiledCharter(
        mission="software-dev",
        template_set="software-dev-default",
        selected_paradigms=[],
        selected_directives=[],
        available_tools=[],
        markdown="# Generated\n",
        references=[],
    )

    with pytest.raises(FileExistsError, match="resolves outside repository root"):
        write_compiled_charter(
            repo_root / ".." / "outside-charter",
            compiled,
            force=True,
            repo_root=repo_root,
        )

    assert not (tmp_path / "outside-charter" / "charter.md").exists()

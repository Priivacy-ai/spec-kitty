"""Native Windows regression test for the worktree symlink-vs-copy fallback.

On Windows, creating symlinks requires elevated privileges (Developer Mode or
SeCreateSymbolicLinkPrivilege).  ``setup_feature_directory`` detects this and
falls back to ``shutil.copytree`` / ``shutil.copy2`` for:

- ``.kittify/memory/`` — a directory containing agent memory files
- ``.kittify/AGENTS.md`` — the shared agents context file

Both materialised copies must be readable and contain the expected content.
A path-with-spaces variant exercises the Windows path quoting code paths.

Marked ``@pytest.mark.windows_ci`` — runs only on the ``windows-latest`` CI
job (skipped on POSIX CI runners via the ``-m "not windows_ci"`` filter).

Spec IDs: FR-014, FR-016, FR-017, NFR-001
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _init_repo_with_kittify(repo: Path) -> None:
    """Initialise a minimal git repo with .kittify/memory and AGENTS.md."""
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)

    kittify_memory = repo / ".kittify" / "memory"
    kittify_memory.mkdir(parents=True)
    (kittify_memory / "memory.md").write_text("memory content", encoding="utf-8")

    agents_md = repo / ".kittify" / "AGENTS.md"
    agents_md.write_text("agents content", encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)


@pytest.mark.windows_ci
def test_worktree_materializes_kittify_memory_and_agents_on_windows(tmp_path: pytest.TempPathFactory) -> None:
    """``setup_feature_directory`` must copy .kittify/memory and AGENTS.md on Windows.

    Tests the copy fallback path (``use_copy=True``) that is taken when
    ``platform.system() == "Windows"`` or when symlinks are unavailable.
    Both ``memory.md`` and ``AGENTS.md`` must be readable in the worktree.
    """
    from specify_cli.core.worktree import setup_feature_directory

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo_with_kittify(repo)

    # Simulate the worktree directory structure
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()

    feature_dir = worktree_path / "kitty-specs" / "demo-feature"
    feature_dir.mkdir(parents=True)

    # Call with create_symlinks=False (the Windows fallback path)
    setup_feature_directory(feature_dir, worktree_path, repo, create_symlinks=False)

    # Both files must exist and have readable content
    memory_file = worktree_path / ".kittify" / "memory" / "memory.md"
    agents_file = worktree_path / ".kittify" / "AGENTS.md"

    assert memory_file.exists(), f".kittify/memory/memory.md missing in worktree: {memory_file}"
    assert agents_file.exists(), f".kittify/AGENTS.md missing in worktree: {agents_file}"

    assert memory_file.read_text(encoding="utf-8") == "memory content", f"memory.md content mismatch: {memory_file.read_text(encoding='utf-8')!r}"
    assert agents_file.read_text(encoding="utf-8") == "agents content", f"AGENTS.md content mismatch: {agents_file.read_text(encoding='utf-8')!r}"


@pytest.mark.windows_ci
def test_worktree_on_path_with_spaces_on_windows(tmp_path: pytest.TempPathFactory) -> None:
    """Worktree setup must work when the path contains spaces (Windows).

    Exercises the path-quoting code paths in ``setup_feature_directory`` and
    the underlying git/shutil calls.
    """
    from specify_cli.core.worktree import setup_feature_directory

    repo = tmp_path / "repo with spaces"
    repo.mkdir()
    _init_repo_with_kittify(repo)

    worktree_path = tmp_path / "wt with spaces"
    worktree_path.mkdir()

    feature_dir = worktree_path / "kitty-specs" / "demo-feature-spaces"
    feature_dir.mkdir(parents=True)

    # Use create_symlinks=False (Windows fallback)
    setup_feature_directory(feature_dir, worktree_path, repo, create_symlinks=False)

    agents_file = worktree_path / ".kittify" / "AGENTS.md"
    assert agents_file.exists(), f".kittify/AGENTS.md missing for path-with-spaces repo: {agents_file}"
    assert agents_file.read_text(encoding="utf-8") == "agents content", (
        f"AGENTS.md content mismatch in path-with-spaces repo: {agents_file.read_text(encoding='utf-8')!r}"
    )
